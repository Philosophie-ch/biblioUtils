import csv
from datetime import datetime
from typing import Callable, Generator
from rust_crate import RustedBibEntry, compute_transitive_closures

from src.bib_deps.bib_deps_bootstrap import bib_deps_bootstrap_pipe, get_all_bibkeys, process_bibentry
from src.bib_deps.csv_repository import load_bibentries_csv
from src.sdk.ResultMonad import runwrap, try_except_wrapper
from src.bib_deps.models import BaseBibEntry, ParsedBibEntry, ProcessedBibEntry, TransitivelyClosedBibEntry, Status
from src.sdk.utils import get_logger, lginf

lgr = get_logger("Biblio Dependencies -- Recursive")

MAX_DEPTH = 10


@try_except_wrapper(lgr)
def rusted_bib_entry_generator(entries: list[RustedBibEntry]) -> Generator[TransitivelyClosedBibEntry, None, None]:
    """
    A Python generator that yields RustedBibEntry objects one at a time,
    where each entry has the computed closures (further_references_closed, depends_on_closed). Uses the `compute_transitive_closures` implemented in Rust for better performance.
    """
    frame = "rusted_bib_entry_generator"
    lginf(frame, f"Processing {len(entries)} entries", lgr)
    # Prepare entries as a dictionary for the Rust function
    entries_dict = {entry.bibkey: entry for entry in entries}

    lginf(frame, "Computing transitive closures", lgr)
    # Call the Rust function to get the computed closures (two dictionaries)
    further_references_memo, depends_on_memo = compute_transitive_closures(entries_dict, MAX_DEPTH)

    lginf(frame, "Success! Now yielding entries with closures", lgr)
    # Yield each entry one by one, with closures filled in
    for entry in entries:
        try:
            bibkey = entry.bibkey
            # Look up the closures for this entry using its bibkey
            further_references_closed = further_references_memo.get(bibkey, set())
            depends_on_closed = depends_on_memo.get(bibkey, set())

            further_references_closed_circularity_flag = False
            depends_on_closed_circularity_flag = False

            if bibkey in further_references_closed:
                lgr.warning(f"Entry '{bibkey}' has a circular reference in 'further_references'.")
                further_references_closed_circularity_flag = True

            if bibkey in depends_on_closed:
                lgr.warning(f"Entry '{bibkey}' has a circular reference in 'depends_on'.")
                depends_on_closed_circularity_flag = True

            circularity_flag = further_references_closed_circularity_flag or depends_on_closed_circularity_flag

            match circularity_flag:
                case True:
                    status: Status = "warning"
                    error_message = f"Circular reference detected.\nFor 'further_references', circular reference is {further_references_closed_circularity_flag}\nFor 'depends_on', circular reference is: {depends_on_closed_circularity_flag}"
                case False:
                    status = "success"
                    error_message = ""

            # Yield the entry with its closures
            yield TransitivelyClosedBibEntry(
                id=entry.id,
                bibkey=entry.bibkey,
                title=entry.title,
                notes=entry.notes,
                crossref=entry.crossref,
                further_note=entry.further_note,
                further_references=",".join(entry.further_references),
                depends_on=",".join(entry.depends_on),
                further_references_closed=",".join(list(filter(None, further_references_closed))),
                depends_on_closed=",".join(list(filter(None, depends_on_closed))),
                status=status,
                error_message=error_message,
            )
        except Exception as e:
            lgr.error(f"Error processing entry '{entry.bibkey}': {e}")
            yield TransitivelyClosedBibEntry(
                id=entry.id,
                bibkey=entry.bibkey,
                title=entry.title,
                notes=entry.notes,
                crossref=entry.crossref,
                further_note=entry.further_note,
                further_references=",".join(entry.further_references),
                depends_on=",".join(entry.depends_on),
                further_references_closed="",
                depends_on_closed="",
                status="error",
                error_message=str(e),
            )


@try_except_wrapper(lgr)
def main_recursive(filename: str, encoding: str, output_filename: str) -> None:

    frame = "main_recursive"
    start_datetime = datetime.now()
    lginf(frame, f"Started at {start_datetime}", lgr)

    lginf(frame, f"Loading bibentries from '{filename}' [1/5]", lgr)
    rows = runwrap(load_bibentries_csv(filename, encoding))

    lginf(frame, "Getting all bibkeys in the file [2/5]", lgr)
    all_bibkeys = get_all_bibkeys(rows)

    lginf(frame, "Processing the entries [3/5]", lgr)
    process_bibentry_curried: Callable[[ParsedBibEntry], ProcessedBibEntry] = lambda x: process_bibentry(x, all_bibkeys)
    processed_rows = (bib_deps_bootstrap_pipe(row, all_bibkeys, process_bibentry_curried) for row in rows)

    lginf(frame, "Computing transitive closures [4/5]", lgr)
    bibentries_with_closures = runwrap(
        rusted_bib_entry_generator(
            [
                RustedBibEntry(
                    id=row.id,
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
        )
    )

    lginf(frame, f"Getting fieldnames for final CSV", lgr)
    fieldnames = list(BaseBibEntry.__annotations__.keys()) + list(TransitivelyClosedBibEntry.__annotations__.keys())

    lginf(frame, f"Writing the output to '{output_filename}' [5/5]", lgr)
    with open(output_filename, "w", newline="") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(entry.dict_dump() for entry in bibentries_with_closures)

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
        help="The CSV file to process. Needs to have the following columns: 'id', 'bibkey', 'title', 'notes', 'crossref', 'further_note'.",
        required=True,
    )

    parser.add_argument("-e", "--encoding", type=str, help="The encoding of the CSV file.", required=True)

    parser.add_argument("-o", "--output-filename", type=str, help="The output CSV file.", required=True)

    args = parser.parse_args()

    main_recursive(args.input_csv, args.encoding, args.output_filename)


if __name__ == "__main__":
    cli_main()
