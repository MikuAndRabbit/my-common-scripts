"""Directory traversal with gitignore-style exclusion support."""

import os
from typing import Optional

from pathspec import PathSpec
from pathspec.patterns import GitWildMatchPattern


class Traverser:
    """Recursively traverses directories, collecting files and subdirectories.

    Returns paths sorted by depth (files first, then directories at each level),
    enabling bottom-up hash computation.
    """

    def __init__(self, exclude_patterns: Optional[list[str]] = None):
        """Initialize the traverser.

        Args:
            exclude_patterns: Optional list of gitignore-style exclusion patterns.
                              Patterns match against relative paths within each
                              traversed directory.
        """
        self._spec: Optional[PathSpec] = None
        if exclude_patterns:
            self._spec = PathSpec.from_lines(
                GitWildMatchPattern, exclude_patterns
            )

    def _should_exclude(
        self, entry_path: str, root_path: str, is_dir: bool
    ) -> bool:
        """Check if a path should be excluded based on patterns.

        Args:
            entry_path: The absolute path to the entry.
            root_path: The root directory being traversed (for relative
                path computation).
            is_dir: Whether the entry is a directory.

        Returns:
            True if the entry should be excluded.
        """
        if self._spec is None:
            return False

        rel_path = os.path.relpath(entry_path, root_path)

        # Also try matching with trailing slash for directory patterns
        if is_dir:
            return self._spec.match_file(rel_path) or self._spec.match_file(
                rel_path + "/"
            )
        return self._spec.match_file(rel_path)

    def traverse(self, root_path: str) -> list[str]:
        """Recursively traverse a directory and return sorted paths.

        Files are listed before directories at each depth level (bottom-up
        order for hash computation). Excluded entries (and their children,
        for excluded directories) are skipped.

        Args:
            root_path: Absolute path to the directory to traverse.

        Returns:
            List of absolute paths sorted by depth (deepest first, files
            before dirs at same depth).
        """
        entries: list[tuple[int, bool, str]] = []
        # (depth, is_file, path) — sort by depth desc, is_file desc

        def _walk(current_path: str, traversal_root: str):
            try:
                with os.scandir(current_path) as it:
                    for dir_entry in it:
                        entry_path = os.path.join(
                            current_path, dir_entry.name
                        )

                        if dir_entry.is_dir(follow_symlinks=False):
                            if self._should_exclude(
                                entry_path, traversal_root, is_dir=True
                            ):
                                continue

                            entries.append(
                                (
                                    entry_path.count(os.sep),
                                    False,
                                    entry_path,
                                )
                            )
                            _walk(entry_path, traversal_root)

                        elif dir_entry.is_file(follow_symlinks=False):
                            if self._should_exclude(
                                entry_path, traversal_root, is_dir=False
                            ):
                                continue

                            entries.append(
                                (
                                    entry_path.count(os.sep),
                                    True,
                                    entry_path,
                                )
                            )
                        # Symlinks are silently skipped
            except PermissionError:
                pass

        _walk(root_path, root_path)

        # Sort: deepest first, files before dirs at same depth
        entries.sort(key=lambda x: (-x[0], -x[1]))

        return [path for _, _, path in entries]
