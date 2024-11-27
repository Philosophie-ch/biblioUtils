"""
This script processes a CSV file with BibTeX entries and computes the transitive closure of the dependencies between them.
Uses the bootstrap wave of dependencies obtained in the first step, and a custom made Rust crate to compute the transitive closures.
"""

import csv
from datetime import datetime
from typing import Callable
from rust_crate import (
    RustedBibEntry,
    find_all_repeated_bibentries,
    compute_transitive_closures,
)

from src.bib_deps.bib_deps_bootstrap import bib_deps_bootstrap_pipe, get_all_bibkeys, process_bibentry
from src.bib_deps.data_repository import load_bibentries
from src.sdk.ResultMonad import runwrap, try_except_wrapper
from src.bib_deps.models import ParsedBibEntry, ProcessedBibEntry, PyTransitivelyClosedBibEntry
from src.sdk.utils import get_logger, lginf

lgr = get_logger("Biblio Dependencies -- Recursive")


@try_except_wrapper(lgr)
def main_recursive(filename: str, encoding: str | None, output_filename: str) -> None:

    frame = "main_recursive"
    start_datetime = datetime.now()
    ns = 7  # number of steps
    lginf(frame, f"Started at {start_datetime}", lgr)

    lginf(frame, f"Loading bibentries from '{filename}' [1/{ns}]", lgr)
    rows = runwrap(load_bibentries(filename, encoding))

    lginf(frame, f"Getting all bibkeys in the file [2/{ns}]", lgr)
    all_bibkeys = get_all_bibkeys(rows)

    lginf(frame, f"Bootstrapping the entries [3/{ns}]", lgr)
    process_bibentry_curried: Callable[[ParsedBibEntry], ProcessedBibEntry] = lambda x: process_bibentry(x, all_bibkeys)
    processed_rows = (bib_deps_bootstrap_pipe(row, all_bibkeys, process_bibentry_curried) for row in rows)

    rusted_bibentries = [
        RustedBibEntry(
            bibkey=row.bibkey,
            title=row.title,
            notes=row.notes,
            crossref=row.crossref,
            further_note=row.further_note,
            further_references=row.further_references_good.split(","),
            depends_on=row.depends_on_good.split(","),
        )
        for row in processed_rows
    ]

    lginf(frame, f"Finding all repeated bibentries [4/{ns}]", lgr)

    if repeated_bibentries := find_all_repeated_bibentries(rusted_bibentries):
        error_msg = f"Found {len(repeated_bibentries)} repeated bibentries. Exiting..."
        lgr.error(error_msg)
        buffer = [error_msg]
        buffer.extend(f"{entry.bibkey}" for entry in repeated_bibentries)
        with open(f"{output_filename}_error.txt", "w") as f:
            f.write("\n".join(buffer))
        return None

    lginf(frame, f"Computing transitive closures [5/{ns}]", lgr)
    bibentries_with_closures = compute_transitive_closures(rusted_bibentries)

    lginf(frame, f"Getting fieldnames for final CSV [6/{ns}]", lgr)
    fieldnames = list(PyTransitivelyClosedBibEntry.__annotations__.keys())

    lginf(frame, f"Writing the output to '{output_filename}' [7/{ns}]", lgr)
    with open(output_filename, "w", newline="") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        writer.writerows(entry.to_dict() for entry in bibentries_with_closures)

    end_datetime = datetime.now()
    total_time = end_datetime - start_datetime

    lginf(
        frame,
        f"Success! Processed {len(rows)} entries. Finished at {end_datetime}. Total time: {total_time}. Report written to the file below ↴\n\t{output_filename}",
        lgr,
    )

    return None


def cli_main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Process a CSV file with BibTeX entries")

    parser.add_argument(
        "-i",
        "--input-csv",
        type=str,
        help="The file with the data to process. Needs to be either a CSV or an ODS with the following columns: 'bibkey', 'title', 'notes', 'crossref', 'further_note'. If passing a CSV, please also provide the encoding of the file.",
        required=True,
    )

    parser.add_argument("-e", "--encoding", type=str, help="The encoding of the CSV file.", required=False)

    parser.add_argument("-o", "--output-filename", type=str, help="The output CSV file.", required=True)

    args = parser.parse_args()

    main_recursive(args.input_csv, args.encoding, args.output_filename)


if __name__ == "__main__":
    cli_main()
