#!/usr/bin/env python3
"""CLI entry point for file-hash-calculator.

Computes BLAKE3 hashes for files and directories, supporting multiple output
formats, exclusion patterns, progress indication, concurrent computation,
and checkpoint/resume functionality.
"""

import argparse
import os
import signal
import sys
from typing import Optional

from lib.traverser import Traverser
from lib.hasher import compute_hashes
from lib.formatter import format_output
from lib.models import HashEntry
from lib.checkpoint import (
    CheckpointManager,
    load_checkpoint,
    is_stale,
)
from lib.progress import ProgressBar


def parse_args(argv: list[str]) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        prog="file-hash-calculator",
        description="计算文件和目录的 BLAKE3 哈希值",
    )

    parser.add_argument(
        "paths",
        nargs="*",
        help="要计算哈希的文件或目录路径（可指定多个）",
    )

    parser.add_argument(
        "-f",
        "--format",
        choices=["markdown", "json", "csv", "yaml"],
        default="markdown",
        help="输出格式（默认: markdown）",
    )

    parser.add_argument(
        "-o",
        "--output",
        default=None,
        help="输出文件路径（不指定则输出到终端）",
    )

    parser.add_argument(
        "-e",
        "--exclude",
        action="append",
        default=None,
        help="排除模式（gitignore 风格，可多次指定）",
    )

    parser.add_argument(
        "-w",
        "--workers",
        type=int,
        default=os.cpu_count() or 1,
        help="并发线程数（默认: CPU 核心数）",
    )

    parser.add_argument(
        "-l",
        "--hash-length",
        type=int,
        default=256,
        help="BLAKE3 哈希输出长度（bit，默认: 256）",
    )

    return parser.parse_args(argv)


def _resolve_paths(
    paths: list[str],
) -> tuple[list[str], list[str], list[str]]:
    """Resolve, deduplicate, and categorize input paths.

    Expands directories into file lists using the traverser.

    Args:
        paths: Raw input paths from command line.

    Returns:
        Tuple of (all_absolute_paths, file_paths, dir_paths).
    """
    seen: set[str] = set()

    for p in paths:
        # Resolve to absolute path
        abs_path = os.path.abspath(p)

        if abs_path in seen:
            continue

        # Check if this path is a descendant of an already-seen directory
        # If so, skip it (ancestor directory covers it)
        skip = False
        for seen_path in seen:
            if abs_path.startswith(seen_path + os.sep):
                skip = True
                break

        if skip:
            continue

        # Check if this path is an ancestor of already-seen paths
        # If so, remove those descendants
        descendants_to_remove = set()
        for seen_path in seen:
            if seen_path.startswith(abs_path + os.sep):
                descendants_to_remove.add(seen_path)

        seen -= descendants_to_remove
        seen.add(abs_path)

    return list(seen)


def _collect_paths(
    root_paths: list[str],
    exclude_patterns: Optional[list[str]],
) -> tuple[list[str], list[str]]:
    """Collect all files and directories from the given root paths.

    Args:
        root_paths: Resolved absolute paths.
        exclude_patterns: Gitignore-style patterns to exclude.

    Returns:
        Tuple of (file_paths, dir_paths) where dir_paths includes the
        root directories and all their subdirectories.
    """
    traverser = Traverser(exclude_patterns=exclude_patterns)

    all_files: list[str] = []
    all_dirs: list[str] = []

    for root_path in root_paths:
        if os.path.isfile(root_path):
            all_files.append(root_path)
        elif os.path.isdir(root_path):
            # Traverse collects all entries in bottom-up order
            entries = traverser.traverse(root_path)

            for entry_path in entries:
                if os.path.isfile(entry_path):
                    all_files.append(entry_path)
                elif os.path.isdir(entry_path):
                    all_dirs.append(entry_path)

            # The root directory itself is also a dir to hash
            all_dirs.append(root_path)
        elif os.path.islink(root_path):
            print(
                f"warning: skipping symlink '{root_path}'",
                file=sys.stderr,
            )
        else:
            print(
                f"error: path does not exist: '{root_path}'",
                file=sys.stderr,
            )

    return all_files, all_dirs


def _infer_format(output_path: str, explicit_format: Optional[str]) -> str:
    """Infer output format from file extension if not explicitly specified.

    Args:
        output_path: Path to the output file.
        explicit_format: Format specified via --format (may be None).

    Returns:
        The format string to use.
    """
    if explicit_format and explicit_format != "markdown":
        # User explicitly specified a non-default format
        return explicit_format

    ext = os.path.splitext(output_path)[1].lower()
    if ext == ".json":
        return "json"
    elif ext == ".csv":
        return "csv"
    elif ext in (".yaml", ".yml"):
        return "yaml"
    else:
        return explicit_format or "markdown"


