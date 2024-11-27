"""
Assuming we already computed the dependencies of the bib files, and populated the columns `_further_refs` and `_depends_on` in the bibliography already transitively closed, per bibkey. This script simply takes a list of lists of bibkeys, and returns a list of lists of (1) _further_refs all appended, and (2) _depends_on all appended.
"""

import csv
import polars as pl
from pathlib import Path

from typing import Dict, Generator, NamedTuple, Set, Tuple, List, TypedDict
from src.sdk.ResultMonad import runwrap, try_except_wrapper
from src.sdk.utils import get_logger, remove_extra_whitespace


lgr = get_logger("Closed Dependencies Lookup")


type BibentryWithReferences = Tuple[
    # This comes from either (a) the markdown parser to get direct references; or (b) manual compilation in pages in portal data
    str,  # bibkey
    Set[str],  #  direct_references
]

type LoadOutput = Tuple[Tuple[BibentryWithReferences, ...], int]  # tuple of bibentries  # number of bibentries


def load_bibentries_csv(filename: str, encoding: str) -> LoadOutput:

    with open(filename, 'r', encoding=encoding) as f:
        length = sum(1 for _ in f)

    with open(filename, 'r', encoding=encoding) as f:
        csv_reader = csv.DictReader(f)
        rows = tuple(
            (
                f"{row['bibkey']}",
                {remove_extra_whitespace(f"{bibkey}") for bibkey in row['direct_references'].split(",")},
            )
            for row in csv_reader
        )

    return rows, length


def load_bibentries_ods(filename: str) -> LoadOutput:
    df = pl.read_ods(filename, has_header=True, drop_empty_rows=True)

    length = df.shape[0]

    required_columns = ['bibkey', 'direct_references']
    if missing_columns := [col for col in required_columns if col not in df.columns]:
        raise ValueError(f"Fatal error! Missing the following columns in the ODS file: {missing_columns}")

    rows = tuple(
        (
            f"{bibkey}",
            {remove_extra_whitespace(f"{bibkey}") for bibkey in bibkeys_to_lookup.split(",")},
        )
        for bibkey, bibkeys_to_lookup in zip(
            df['bibkey'].to_list(),
            df['direct_references'].to_list(),
        )
    )

    return rows, length


@try_except_wrapper(lgr)
def load_list_of_bibentries_list(filename: str, encoding: str | None) -> LoadOutput:
    """
    Load a list of lists of bibentries from a file.
    """

    path = Path(filename)
    if not path.exists():
        raise FileNotFoundError(f"The file '{filename}' does not exist.")

    extension = path.suffix

    match (extension, encoding):
        case (".csv", encoding):
            if encoding is None:
                raise ValueError("Encoding must be provided for CSV files.")
            return load_bibentries_csv(filename, encoding)

        case (".ods", None):
            return load_bibentries_ods(filename)

        case _:
            raise ValueError(
                f"Format '{extension}' not supported. Only CSV and ODS files are supported. File passed was: '{filename}', extension found was '{extension}'."
            )


type LookupHashmap = Dict[
    # This comes from the bibliography
    str,  # bibkey
    Tuple[
        List[str],  # further_refs
        List[str],  # depends_on
    ],
]


@try_except_wrapper(lgr)
def load_lookup_hashmap(filename: str) -> LookupHashmap:
    """
    Load a lookup hashmap from the bibliography ODS file.
    """

    path = Path(filename)
    if not path.exists():
        raise FileNotFoundError(f"The file '{filename}' does not exist.")

    extension = path.suffix

    if extension != ".ods":
        raise ValueError(f"Format '{extension}' not supported. Only ODS files are supported.")

    df = pl.read_ods(filename, has_header=True, drop_empty_rows=True)
    required_columns = ['bibkey', '_further_refs', '_depends_on']

    if missing_columns := [col for col in required_columns if col not in df.columns]:
        raise ValueError(f"Fatal error! Missing the following columns in the ODS file: {missing_columns}")

    hashmap = {
        bibkey: (
            [remove_extra_whitespace(f"{bibkey}") for bibkey in further_refs.split(",") if further_refs],
            [remove_extra_whitespace(f"{bibkey}") for bibkey in depends_on.split(",") if depends_on],
        )
        for bibkey, further_refs, depends_on in zip(
            df['bibkey'].to_list(),
            df['_further_refs'].fill_null("").to_list(),
            df['_depends_on'].fill_null("").to_list(),
        )
    }

    return hashmap


