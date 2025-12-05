"""
Extract bibkeys for authors from bibliography and compute closures.

This script combines two steps:
1. Extract direct bibkeys where author_ids matches (bootstrap)
2. Look up further_references and depends_on from precomputed closures (lookup)

Based on author_references_bootstrap.py and closed_deps_lookup.py
"""

import csv
import polars as pl
from pathlib import Path
from typing import Dict, FrozenSet, Generator, Tuple
from src.sdk.ResultMonad import light_error_handler, main_try_except_wrapper
from src.sdk.utils import get_logger, lginf, remove_extra_whitespace

lgr = get_logger("Author References Extractor")
DEBUG = True

type TBibkey = str
type TAuthorID = str
type TAuthorName = str

type TBibliographyMap = Dict[
    TBibkey,  # unique identifier of the bibliographic entry
    FrozenSet[TAuthorID],  # author_ids of the bibliographic entry
]

type TClosuresMap = Dict[
    TBibkey,
    Tuple[FrozenSet[TBibkey], FrozenSet[TBibkey]],  # (further_references, depends_on)
]

type TAuthor = Tuple[TAuthorID, TAuthorName]

type TAuthorWithReferences = Tuple[
    TAuthorID,
    TAuthorName,
    FrozenSet[TBibkey],  # main_bibkeys
    FrozenSet[TBibkey],  # further_references
    FrozenSet[TBibkey],  # depends_on
]


@light_error_handler(DEBUG)
def _parse_biblio_authors(author_ids_s: str) -> FrozenSet[TAuthorID]:
    """Parse comma-separated author IDs."""
    if not author_ids_s or author_ids_s.strip() == "" or author_ids_s == "None":
        return frozenset()
    return frozenset(remove_extra_whitespace(author_id) for author_id in author_ids_s.split(","))


