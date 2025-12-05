"""
Truncate cells longer than 49000 characters for Google Sheets compatibility.
"""

import csv
from pathlib import Path
from src.sdk.utils import get_logger

lgr = get_logger("Truncate Long Cells")
MAX_CELL_LENGTH = 49000


def truncate_long_cells(input_file: str, output_file: str, encoding: str) -> None:
    """Truncate any cells longer than MAX_CELL_LENGTH to [TOO LONG]."""

    with open(input_file, "r", encoding=encoding) as f_in:
        reader = csv.DictReader(f_in)
        fieldnames = reader.fieldnames

        rows = []
        long_cells_count = 0
        affected_ids = []

        for row in reader:
            new_row = {}
            for key, value in row.items():
                if len(value) > MAX_CELL_LENGTH:
                    new_row[key] = "[TOO LONG]"
                    long_cells_count += 1
                    if 'id' in row:
                        affected_ids.append((row['id'], key))
                else:
                    new_row[key] = value
            rows.append(new_row)

    with open(output_file, "w", newline="", encoding=encoding) as f_out:
        writer = csv.DictWriter(f_out, fieldnames=fieldnames or [])
        writer.writeheader()
        writer.writerows(rows)

    lgr.info(f"Truncated {long_cells_count} cells to [TOO LONG]")
    if affected_ids:
        lgr.info(f"Affected IDs: {affected_ids[:10]}")  # Show first 10


def cli() -> None:
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Truncate long cells for Google Sheets")
    parser.add_argument("-i", "--input-file", required=True, help="Input CSV file")
    parser.add_argument("-o", "--output-file", required=True, help="Output CSV file")
    parser.add_argument("-e", "--encoding", default="utf-8", help="CSV encoding (default: utf-8)")

    args = parser.parse_args()

    truncate_long_cells(args.input_file, args.output_file, args.encoding)


if __name__ == "__main__":
    cli()
