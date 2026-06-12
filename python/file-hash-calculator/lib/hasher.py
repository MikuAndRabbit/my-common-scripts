"""BLAKE3 hash computation for files and directories."""

import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional

import blake3

from .models import HashEntry


CHUNK_SIZE = 64 * 1024  # 64KB


def _compute_file_hash(
    file_path: str, hash_length: int = 32
) -> HashEntry:
    """Compute BLAKE3 hash for a single file using streaming reads.

    Args:
        file_path: Absolute path to the file.
        hash_length: Output hash length in bytes (default 32 = 256-bit).

    Returns:
        HashEntry with the computed hash and file metadata.
    """
    stat = os.stat(file_path)
    hasher = blake3.blake3()

    with open(file_path, "rb") as f:
        while True:
            chunk = f.read(CHUNK_SIZE)
            if not chunk:
                break
            hasher.update(chunk)

    hex_digest = hasher.hexdigest(length=hash_length)

    return HashEntry(
        path=file_path,
        name=os.path.basename(file_path),
        hash=hex_digest,
        entry_type="file",
        mtime=stat.st_mtime,
        size=stat.st_size,
    )


def _compute_dir_hash(
    dir_path: str,
    child_entries: list[HashEntry],
    hash_length: int = 32,
) -> HashEntry:
    """Compute BLAKE3 hash for a directory from its children's hashes.

    Directory hash = BLAKE3(sorted_child_hashes joined by '#').
    Empty directories hash = BLAKE3("").

    Args:
        dir_path: Absolute path to the directory.
        child_entries: HashEntry objects for all direct children (files and
            subdirectories) of this directory.
        hash_length: Output hash length in bytes.

    Returns:
        HashEntry with the computed directory hash.
    """
    stat = os.stat(dir_path)

    if not child_entries:
        # Empty directory
        hex_digest = blake3.blake3(b"").hexdigest(length=hash_length)
    else:
        # Sort child hashes for determinism
        sorted_hashes = sorted(entry.hash for entry in child_entries)
        combined = "#".join(sorted_hashes)
        hex_digest = blake3.blake3(combined.encode("utf-8")).hexdigest(
            length=hash_length
        )

    return HashEntry(
        path=dir_path,
        name=os.path.basename(dir_path),
        hash=hex_digest,
        entry_type="directory",
        mtime=stat.st_mtime,
        size=0,
    )


def compute_hashes(
    file_paths: list[str],
    dir_paths: list[str],
    hash_length: int = 32,
    max_workers: int = 1,
    progress_callback=None,
    checkpoint_callback=None,
) -> list[HashEntry]:
    """Compute BLAKE3 hashes for files and directories.

    Files are hashed directly. Directories are hashed bottom-up: file
    children first, then subdirectory children, then the directory itself.

    Args:
        file_paths: List of absolute file paths to hash.
        dir_paths: List of absolute directory paths to hash.
        hash_length: Output hash length in bytes (default 32 = 256-bit).
        max_workers: Number of worker threads for parallel file hashing.
        progress_callback: Optional callable(path) called after each entry.
        checkpoint_callback: Optional callable(HashEntry) called to save
            checkpoint after each entry.

    Returns:
        List of HashEntry objects in computation order.
    """
    results: list[HashEntry] = []

    # Group files by their parent directory for bottom-up computation
    # Build a mapping: dir_path -> list of direct child files
    dir_files: dict[str, list[str]] = {}
    all_files: list[str] = list(file_paths)

    for dir_path in dir_paths:
        dir_files[dir_path] = []
        # Find files that are direct children of this directory
        for fp in file_paths:
            parent = os.path.dirname(fp)
            if parent == dir_path:
                dir_files[dir_path].append(fp)
            # Also check if file is in a subdirectory of dir_path
            elif fp.startswith(dir_path + os.sep):
                # These will be handled when processing their direct parent dir
                pass

    # Process all files with thread pool
    all_hashes: dict[str, HashEntry] = {}

    def hash_file(fp: str) -> HashEntry:
        entry = _compute_file_hash(fp, hash_length)
        return entry

    if max_workers > 1:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_path = {
                executor.submit(hash_file, fp): fp for fp in all_files
            }
            for future in as_completed(future_to_path):
                entry = future.result()
                all_hashes[entry.path] = entry
                results.append(entry)
                if progress_callback:
                    progress_callback(entry.path)
                if checkpoint_callback:
                    checkpoint_callback(entry)
    else:
        for fp in all_files:
            entry = hash_file(fp)
            all_hashes[entry.path] = entry
            results.append(entry)
            if progress_callback:
                progress_callback(entry.path)
            if checkpoint_callback:
                checkpoint_callback(entry)

    # Process directories bottom-up (by depth, deepest first)
    # Sort dir_paths by depth (deepest first)
    sorted_dirs = sorted(
        dir_paths, key=lambda d: d.count(os.sep), reverse=True
    )

    for dir_path in sorted_dirs:
        # Collect direct children of this directory
        child_entries: list[HashEntry] = []

        # Find direct child files
        for fp in all_files:
            if os.path.dirname(fp) == dir_path and fp in all_hashes:
                child_entries.append(all_hashes[fp])

        # Find direct child directories
        for child_dir in sorted_dirs:
            if os.path.dirname(child_dir) == dir_path:
                # This child dir should already be computed (we're going
                # bottom-up, so deeper dirs are computed first)
                child_entry = _find_entry(results, child_dir)
                if child_entry:
                    child_entries.append(child_entry)

        entry = _compute_dir_hash(dir_path, child_entries, hash_length)
        all_hashes[entry.path] = entry
        results.append(entry)
        if progress_callback:
            progress_callback(entry.path)
        if checkpoint_callback:
            checkpoint_callback(entry)

    # Sort results by path for deterministic output
    results.sort(key=lambda e: e.path)

    return results


def _find_entry(
    entries: list[HashEntry], path: str
) -> Optional[HashEntry]:
    """Find a HashEntry by path in a list."""
    for entry in entries:
        if entry.path == path:
            return entry
    return None
