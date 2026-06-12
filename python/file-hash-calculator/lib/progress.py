"""Progress bar wrapper using tqdm."""

import sys
from typing import Optional


class ProgressBar:
    """Simple progress bar wrapper around tqdm.

    Outputs to stderr to avoid interfering with stdout/file output.
    """

    def __init__(self, total: int, desc: str = "Computing hashes"):
        """Initialize the progress bar.

        Args:
            total: Total number of items to process.
            desc: Description text shown before the progress bar.
        """
        self._total = max(total, 0)

        # Lazy import tqdm to avoid import errors if not installed
        from tqdm import tqdm

        self._bar: Optional[tqdm] = tqdm(
            total=self._total,
            desc=desc,
            unit="entries",
            file=sys.stderr,
            disable=self._total == 0,
        )

    def start(self) -> None:
        """Start the progress bar (no-op, it starts on creation)."""
        pass

    def update(self, n: int = 1) -> None:
        """Update the progress bar by n steps.

        Args:
            n: Number of steps to advance.
        """
        if self._bar and not self._bar.disable:
            self._bar.update(n)

    def close(self) -> None:
        """Close the progress bar."""
        if self._bar:
            self._bar.close()
