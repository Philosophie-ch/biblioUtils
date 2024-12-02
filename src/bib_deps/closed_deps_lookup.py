"""
Assuming we already computed the dependencies of the bib files, and populated the columns `_further_refs` and `_depends_on` in the bibliography already transitively closed, per bibentity. This script simply takes a list of lists of bibentities, and returns a list of lists of (1) _further_refs all appended, and (2) _depends_on all appended.
"""

import csv
import polars as pl
from pathlib import Path

from typing import Dict, FrozenSet, Generator, Tuple
from src.sdk.ResultMonad import light_error_handler, main_try_except_wrapper
from src.sdk.utils import get_logger, lginf, remove_extra_whitespace


lgr = get_logger("Closed Dependencies Lookup")
DEBUG = True

type TIdentifier = str  # a unique identifier for a bibentity, can be a bibkey, an ID, an author biblio name, etc.
type TNumberOfBibentities = int
type TDirectReferences = str
type TFurtherReferences = str  # further_references
type TDependsOn = str  # depends_on


type TBibentityWithReferences = Tuple[
    # This comes from either (a) the markdown parser to get direct references; or (b) the author bootstrap script to get direct references
    TIdentifier,
    FrozenSet[TDirectReferences],
]

type TLookupHashmap = Dict[
    # This comes from the bibliography
    TIdentifier,
    Tuple[
        FrozenSet[TFurtherReferences],
        FrozenSet[TDependsOn],
    ],
]

type TReferencesDependencies = Tuple[
    # This goes to the pages spreadsheet in 'portal data'
    TIdentifier,
    FrozenSet[TDirectReferences],
    FrozenSet[TFurtherReferences],
    FrozenSet[TDependsOn],
]


@light_error_handler(DEBUG)
def _load_bibentities_csv(filename: str, encoding: str) -> Generator[TBibentityWithReferences, None, None]:

    required_columns = ['identifier', 'direct_references']

    with open(filename, 'r', encoding=encoding) as f:
        csv_reader = csv.DictReader(f)

        if csv_reader.fieldnames is None or (
            missing_columns := [col for col in required_columns if col not in csv_reader.fieldnames]
        ):
            raise ValueError(f"Fatal error! Missing the following columns in the CSV file: {missing_columns}")

        for row in csv_reader:
            yield (
                f"{row['identifier']}",
                frozenset(remove_extra_whitespace(f"{bibkey}") for bibkey in row['direct_references'].split(",")),
            )


def _count_bibentities_csv(filename: str, encoding: str) -> TNumberOfBibentities:
    with open(filename, 'r', encoding=encoding) as f:
        return sum(1 for _ in f)


def load_bibentities_ods(filename: str) -> Tuple[Generator[TBibentityWithReferences, None, None], TNumberOfBibentities]:
    df = pl.read_ods(filename, has_header=True, drop_empty_rows=True)

    length = df.shape[0]

    required_columns = ['identifier', 'direct_references']
    if missing_columns := [col for col in required_columns if col not in df.columns]:
        raise ValueError(f"Fatal error! Missing the following columns in the ODS file: {missing_columns}")

    rows = (
        (
            f"{identifier}",
            frozenset(remove_extra_whitespace(f"{bibkey}") for bibkey in bibkeys_to_lookup.split(",")),
        )
        for identifier, bibkeys_to_lookup in zip(
            df['identifier'].to_list(),
            df['direct_references'].to_list(),
        )
    )

    return rows, length


def load_bibentities(filename: str, encoding: str | None) -> Generator[TBibentityWithReferences, None, None]:
    """
    Load a list of lists of bibentries from a file.
    """

    frame = f"load_bibentities"

    path = Path(filename)
    if not path.exists():
        raise FileNotFoundError(f"The file '{filename}' does not exist.")

    extension = path.suffix

    match (extension, encoding):
        case (".csv", encoding):
            if encoding is None:
                raise ValueError("Encoding must be provided for CSV files.")
            bibentities = _load_bibentities_csv(filename, encoding)
            num_bibentities = _count_bibentities_csv(filename, encoding)

        case (".ods", None):
            bibentities, num_bibentities = load_bibentities_ods(filename)

        case _:
            raise ValueError(
                f"Format '{extension}' not supported. Only CSV and ODS files are supported. File passed was: '{filename}', extension found was '{extension}'."
            )

    lginf(frame, f"Loaded {num_bibentities} bibentities from '{filename}'", lgr)

    return bibentities


