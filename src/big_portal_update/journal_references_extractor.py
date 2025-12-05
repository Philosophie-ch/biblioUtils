"""
Extract bibkeys for journals from bibliography and compute closures.

This script combines two steps:
1. Extract direct bibkeys where journal-id matches (bootstrap)
2. Look up further_references and depends_on from precomputed closures (lookup)

Based on publisher_references_extractor.py
"""

import csv
import polars as pl
from pathlib import Path
from typing import Dict, FrozenSet, Generator, Tuple
from src.sdk.ResultMonad import light_error_handler, main_try_except_wrapper
from src.sdk.utils import get_logger, lginf, remove_extra_whitespace

lgr = get_logger("Journal References Extractor")
DEBUG = True

type TBibkey = str
type TJournalID = str
type TJournalName = str

type TBibliographyMap = Dict[
    TBibkey,  # unique identifier of the bibliographic entry
    TJournalID,  # journal_id of the bibliographic entry
]

type TClosuresMap = Dict[
    TBibkey,
    Tuple[FrozenSet[TBibkey], FrozenSet[TBibkey]],  # (further_references, depends_on)
]

type TJournal = Tuple[TJournalID, TJournalName]

type TJournalWithReferences = Tuple[
    TJournalID,
    TJournalName,
    FrozenSet[TBibkey],  # main_bibkeys
    FrozenSet[TBibkey],  # further_references
    FrozenSet[TBibkey],  # depends_on
]


@light_error_handler(DEBUG)
def _load_bibliography_map_ods(bibliography_file_ods: str) -> TBibliographyMap:
    """Load mapping of bibkey -> journal-id from bibliography ODS."""
    # Force all columns as strings to avoid null type issues
    df = pl.read_ods(bibliography_file_ods, has_header=True, drop_empty_rows=True, infer_schema_length=0)

    required_columns = ["bibkey", "journal-id"]
    if missing_columns := [col for col in required_columns if col not in df.columns]:
        raise ValueError(f"Fatal error! Missing columns in bibliography ODS: {missing_columns}")

    # Filter out empty journal-ids and create mapping
    biblio_map = {
        f"{bibkey}": f"{journal_id}"
        for bibkey, journal_id in zip(df["bibkey"].to_list(), df["journal-id"].to_list())
        if journal_id and f"{journal_id}".strip() and f"{journal_id}" != "None"  # Only include entries with journal-id
    }

    return biblio_map


@light_error_handler(DEBUG)
def _load_closures_map_tsv(closures_file_tsv: str) -> TClosuresMap:
    """Load precomputed closures from TSV file."""
    df = pl.read_csv(closures_file_tsv, separator="\t", has_header=True)

    required_columns = ["bibkey", "_further-references", "_depends-on"]
    if missing_columns := [col for col in required_columns if col not in df.columns]:
        raise ValueError(f"Fatal error! Missing columns in closures TSV: {missing_columns}")

    closures_map = {
        bibkey: (
            frozenset(remove_extra_whitespace(ref) for ref in further_refs.split(",") if ref and ref.strip()),
            frozenset(remove_extra_whitespace(ref) for ref in depends_on.split(",") if ref and ref.strip()),
        )
        for bibkey, further_refs, depends_on in zip(
            df["bibkey"].to_list(),
            df["_further-references"].fill_null("").to_list(),
            df["_depends-on"].fill_null("").to_list(),
        )
    }

    return closures_map


def load_bibliography_and_closures(bibliography_file: str, closures_file: str) -> Tuple[TBibliographyMap, TClosuresMap]:
    """Load both bibliography mapping and precomputed closures."""
    frame = "load_bibliography_and_closures"

    lginf(frame, f"Loading bibliography from '{bibliography_file}'...", lgr)
    biblio_map = _load_bibliography_map_ods(bibliography_file)
    lginf(frame, f"Loaded {len(biblio_map)} bibliography entries with journal-id", lgr)

    lginf(frame, f"Loading closures from '{closures_file}'...", lgr)
    closures_map = _load_closures_map_tsv(closures_file)
    lginf(frame, f"Loaded {len(closures_map)} closure entries", lgr)

    return biblio_map, closures_map


@light_error_handler(DEBUG)
def _load_journals_csv(journals_file: str, encoding: str) -> Generator[TJournal, None, None]:
    """Load journals from CSV file."""
    with open(journals_file, "r", encoding=encoding) as f:
        reader = csv.DictReader(f)

        required_columns = ["id", "name"]
        if reader.fieldnames is None or not all(col in reader.fieldnames for col in required_columns):
            raise ValueError(f"CSV must have columns: {', '.join(required_columns)}")

        for row in reader:
            yield (remove_extra_whitespace(f"{row['id']}"), remove_extra_whitespace(f"{row['name']}"))


