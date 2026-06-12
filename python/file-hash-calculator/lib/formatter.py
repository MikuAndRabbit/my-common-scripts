"""Output formatting for hash results (Markdown, JSON, CSV, YAML)."""

import csv
import io
import json
from typing import TextIO

import yaml

from .models import HashEntry


def format_markdown(entries: list[HashEntry], output: TextIO) -> None:
    """Write entries as a Markdown table.

    Columns: Path | Name | Hash | Type
    """
    output.write("| Path | Name | Hash | Type |\n")
    output.write("|------|------|------|------|\n")
    for entry in entries:
        output.write(
            f"| {entry.path} | {entry.name} | {entry.hash} "
            f"| {entry.entry_type} |\n"
        )


def format_json(entries: list[HashEntry], output: TextIO) -> None:
    """Write entries as a JSON array."""
    data = [entry.to_dict() for entry in entries]
    json.dump(data, output, indent=2, ensure_ascii=False)
    output.write("\n")


def format_csv(entries: list[HashEntry], output: TextIO) -> None:
    """Write entries as CSV with header."""
    writer = csv.writer(output)
    writer.writerow(["path", "name", "hash", "entry_type"])
    for entry in entries:
        writer.writerow(
            [entry.path, entry.name, entry.hash, entry.entry_type]
        )


def format_yaml(entries: list[HashEntry], output: TextIO) -> None:
    """Write entries as a YAML list."""
    data = [entry.to_dict() for entry in entries]
    yaml.safe_dump(data, output, allow_unicode=True, default_flow_style=False)


FORMATTERS = {
    "markdown": format_markdown,
    "json": format_json,
    "csv": format_csv,
    "yaml": format_yaml,
}


def format_output(
    entries: list[HashEntry],
    output: TextIO,
    fmt: str = "markdown",
) -> None:
    """Format and write hash entries to the given output stream.

    Args:
        entries: List of HashEntry objects.
        output: File-like object to write to.
        fmt: Output format: "markdown", "json", "csv", or "yaml".
    """
    formatter = FORMATTERS.get(fmt)
    if formatter is None:
        raise ValueError(
            f"Unknown format: {fmt}. "
            f"Supported: {', '.join(FORMATTERS.keys())}"
        )
    formatter(entries, output)
