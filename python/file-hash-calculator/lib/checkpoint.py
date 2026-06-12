"""Checkpoint/resume management using JSON Lines format.

Writes a .checkpoint.jsonl file alongside the output file. Each line is a
JSON-serialized CheckpointEntry. Supports incremental append and flush for
crash safety, and loading for resume.
"""

import json
import os
from typing import Optional

from .models import HashEntry, CheckpointEntry


class CheckpointManager:
    """Manages checkpoint file I/O for incremental save and resume.

    The checkpoint file is stored at <output_path>.checkpoint.jsonl.
    """

    def __init__(self, output_path: str):
        """Initialize the checkpoint manager.

        Args:
            output_path: Path to the final output file. The checkpoint file
                will be at <output_path>.checkpoint.jsonl.
        """
        self._output_path = output_path
        self._checkpoint_path = output_path + ".checkpoint.jsonl"
        self._file: Optional[object] = None

    @property
    def checkpoint_path(self) -> str:
        """Get the checkpoint file path."""
        return self._checkpoint_path

    def exists(self) -> bool:
        """Check if a checkpoint file exists and is non-empty."""
        return (
            os.path.exists(self._checkpoint_path)
            and os.path.getsize(self._checkpoint_path) > 0
        )

    def _ensure_open(self):
        """Ensure the checkpoint file is open for appending."""
        if self._file is None:
            self._file = open(self._checkpoint_path, "a", encoding="utf-8")

    def append(self, entry: HashEntry) -> None:
        """Append a single HashEntry to the checkpoint file and flush.

        Args:
            entry: The HashEntry to append.
        """
        self._ensure_open()
        cp_entry = CheckpointEntry.from_hash_entry(entry)
        self._file.write(json.dumps(cp_entry.to_dict(), ensure_ascii=False))
        self._file.write("\n")
        self._file.flush()

    def flush(self) -> None:
        """Flush the checkpoint file to disk."""
        if self._file:
            self._file.flush()

    def load(self) -> list[CheckpointEntry]:
        """Load all entries from the checkpoint file.

        Returns:
            List of CheckpointEntry objects. Invalid lines are silently
            skipped.
        """
        entries: list[CheckpointEntry] = []
        if not os.path.exists(self._checkpoint_path):
            return entries

        with open(self._checkpoint_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    entries.append(CheckpointEntry.from_dict(data))
                except (json.JSONDecodeError, KeyError):
                    # Skip corrupted lines
                    continue

        return entries

    def close(self) -> None:
        """Close the checkpoint file."""
        if self._file:
            self._file.close()
            self._file = None

    def finalize(
        self,
        all_entries: list[HashEntry],
        fmt: str,
        hash_length: int,
    ) -> None:
        """Write final output and clean up the checkpoint file.

        Writes all entries in the requested format to the output file,
        then deletes the checkpoint file.

        Args:
            all_entries: Complete list of HashEntry objects.
            fmt: Output format string.
            hash_length: Hash length in bytes.
        """
        from .formatter import format_output

        self.close()

        with open(self._output_path, "w", encoding="utf-8") as f:
            format_output(all_entries, f, fmt=fmt)

        # Remove checkpoint file on successful completion
        if os.path.exists(self._checkpoint_path):
            os.remove(self._checkpoint_path)


def load_checkpoint(
    checkpoint_path: str,
) -> dict[str, CheckpointEntry]:
    """Load a checkpoint file and return a mapping from path to entry.

    Args:
        checkpoint_path: Path to the .checkpoint.jsonl file.

    Returns:
        Dict mapping absolute paths to CheckpointEntry objects.
    """
    manager = CheckpointManager(
        checkpoint_path.replace(".checkpoint.jsonl", "")
    )
    entries = manager.load()
    return {entry.path: entry for entry in entries}


def is_stale(entry: CheckpointEntry) -> bool:
    """Check if a checkpoint entry is stale (file has changed).

    Compares the current file mtime and size against the checkpoint record.

    Args:
        entry: The checkpoint entry to check.

    Returns:
        True if the file has changed since the checkpoint was created
        (i.e., needs re-computation).
    """
    if not os.path.exists(entry.path):
        return True

    try:
        stat = os.stat(entry.path)
    except OSError:
        return True

    return stat.st_mtime != entry.mtime or stat.st_size != entry.size