def load_journals(journals_file: str, encoding: str) -> Generator[TJournal, None, None]:
    """Load journals from file."""
    frame = "load_journals"

    path = Path(journals_file)
    if not path.exists():
        raise FileNotFoundError(f"File '{journals_file}' not found.")

    extension = path.suffix
    if extension != ".csv":
        raise ValueError(f"Only CSV files supported. Got '{extension}'")

    lginf(frame, f"Loading journals from '{journals_file}'...", lgr)
    journals = _load_journals_csv(journals_file, encoding)

    return journals


def process_journal(
    journal: TJournal,
    biblio_map: TBibliographyMap,
    closures_map: TClosuresMap,
) -> TJournalWithReferences:
    """Extract bibkeys and closures for a journal."""
    journal_id, journal_name = journal

    # Step 1: Find all bibkeys where journal-id matches
    main_bibkeys = frozenset(bibkey for bibkey, jnl_id in biblio_map.items() if jnl_id == journal_id)

    # Step 2: Look up closures for each main bibkey
    further_refs_nested = []
    depends_on_nested = []

    for bibkey in main_bibkeys:
        if bibkey in closures_map:
            further_refs, depends_on = closures_map[bibkey]
            further_refs_nested.append(further_refs)
            depends_on_nested.append(depends_on)

    # Step 3: Aggregate all closures
    further_references = frozenset(ref for refs in further_refs_nested for ref in refs)
    depends_on = frozenset(ref for refs in depends_on_nested for ref in refs)

    return (journal_id, journal_name, main_bibkeys, further_references, depends_on)


@light_error_handler(DEBUG)
def _write_output_csv(
    result: Generator[TJournalWithReferences, None, None],
    output_file: str,
    encoding: str,
    original_journals: list[Dict[str, str]],
) -> None:
    """Write output CSV preserving original column order, mapping to existing column names."""
    # Convert result to dict keyed by journal_id
    result_dict = {
        journal_id: {
            "_references_keys": ", ".join(sorted(main_bibkeys)),
            "_further_references_keys": ", ".join(sorted(further_references)),
            "_references_dependencies_keys": ", ".join(sorted(depends_on)),
        }
        for journal_id, _, main_bibkeys, further_references, depends_on in result
    }

    # Preserve original row order and update existing columns
    output_rows = []
    for orig_row in original_journals:
        jnl_id = remove_extra_whitespace(f"{orig_row['id']}")
        new_row = dict(orig_row)  # Copy original columns
        if jnl_id in result_dict:
            # Update the existing columns
            new_row["_references_keys"] = result_dict[jnl_id]["_references_keys"]
            new_row["_further_references_keys"] = result_dict[jnl_id]["_further_references_keys"]
            new_row["_references_dependencies_keys"] = result_dict[jnl_id]["_references_dependencies_keys"]
        else:
            # Journal has no bibkeys - clear the columns
            new_row["_references_keys"] = ""
            new_row["_further_references_keys"] = ""
            new_row["_references_dependencies_keys"] = ""
        output_rows.append(new_row)

    # Write with original columns (no new columns added)
    fieldnames = list(original_journals[0].keys())

    with open(output_file, "w", newline="", encoding=encoding) as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(output_rows)


def write_output(
    result: Generator[TJournalWithReferences, None, None],
    output_file: str,
    encoding: str,
    original_journals_file: str,
) -> None:
    """Write output preserving original CSV structure."""
    # Load original journals to preserve column order
    with open(original_journals_file, "r", encoding=encoding) as f:
        original_journals = list(csv.DictReader(f))

    path = Path(output_file)
    if path.exists():
        lgr.warning(f"Output file '{output_file}' already exists. Overwriting...")

    _write_output_csv(result, output_file, encoding, original_journals)


@main_try_except_wrapper(lgr)
def main(
    journals_file: str,
    bibliography_file: str,
    closures_file: str,
    output_file: str,
    encoding: str,
) -> None:
    """Main function to extract journal bibkeys and closures."""
    frame = "main"

    # Load data
    biblio_map, closures_map = load_bibliography_and_closures(bibliography_file, closures_file)
    journals = load_journals(journals_file, encoding)

    # Process
    lginf(frame, "Processing journals...", lgr)
    result = (process_journal(jnl, biblio_map, closures_map) for jnl in journals)

    # Write output
    lginf(frame, f"Writing output to '{output_file}'...", lgr)
    write_output(result, output_file, encoding, journals_file)

    lginf(frame, "Done!", lgr)


def cli() -> None:
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Extract bibkeys and closures for journals")
    parser.add_argument("-j", "--journals-file", required=True, help="Journals CSV file")
    parser.add_argument("-b", "--bibliography-file", required=True, help="Bibliography ODS file")
    parser.add_argument("-c", "--closures-file", required=True, help="Closures TSV file")
    parser.add_argument("-o", "--output-file", required=True, help="Output CSV file")
    parser.add_argument("-e", "--encoding", default="utf-8", help="CSV encoding (default: utf-8)")

    args = parser.parse_args()

    main(
        journals_file=args.journals_file,
        bibliography_file=args.bibliography_file,
        closures_file=args.closures_file,
        output_file=args.output_file,
        encoding=args.encoding,
    )


if __name__ == "__main__":
    cli()
