"""Data models for file-hash-calculator."""

from dataclasses import dataclass
from typing import Literal


EntryType = Literal["file", "directory"]


@dataclass
class HashEntry:
    """Represents the hash result of a single file or directory.

    Attributes:
        path: Absolute path to the file/directory.
        name: File/directory name (without parent path).
        hash: BLAKE3 hash value as a hex string.
        entry_type: Either "file" or "directory".
        mtime: File modification time (Unix timestamp).
        size: File size in bytes (0 for directories).
    """

    path: str
    name: str
    hash: str
    entry_type: EntryType
    mtime: float
    size: int

    def to_dict(self) -> dict:
        """Convert to a plain dict for serialization."""
        return {
            "path": self.path,
            "name": self.name,
            "hash": self.hash,
            "entry_type": self.entry_type,
            "mtime": self.mtime,
            "size": self.size,
        }


@dataclass
class CheckpointEntry:
    """Represents a completed hash record for resume/checkpoint.

    Attributes:
        path: Absolute path to the file/directory (primary key).
        hash: BLAKE3 hash value.
        entry_type: "file" or "directory".
        name: File/directory name.
        mtime: Recorded modification time for staleness detection.
        size: Recorded file size for staleness detection.
    """

    path: str
    hash: str
    entry_type: str
    name: str
    mtime: float
    size: int

    @classmethod
    def from_hash_entry(cls, entry: HashEntry) -> "CheckpointEntry":
        """Create a CheckpointEntry from a HashEntry."""
        return cls(
            path=entry.path,
            hash=entry.hash,
            entry_type=entry.entry_type,
            name=entry.name,
            mtime=entry.mtime,
            size=entry.size,
        )

    @classmethod
    def from_dict(cls, data: dict) -> "CheckpointEntry":
        """Create a CheckpointEntry from a deserialized dict."""
        return cls(
            path=data["path"],
            hash=data["hash"],
            entry_type=data["entry_type"],
            name=data["name"],
            mtime=data["mtime"],
            size=data["size"],
        )

    def to_dict(self) -> dict:
        """Convert to a plain dict for serialization."""
        return {
            "path": self.path,
            "hash": self.hash,
            "entry_type": self.entry_type,
            "name": self.name,
            "mtime": self.mtime,
            "size": self.size,
        }
