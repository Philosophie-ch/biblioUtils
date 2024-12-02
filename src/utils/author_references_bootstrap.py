"""
Bootstrap the references per author, by looking into the bibliography and matching the author IDs to the author IDs per bibliographic entry.
"""

import csv
import polars as pl

from pathlib import Path
from typing import Dict, FrozenSet, Generator, NamedTuple, Tuple
from types import MappingProxyType
from src.sdk.ResultMonad import light_error_handler, main_try_except_wrapper
from src.sdk.utils import get_logger, lginf, remove_extra_whitespace
from src.utils.bibkey_utils import validate_bibkeys


lgr = get_logger("Author References Finder")

DEBUG = True


type TBibkey = str
type TAuthorID = int

type TBibliographyMap = Dict[
    TBibkey,  # unique identifier of the bibliographic entry
    FrozenSet[TAuthorID],  # authors of the bibliographic entry
]

type TID = int
type TBiblioName = str

type TRawAuthor = Tuple[
    TID,  # unique identifier of the author
    TBiblioName,  # name of the author as it appears in the bibliography
]


class Author(NamedTuple):
    id: TID
    biblio_name: TBiblioName
    references: FrozenSet[TBibkey]


type TResult = Generator[Author, None, None]


@light_error_handler(DEBUG)
def _parse_biblio_authors(author_ids_s: str) -> FrozenSet[TAuthorID]:
    return frozenset(int(remove_extra_whitespace(author_id)) for author_id in author_ids_s.split(","))


@light_error_handler(DEBUG)
def _load_bibliography_ods(bibliography_file_ods: str) -> TBibliographyMap:
    df = pl.read_ods(bibliography_file_ods, has_header=True, drop_empty_rows=True)

    required_columns = ["bibkey", "author_ids"]

    if missing_columns := [col for col in required_columns if col not in df.columns]:
        raise ValueError(f"Fatal error! Missing the following columns in the ODS file: {missing_columns}")

    dict = {
        f"{bibkey}": _parse_biblio_authors(f"{author_ids}")
        for bibkey, author_ids in zip(df["bibkey"].to_list(), df["author_ids"].to_list())
    }

    return dict


def load_bibliography(bibliography_file: str) -> TBibliographyMap:

    frame = f"load_bibliography"

    lginf(frame, f"Reading bibliography file '{bibliography_file}'...", lgr)

    path = Path(bibliography_file)
    if not path.exists():
        raise FileNotFoundError(f"File '{bibliography_file}' not found.")

    extension = path.suffix

    match (extension):

        case ".ods":
            biblio_map = _load_bibliography_ods(bibliography_file)

        case _:
            raise ValueError(f"The input file must be an ODS file. '{extension}' is not supported.")

    validate_bibkeys(biblio_map.keys())

    lginf(frame, f"Loaded and validated {len(biblio_map)} bibliographic entries.", lgr)

    return biblio_map


@light_error_handler(DEBUG)
def _parse_raw_author(id_s: str, biblio_name_s: str) -> TRawAuthor:
    id_stripped = remove_extra_whitespace(id_s)
    try:
        id_clean = int(id_stripped)
    except ValueError:
        raise ValueError(f"Could not parse the author ID '{id_stripped}' as an integer for '{biblio_name_s}'.")

    return (id_clean, remove_extra_whitespace(biblio_name_s))


@light_error_handler(DEBUG)
def _load_authors_csv(authors_file_csv: str, encoding: str) -> Generator[TRawAuthor, None, None]:

    with open(authors_file_csv, "r", encoding=encoding) as f:
        csv_reader = csv.DictReader(f)

        required_columns = ["id", "_biblio_name"]

        if csv_reader.fieldnames is None or not all(col in csv_reader.fieldnames for col in required_columns):
            msg = f"The CSV file needs to have a header row with at least the following columns: {', '.join(required_columns)}."
            raise ValueError(msg)

        for row in csv_reader:
            yield _parse_raw_author(row["id"], row["_biblio_name"])


def _count_authors_csv(authors_file_csv: str, encoding: str) -> int:

    with open(authors_file_csv, "r", encoding=encoding) as f:
        csv_reader = csv.DictReader(f)

        return sum(1 for _ in csv_reader)