@light_error_handler(DEBUG)
def _load_bibliography_map_ods(bibliography_file_ods: str) -> TBibliographyMap:
    """Load mapping of bibkey -> author_ids from bibliography ODS."""
    # Force all columns as strings to avoid null type issues
    df = pl.read_ods(bibliography_file_ods, has_header=True, drop_empty_rows=True, infer_schema_length=0)

    required_columns = ["bibkey", "author_ids"]
    if missing_columns := [col for col in required_columns if col not in df.columns]:
        raise ValueError(f"Fatal error! Missing columns in bibliography ODS: {missing_columns}")

    # Parse author_ids as comma-separated integers
    biblio_map = {
        f"{bibkey}": _parse_biblio_authors(f"{author_ids}")
        for bibkey, author_ids in zip(df["bibkey"].to_list(), df["author_ids"].to_list())
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


def load_bibliography_and_closures(
    bibliography_file: str, closures_file: str
) -> Tuple[TBibliographyMap, TClosuresMap]:
    """Load both bibliography mapping and precomputed closures."""
    frame = "load_bibliography_and_closures"

    lginf(frame, f"Loading bibliography from '{bibliography_file}'...", lgr)
    biblio_map = _load_bibliography_map_ods(bibliography_file)
    lginf(frame, f"Loaded {len(biblio_map)} bibliography entries with author_ids", lgr)

    lginf(frame, f"Loading closures from '{closures_file}'...", lgr)
    closures_map = _load_closures_map_tsv(closures_file)
    lginf(frame, f"Loaded {len(closures_map)} closure entries", lgr)

    return biblio_map, closures_map


@light_error_handler(DEBUG)
def _load_authors_csv(authors_file: str, encoding: str) -> Generator[TAuthor, None, None]:
    """Load authors from CSV file."""
    with open(authors_file, "r", encoding=encoding) as f:
        reader = csv.DictReader(f)

        required_columns = ["id", "_biblio_name"]
        if reader.fieldnames is None or not all(col in reader.fieldnames for col in required_columns):
            raise ValueError(f"CSV must have columns: {', '.join(required_columns)}")

        for row in reader:
            yield (remove_extra_whitespace(f"{row['id']}"), remove_extra_whitespace(f"{row['_biblio_name']}"))


def load_authors(authors_file: str, encoding: str) -> Generator[TAuthor, None, None]:
    """Load authors from file."""
    frame = "load_authors"

    path = Path(authors_file)
    if not path.exists():
        raise FileNotFoundError(f"File '{authors_file}' not found.")

    extension = path.suffix
    if extension != ".csv":
        raise ValueError(f"Only CSV files supported. Got '{extension}'")

    lginf(frame, f"Loading authors from '{authors_file}'...", lgr)
    authors = _load_authors_csv(authors_file, encoding)

    return authors


def process_author(
    author: TAuthor,
    biblio_map: TBibliographyMap,
    closures_map: TClosuresMap,
) -> TAuthorWithReferences:
    """Extract bibkeys and closures for an author."""
    author_id, author_name = author

    # Step 1: Find all bibkeys where author_id is in the author_ids set
    main_bibkeys = frozenset(bibkey for bibkey, author_ids in biblio_map.items() if author_id in author_ids)

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

    return (author_id, author_name, main_bibkeys, further_references, depends_on)


@light_error_handler(DEBUG)
def _write_output_csv(
    result: Generator[TAuthorWithReferences, None, None],
    output_file: str,
    encoding: str,
    original_authors: list[dict],
) -> None:
    """Write output CSV preserving original column order, mapping to existing column names."""
    # Convert result to dict keyed by author_id
    result_dict = {
        author_id: {
            "biblio_keys": ", ".join(sorted(main_bibkeys)),
            "biblio_keys_further_references": ", ".join(sorted(further_references)),
            "biblio_dependencies_keys": ", ".join(sorted(depends_on)),
        }
        for author_id, _, main_bibkeys, further_references, depends_on in result
    }

    # Preserve original row order and update existing columns
    output_rows = []
    for orig_row in original_authors:
        author_id = remove_extra_whitespace(f"{orig_row['id']}")
        new_row = dict(orig_row)  # Copy original columns
        if author_id in result_dict:
            # Update the existing columns
            new_row["biblio_keys"] = result_dict[author_id]["biblio_keys"]
            new_row["biblio_keys_further_references"] = result_dict[author_id]["biblio_keys_further_references"]
            new_row["biblio_dependencies_keys"] = result_dict[author_id]["biblio_dependencies_keys"]
        else:
            # Author has no bibkeys - clear the columns
            new_row["biblio_keys"] = ""
            new_row["biblio_keys_further_references"] = ""
            new_row["biblio_dependencies_keys"] = ""
        output_rows.append(new_row)

    # Write with original columns (no new columns added)
    fieldnames = list(original_authors[0].keys())

    with open(output_file, "w", newline="", encoding=encoding) as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(output_rows)


def write_output(
    result: Generator[TAuthorWithReferences, None, None],
    output_file: str,
    encoding: str,
    original_authors_file: str,
) -> None:
    """Write output preserving original CSV structure."""
    # Load original authors to preserve column order
    with open(original_authors_file, "r", encoding=encoding) as f:
        original_authors = list(csv.DictReader(f))

    path = Path(output_file)
    if path.exists():
        lgr.warning(f"Output file '{output_file}' already exists. Overwriting...")

    _write_output_csv(result, output_file, encoding, original_authors)


@main_try_except_wrapper(lgr)
def main(
    authors_file: str,
    bibliography_file: str,
    closures_file: str,
    output_file: str,
    encoding: str,
) -> None:
    """Main function to extract author bibkeys and closures."""
    frame = "main"

    # Load data
    biblio_map, closures_map = load_bibliography_and_closures(bibliography_file, closures_file)
    authors = load_authors(authors_file, encoding)

    # Process
    lginf(frame, "Processing authors...", lgr)
    result = (process_author(author, biblio_map, closures_map) for author in authors)

    # Write output
    lginf(frame, f"Writing output to '{output_file}'...", lgr)
    write_output(result, output_file, encoding, authors_file)

    lginf(frame, "Done!", lgr)


def cli() -> None:
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Extract bibkeys and closures for authors")
    parser.add_argument("-a", "--authors-file", required=True, help="Authors CSV file")
    parser.add_argument("-b", "--bibliography-file", required=True, help="Bibliography ODS file")
    parser.add_argument("-c", "--closures-file", required=True, help="Closures TSV file")
    parser.add_argument("-o", "--output-file", required=True, help="Output CSV file")
    parser.add_argument("-e", "--encoding", default="utf-8", help="CSV encoding (default: utf-8)")

    args = parser.parse_args()

    main(
        authors_file=args.authors_file,
        bibliography_file=args.bibliography_file,
        closures_file=args.closures_file,
        output_file=args.output_file,
        encoding=args.encoding,
    )


if __name__ == "__main__":
    cli()