def main(argv: Optional[list[str]] = None) -> int:
    """Main entry point.

    Args:
        argv: Command-line arguments (None = use sys.argv).

    Returns:
        Exit code (0 = success, 1 = error, 2 = argument error, 130 = interrupted).
    """
    if argv is None:
        argv = sys.argv[1:]

    args = parse_args(argv)

    # Read stdin if it's a pipe (not a TTY)
    paths = list(args.paths)
    if not sys.stdin.isatty():
        for line in sys.stdin:
            line = line.strip()
            if line:
                paths.append(line)

    if not paths:
        # No input — show help and exit
        print("error: no input paths specified", file=sys.stderr)
        print(
            "Usage: file-hash-calculator PATH [PATH...]",
            file=sys.stderr,
        )
        return 2

    # Resolve and deduplicate paths
    resolved_paths = _resolve_paths(paths)

    # Validate hash length
    if args.hash_length <= 0:
        print(
            "error: --hash-length must be a positive integer",
            file=sys.stderr,
        )
        return 2

    hash_length_bytes = args.hash_length // 8
    if args.hash_length % 8 != 0:
        print(
            "warning: --hash-length rounded down to "
            f"{hash_length_bytes * 8} bits",
            file=sys.stderr,
        )

    # Collect all files and directories
    all_files, all_dirs = _collect_paths(resolved_paths, args.exclude)

    if not all_files and not all_dirs:
        print("error: no valid files or directories found", file=sys.stderr)
        return 1

    # Determine output format and destination
    output_format = args.format
    output_file: Optional[TextIO] = None
    checkpoint_manager: Optional[CheckpointManager] = None

    try:
        if args.output:
            # Infer format from extension if not explicitly set
            output_format = _infer_format(args.output, args.format)

            # Check if output file exists and is non-empty
            if os.path.exists(args.output) and os.path.getsize(args.output) > 0:
                print(
                    f"warning: output file '{args.output}' already exists "
                    "and is not empty",
                    file=sys.stderr,
                )
                response = input("Overwrite? (y/N): ").strip().lower()
                if response not in ("y", "yes"):
                    print("Aborted.", file=sys.stderr)
                    return 1

            # Set up checkpoint manager
            checkpoint_manager = CheckpointManager(args.output)

            # Load existing checkpoint if available
            completed: dict[str, HashEntry] = {}
            if checkpoint_manager.exists():
                checkpoint_entries = checkpoint_manager.load()
                for cp_entry in checkpoint_entries:
                    if not is_stale(cp_entry):
                        completed[cp_entry.path] = HashEntry(
                            path=cp_entry.path,
                            name=cp_entry.name,
                            hash=cp_entry.hash,
                            entry_type=cp_entry.entry_type,
                            mtime=cp_entry.mtime,
                            size=cp_entry.size,
                        )

            # Filter out already-completed entries
            remaining_files = [
                f for f in all_files if f not in completed
            ]
            remaining_dirs = [
                d for d in all_dirs if d not in completed
            ]

            if len(completed) > 0:
                print(
                    f"info: resuming from checkpoint — "
                    f"{len(completed)} entries already completed, "
                    f"{len(remaining_files) + len(remaining_dirs)} remaining",
                    file=sys.stderr,
                )
        else:
            remaining_files = all_files
            remaining_dirs = all_dirs
            completed = {}

        # Set up progress bar
        total = len(remaining_files) + len(remaining_dirs)
        progress = ProgressBar(total=total) if total > 0 else None

        if progress:
            progress.start()

        # Compute hashes
        new_results: list[HashEntry] = []
        interrupted = False

        def on_entry_complete(entry_path: str):
            if progress:
                progress.update()

        def on_checkpoint(entry: HashEntry):
            if checkpoint_manager:
                checkpoint_manager.append(entry)

        try:
            results = compute_hashes(
                file_paths=remaining_files,
                dir_paths=remaining_dirs,
                hash_length=hash_length_bytes,
                max_workers=args.workers,
                progress_callback=on_entry_complete,
                checkpoint_callback=on_checkpoint,
            )
            new_results = results
        except KeyboardInterrupt:
            interrupted = True
            if checkpoint_manager:
                checkpoint_manager.flush()
            if progress:
                progress.close()
            print("\nInterrupted (Ctrl+C)", file=sys.stderr)
            return 130

        if progress:
            progress.close()

        # Merge completed (from checkpoint) with new results
        all_results = list(completed.values()) + new_results

        if not all_results:
            return 1

        # Write output
        if args.output and checkpoint_manager:
            # Write all results through checkpoint manager for final output
            checkpoint_manager.finalize(
                all_results, output_format, hash_length_bytes
            )
        elif args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                format_output(all_results, f, fmt=output_format)
        else:
            format_output(all_results, sys.stdout, fmt=output_format)

        return 0

    except Exception as e:
        print(f"error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