@light_error_handler(DEBUG)
def _load_authors_ods(authors_file_ods: str) -> Tuple[Generator[TRawAuthor, None, None], int]:

    df = pl.read_ods(authors_file_ods, has_header=True, drop_empty_rows=True)

    required_columns = ["id", "_biblio_name"]

    if missing_columns := [col for col in required_columns if col not in df.columns]:
        raise ValueError(f"Fatal error! Missing the following columns in the ODS file: {missing_columns}")

    authors = (
        _parse_raw_author(f"{id_raw}", f"{biblio_name}")
        for id_raw, biblio_name in zip(df["id"].to_list(), df["_biblio_name"].to_list())
    )

    return authors, len(df)


def load_authors(authors_file: str, encoding: str | None = None) -> Generator[TRawAuthor, None, None]:

    frame = f"load_authors"
    lginf(frame, f"Reading authors file '{authors_file}'...", lgr)

    path = Path(authors_file)
    if not path.exists():
        raise FileNotFoundError(f"File '{authors_file}' not found.")

    extension = path.suffix

    match (extension, encoding):

        case (".csv", encoding):
            if encoding is None:
                raise ValueError("The encoding for the authors file must be specified for CSV files.")
            authors = _load_authors_csv(authors_file, encoding)
            authors_n = _count_authors_csv(authors_file, encoding)

        case (".ods", _):
            authors, authors_n = _load_authors_ods(authors_file)

        case _:
            raise ValueError(f"The input file must be an ODS file. '{extension}' is not supported.")

    lginf(frame, f"Loaded {authors_n} authors.", lgr)

    return authors


def process_author(raw_author: TRawAuthor, bibliography_map: TBibliographyMap) -> Author:

    id, biblio_name = raw_author

    references = frozenset(bibkey for bibkey, author_ids in bibliography_map.items() if id in author_ids)

    author = Author(id=id, biblio_name=biblio_name, references=references)

    return author


@light_error_handler(DEBUG)
def _write_output_csv(result: TResult, output_file_csv: str, encoding: str) -> None:

    result_evaluted = tuple(
        {
            "id": author.id,
            "biblio_name": author.biblio_name,
            "biblio_keys": ", ".join(author.references),
        }
        for author in result
    )

    with open(output_file_csv, "w", newline="", encoding=encoding) as f:
        writer = csv.DictWriter(f, fieldnames=["id", "biblio_name", "biblio_keys"])
        writer.writeheader()
        writer.writerows(result_evaluted)

    return None


def write_output(result: TResult, output_file: str, encoding: str | None = None) -> None:

    path = Path(output_file)
    if path.exists():
        lgr.warning(f"Output file '{output_file}' already exists. Overwriting...")
    extension = path.suffix

    match (extension, encoding):

        case (".csv", encoding):
            if encoding is None:
                raise ValueError("The encoding must be specified for CSV files.")
            _write_output_csv(result, output_file, encoding)

        case _:
            raise ValueError(f"Format '{extension}' not supported. Only CSV files are supported.")

    return None


@main_try_except_wrapper(lgr)
def main(
    bibliography_file: str,
    authors_file: str,
    output_file: str,
    encoding: str | None = None,
) -> None:

    frame = "main_process"

    lginf(frame, f"Loading bibliography from '{bibliography_file}'...", lgr)
    bibliography_map = load_bibliography(bibliography_file)

    lginf(frame, f"Loading authors from '{authors_file}'...", lgr)
    raw_authors = load_authors(authors_file, encoding)

    lginf(frame, "Bootstrapping author references...", lgr)
    result = (process_author(raw_author, bibliography_map) for raw_author in raw_authors)

    lginf(frame, f"Writing output to '{output_file}'...", lgr)
    write_output(result, output_file, encoding)

    lginf(frame, "Done!", lgr)
    return None


def cli() -> None:

    import argparse

    parser = argparse.ArgumentParser(description="Bootstrap the references per author.")
    parser.add_argument("-b", "--bibliography-file", type=str, help="The bibliography file.", required=True)
    parser.add_argument("-a", "--authors-file", type=str, help="The authors file.", required=True)
    parser.add_argument("-o", "--output-file", type=str, help="The output file.", required=True)
    parser.add_argument(
        "-e", "--authors-file-encoding", type=str, default=None, help="The encoding of the authors CSV file."
    )

    args = parser.parse_args()

    main(
        bibliography_file=args.bibliography_file,
        authors_file=args.authors_file,
        output_file=args.output_file,
        encoding=args.authors_file_encoding,
    )


if __name__ == "__main__":
    cli()
