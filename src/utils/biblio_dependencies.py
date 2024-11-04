from TexSoup import TexSoup
from TexSoup.data import TexNode, BraceGroup
import csv
import os
from typing import Literal, TypeAlias

from dataclasses import asdict, dataclass

from src.sdk.ResultMonad import Err, Ok, try_except_wrapper
from src.sdk.utils import get_logger, remove_extra_whitespace


lgr = get_logger("Biblio Dependencies")


@dataclass
class INBibEntry:
    id: str
    bibkey: str
    title: str
    notes: str
    crossref: str
    further_note: str


@dataclass
class ParsedBibEntry(INBibEntry):
    further_references_raw: list[str]
    depends_on_raw: list[str]
    status: Literal["success", "error"]
    error_message: str = ""


@dataclass
class ProcessedBibEntry(INBibEntry):
    further_references_good: str
    further_references_bad: str
    depends_on_good: str
    depends_on_bad: str
    status: Literal["success", "error"]
    error_message: str = ""

    def dict_dump(self) -> dict[str, str]:
        return asdict(self)


CitetField: TypeAlias = Literal[
    # For further_references
    "title",
    "notes",
    # for depends_on
    "crossref",
    "further_note",
]


def load_bibentries_csv(filename: str, encoding: str) -> list[INBibEntry]:

    if not os.path.exists(filename):
        raise FileNotFoundError(f"File '{filename}' not found")

    with open(filename, 'r', encoding=encoding) as f:
        csv_reader = csv.DictReader(f)
        rows = [
            INBibEntry(
                id=row['id'],
                bibkey=row['bibkey'],
                title=row['title'],
                notes=row['notes'],
                crossref=row['crossref'],
                further_note=row['further_note'],
            )
            for row in csv_reader
        ]

    return rows


@try_except_wrapper(lgr)
def get_citet_bibkeys(row: INBibEntry, citet_field: CitetField) -> list[str]:

    data = getattr(row, citet_field)

    try:
        # Isolate chaos
        citet_l = TexSoup(data).find_all('citet')
    except Exception as e:
        raise ValueError(f"External dependency error! TexSoup failed for '{citet_field}'.\n{e}")

    citets_raw_nested = [citet.args for citet in citet_l if isinstance(citet, TexNode)]
    citets_raw_flat = [item for sublist in citets_raw_nested for item in sublist]
    citets_s = [citet.string.split(",") for citet in citets_raw_flat if isinstance(citet, BraceGroup)]
    citets_s_flat = [item.strip() for sublist in citets_s for item in sublist]

    return citets_s_flat


@dataclass
class CitetResults:
    notes: Ok[list[str]] | Err
    title: Ok[list[str]] | Err
    further_note: Ok[list[str]] | Err


def parse_bibentry(row: INBibEntry) -> ParsedBibEntry:
    error_messages = []

    further_references_raw: list[str] = []

    citet_results = CitetResults(
        notes=get_citet_bibkeys(row, "notes"),
        title=get_citet_bibkeys(row, "title"),
        further_note=get_citet_bibkeys(row, "further_note"),
    )

    for field in ["notes", "title"]:
        if isinstance(getattr(citet_results, field), Err):
            error_messages.append(f"Error parsing '{field}' field: {getattr(citet_results, field).message}")
        else:
            further_references_raw += getattr(citet_results, field).out

    depends_on_raw = list(further_references_raw)

    for field in ["further_note"]:
        if isinstance(getattr(citet_results, field), Err):
            error_messages.append(f"Error parsing '{field}' field: {getattr(citet_results, field).message}")
        else:
            depends_on_raw += getattr(citet_results, field).out

    crossrefs_parsed = [remove_extra_whitespace(cr) for cr in row.crossref.split(",")] if row.crossref else []

    depends_on_raw += crossrefs_parsed

    if error_messages != []:
        return ParsedBibEntry(
            id=row.id,
            bibkey=row.bibkey,
            title=row.title,
            notes=row.notes,
            crossref=row.crossref,
            further_note=row.further_note,
            further_references_raw=[],
            depends_on_raw=[],
            status="error",
            error_message="\n\n".join(error_messages),
        )

    return ParsedBibEntry(
        id=row.id,
        bibkey=row.bibkey,
        title=row.title,
        notes=row.notes,
        crossref=row.crossref,
        further_note=row.further_note,
        further_references_raw=further_references_raw,
        depends_on_raw=depends_on_raw,
        status="success",
    )


def get_all_bibkeys(rows: list[INBibEntry]) -> list[str]:

    all_bibkeys = [row.bibkey for row in rows]

    return all_bibkeys


def process_bibentry(parsed_bibentry: ParsedBibEntry, all_bibkeys_list: list[str]) -> ProcessedBibEntry:
    further_refs = (
        (bibkey, 0) if bibkey in all_bibkeys_list else (bibkey, 1) for bibkey in parsed_bibentry.further_references_raw
    )
    depends_on = (
        (bibkey, 0) if bibkey in all_bibkeys_list else (bibkey, 1) for bibkey in parsed_bibentry.depends_on_raw
    )

    further_references_good = [bibkey for bibkey, status in further_refs if status == 0]
    further_references_bad = [bibkey for bibkey, status in further_refs if status == 1]
    depends_on_good = [bibkey for bibkey, status in depends_on if status == 0]
    depends_on_bad = [bibkey for bibkey, status in depends_on if status == 1]

    return ProcessedBibEntry(
        id=parsed_bibentry.id,
        bibkey=parsed_bibentry.bibkey,
        title=parsed_bibentry.title,
        notes=parsed_bibentry.notes,
        crossref=parsed_bibentry.crossref,
        further_note=parsed_bibentry.further_note,
        further_references_good=",".join(further_references_good),
        further_references_bad=",".join(further_references_bad),
        depends_on_good=",".join(depends_on_good),
        depends_on_bad=",".join(depends_on_bad),
        status=parsed_bibentry.status,
        error_message=parsed_bibentry.error_message,
    )


def main(filename: str, encoding: str, output_filename: str) -> None:

    lgr.info(f"Loading bibentries from '{filename}' [1/5]")
    rows = load_bibentries_csv(filename, encoding)

    lgr.info(f"Parsing {len(rows)} entries [2/5]")
    parsed_rows = (parse_bibentry(row) for row in rows)

    lgr.info("Getting all bibkeys in the file [3/5]")
    all_bibkeys = get_all_bibkeys(rows)

    lgr.info("Processing the entries [4/5]")
    processed_rows = (process_bibentry(parsed_row, all_bibkeys) for parsed_row in parsed_rows)

    lgr.info(f"Writing the output to '{output_filename}' [5/5]")
    fieldnames = list(INBibEntry.__annotations__.keys()) + list(ProcessedBibEntry.__annotations__.keys())

    with open(output_filename, 'w', encoding=encoding) as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows((row.dict_dump() for row in processed_rows))

    lgr.info(f"Success! Processed {len(rows)} entries. Report written to the file below ↴\n\t{output_filename}")

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

    main(args.input_csv, args.encoding, args.output_filename)


if __name__ == "__main__":
    cli_main()