@light_error_handler(DEBUG)
def load_lookup_hashmap(bibliography_filename: str) -> TLookupHashmap:
    """
    Load a lookup hashmap from the bibliography ODS file.
    """

    path = Path(bibliography_filename)
    if not path.exists():
        raise FileNotFoundError(f"The file '{bibliography_filename}' does not exist.")

    extension = path.suffix

    if extension != ".ods":
        raise ValueError(f"Format '{extension}' not supported. Only ODS files are supported.")

    df = pl.read_ods(bibliography_filename, has_header=True, drop_empty_rows=True)
    required_columns = ['bibkey', '_further_refs', '_depends_on']

    if missing_columns := [col for col in required_columns if col not in df.columns]:
        raise ValueError(f"Fatal error! Missing the following columns in the ODS file: {missing_columns}")

    hashmap = {
        bibkey: (
            frozenset(remove_extra_whitespace(f"{bibkey}") for bibkey in further_refs.split(",") if further_refs),
            frozenset(remove_extra_whitespace(f"{bibkey}") for bibkey in depends_on.split(",") if depends_on),
        )
        for bibkey, further_refs, depends_on in zip(
            df['bibkey'].to_list(),
            df['_further_refs'].fill_null("").to_list(),
            df['_depends_on'].fill_null("").to_list(),
        )
    }

    return hashmap


def process_bibentity(
    bibentity_with_references: TBibentityWithReferences,
    hashmap: TLookupHashmap,
) -> TReferencesDependencies:
    """
    Find all further_references and depends_on for a list of references of a bibkey.
    """

    identifier, direct_references = bibentity_with_references

    if direct_references == {""}:
        direct_references = frozenset()

    result_nested = [hashmap[reference] for reference in direct_references]

    references_further_references_nested = (tup[0] for tup in result_nested)

    references_depends_on_nested = (tup[1] for tup in result_nested)

    references_further_references = frozenset({ref for refs in references_further_references_nested for ref in refs})

    references_depends_on = frozenset({ref for refs in references_depends_on_nested for ref in refs})

    return identifier, direct_references, references_further_references, references_depends_on


@light_error_handler(DEBUG)
def _write_output_csv(
    result: Generator[TReferencesDependencies, None, None],
    output_filename: str,
    encoding: str,
) -> None:
    result_evaluated = tuple(
        {
            "identifier": identifier,
            "direct_references": ", ".join(sorted(direct_references)),
            "further_references": ", ".join(sorted(further_references)),
            "depends_on": ", ".join(sorted(depends_on)),
        }
        for identifier, direct_references, further_references, depends_on in result
    )

    with open(output_filename, 'w', encoding=encoding) as f:
        csv_writer = csv.DictWriter(
            f, fieldnames=["identifier", "direct_references", "further_references", "depends_on"]
        )
        csv_writer.writeheader()
        csv_writer.writerows(result_evaluated)


def write_output(
    result: Generator[TReferencesDependencies, None, None], output_filename: str, encoding: str | None = None
) -> None:

    path = Path(output_filename)
    if path.exists():
        lgr.warning(f"Output file '{output_filename}' already exists. Overwriting...")
    extension = path.suffix

    match (extension, encoding):

        case (".csv", encoding):
            if encoding is None:
                raise ValueError("The encoding must be specified for CSV files.")
            _write_output_csv(result, output_filename, encoding)

        case _:
            raise ValueError(f"Format '{extension}' not supported. Only CSV files are supported.")

    return None


@main_try_except_wrapper(lgr)
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
    bibentries = load_bibentities(bibentries_filename, encoding)

    lgr.info(f"Loading lookup hashmap from '{bibliography_filename}'")
    hashmap = load_lookup_hashmap(bibliography_filename)
    lgr.info(f"Loaded {len(hashmap)} entries on the lookup hashmap.")

    lgr.info(f"Finding references dependencies")
    result = (process_bibentity(bibentity, hashmap) for bibentity in bibentries)
    lgr.info(f"Found references dependencies!")

    lgr.info(f"Writing to '{output_filename}'")
    write_output(result, output_filename, encoding)

    lgr.info(f"Done!")
    return None


def cli() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description="Find all further_references and depends_on for a list of references of a bibentity."
    )

    parser.add_argument(
        "-i",
        "--input-filename",
        type=str,
        help="The filename of the list of references of a bibentity, in CSV or ODS format. Must contain the columns 'identifier' and 'direct_references'.",
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
        help="The filename of the output CSV file. Will contain the columns 'identifier', 'direct_references', 'further_references', and 'depends_on'.",
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