type ReferencesDependencies = Tuple[
    # This goes to the pages spreadsheet in 'portal data'
    str,  # bibkey
    Set[str],  # direct_references
    Set[str],  # references further_references
    Set[str],  # references depends_on
]


def find_pages_references(
    bibentry_with_references: BibentryWithReferences,
    hashmap: LookupHashmap,
) -> ReferencesDependencies:
    """
    Find all further_references and depends_on for a list of references of a bibkey.
    """

    main_bibkey, references = bibentry_with_references

    if references == {""}:
        references = set()

    result_nested = [hashmap[reference] for reference in references]

    references_further_references_nested = (tup[0] for tup in result_nested)

    references_depends_on_nested = (tup[1] for tup in result_nested)

    references_further_references = {ref for refs in references_further_references_nested for ref in refs}

    references_depends_on = {ref for refs in references_depends_on_nested for ref in refs}

    return main_bibkey, references, references_further_references, references_depends_on


@try_except_wrapper(lgr)
def main(
    bibentries_filename: str,
    bibliography_filename: str,
    encoding: str | None,
    output_filename: str,
) -> None:
    """
    Main function to find all further_references and depends_on for a list of references of a bibkey.
    """

    lgr.info(f"Loading bibentries from '{bibentries_filename}'")
    bibentries, num_bibentries = runwrap(load_list_of_bibentries_list(bibentries_filename, encoding))
    lgr.info(f"Loaded {num_bibentries} bibentries")

    lgr.info(f"Loading lookup hashmap from '{bibliography_filename}'")
    hashmap = runwrap(load_lookup_hashmap(bibliography_filename))
    lgr.info(f"Loaded lookup hashmap")

    lgr.info(f"Finding references dependencies")
    references_dependencies = [find_pages_references(bibentry, hashmap) for bibentry in bibentries]
    lgr.info(f"Found references dependencies!")

    lgr.info(f"Writing to '{output_filename}'")
    with open(output_filename, 'w') as f:
        csv_writer = csv.writer(f)
        csv_writer.writerow(["bibkey", "direct_references", "references_further_references", "references_depends_on"])
        for bibkey, direct_references, references_further_references, references_depends_on in references_dependencies:
            csv_writer.writerow(
                [
                    bibkey,
                    ", ".join(sorted(direct_references)),
                    ", ".join(sorted(references_further_references)),
                    ", ".join(sorted(references_depends_on)),
                ]
            )

    lgr.info(f"Done! Output written to '{output_filename}'")
    return None


def cli() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description="Find all further_references and depends_on for a list of references of a bibkey."
    )

    parser.add_argument(
        "-i",
        "--input-filename",
        type=str,
        help="The filename of the list of references of a bibkey, in CSV or ODS format. Must contain the columns 'bibkey' and 'direct_references'.",
        required=True,
    )

    parser.add_argument(
        "-e",
        "--encoding",
        type=str,
        help="The encoding of the input file. Required for input CSV files.",
        default=None,
    )

    parser.add_argument(
        "-b",
        "--bibliography-filename",
        type=str,
        help="The filename of the bibliography ODS file. Must contain the columns 'bibkey', '_further_refs', and '_depends_on'.",
        required=True,
    )

    parser.add_argument(
        "-o",
        "--output-filename",
        type=str,
        help="The filename of the output CSV file. Will contain the columns 'bibkey', 'pages_further_references', and 'pages_depends_on'.",
        required=True,
    )

    args = parser.parse_args()

    main(
        bibentries_filename=args.input_filename,
        bibliography_filename=args.bibliography_filename,
        encoding=args.encoding,
        output_filename=args.output_filename,
    )

    return None


if __name__ == "__main__":
    cli()
