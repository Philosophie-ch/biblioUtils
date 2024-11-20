"""
Script to find duplicate bibkeys in Philosophie.ch's bibliography.

Divided by different functions, the script is as follows:
- `load_bibkeys` simply reads the bibliography file and returns a tuple of bibkeys. Uses polars to read from a ODS file.
- `find_duplicates` gets a list of bibkeys as input and returns a list of duplicates, and their positions in the original list.
- `main` is the entry point of the script, and it calls the other functions.
- `cli` imports argparse and defines the arguments that the script will receive:
    + `-b` or `--bibliography` is the file containing the bibliography. Supported format: ODS only.
    + `-o` or `--output` is the file where the duplicates will be written. Supported format: ODS only.
"""

from pathlib import Path
from typing import Tuple
import polars as pl
import csv

from src.sdk.ResultMonad import Err, try_except_wrapper
from src.sdk.utils import get_logger

lgr = get_logger("Duplicate Bibkeys Finder")


type TBibkeys = Tuple[str]


def load_bibkeys(bibliography_file: str) -> TBibkeys:

    path = Path(bibliography_file)
    if not path.exists():
        raise FileNotFoundError("The bibliography file does not exist.")

    extension = path.suffix

    match extension:
        case ".ods":
            df = pl.read_ods(bibliography_file, has_header=True, drop_empty_rows=True)
            bibkeys_l = df['bibkey'].to_list()
            bibkeys = tuple(bibkeys_l)

        case _:
            raise ValueError(f"Format '{extension}' not supported. Only ODS files are supported.")

    return bibkeys


type TDuplicate = Tuple[str, int]
type TDuplicates = Tuple[TDuplicate, ...]


def find_duplicates(bibkeys: TBibkeys) -> TDuplicates | None:

    counts: dict[str, list[int]] = {}
    for idx, bibkey in enumerate(bibkeys):
        if bibkey in counts:
            counts[bibkey].append(idx)
        else:
            counts[bibkey] = [idx]

    # Identify duplicates
    duplicates = tuple((bibkey, idx) for bibkey, indices in counts.items() if len(indices) > 1 for idx in indices)

    return duplicates if duplicates else None


def write_duplicates(output_file: str, duplicates: TDuplicates) -> None:

    path = Path(output_file)
    if not path.exists():
        raise FileNotFoundError("The output file does not exist.")

    extension = path.suffix

    match extension:
        case ".csv":
            with open(output_file, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["bibkey", "position"])
                writer.writerows(duplicates)

        case _:
            raise ValueError(f"Format '{extension}' not supported. Only ODS files are supported.")

    return None


@try_except_wrapper(lgr)
def main(bibliography_file: str, output_file: str) -> None:

    lgr.info(f"Loading bibkeys from '{bibliography_file}'...")
    bibkeys = load_bibkeys(bibliography_file)

    lgr.info("Finding duplicates...")
    duplicates = find_duplicates(bibkeys)

    if duplicates is not None:
        lgr.info(f"Duplicates found! Writing duplicates to '{output_file}'...")
        write_duplicates(output_file, duplicates)

    else:
        lgr.info("No duplicates found. Exiting.")

    return None


def cli() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Find duplicate bibkeys in a bibliography.")

    parser.add_argument(
        "-b",
        "--bibliography",
        type=str,
        help="The file containing the bibliography. Supported format: ODS only.",
        required=True,
    )

    parser.add_argument(
        "-o",
        "--output",
        type=str,
        help="The file where the duplicates will be written. Supported format: CSV only.",
        required=True,
    )

    args = parser.parse_args()

    result = main(args.bibliography, args.output)

    if isinstance(result, Err):
        lgr.error("An error occurred. Please check the logs for more information.")

    return None


if __name__ == "__main__":
    cli()
