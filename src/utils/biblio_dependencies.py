from logging import Logger, log
from TexSoup import TexSoup
from TexSoup.data import TexNode, BraceGroup
import csv
import os
from typing import Literal, TypeAlias

from dataclasses import dataclass

from src.sdk.utils import get_logger

logger = get_logger("biblio_dependencies")

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


@dataclass
class ProcessedBibEntry(INBibEntry):
    further_references_good: str
    further_references_bad: str
    depends_on_good: str
    depends_on_bad: str


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


def get_citet_bibkeys(row: INBibEntry, citet_field: CitetField) -> list[str]:
    data = getattr(row, citet_field)
    try:
        citet_l = TexSoup(data).find_all('citet')
        citets_raw_nested = [citet.args for citet in citet_l if isinstance(citet, TexNode)]
        citets_raw_flat = [item for sublist in citets_raw_nested for item in sublist]
        citets_s = [citet.string.split(",") for citet in citets_raw_flat if isinstance(citet, BraceGroup)]
        citets_s_flat = [item.strip() for sublist in citets_s for item in sublist]

        return citets_s_flat
    except Exception as e:
        logger.error(f"Error parsing field '{citet_field}' in row '{row.id}'. Content of the field: {data}. Error:\n{e}")
        return []


def parse_bibentry(row: INBibEntry) -> ParsedBibEntry:
    notes_bibkeys = get_citet_bibkeys(row, "notes")
    title_bibkeys = get_citet_bibkeys(row, "title")

    further_references_raw = notes_bibkeys + title_bibkeys

    further_notes_bibkeys = get_citet_bibkeys(row, "further_note")
    crossref_bibkeys = get_citet_bibkeys(row, "crossref")

    depends_on_raw = further_references_raw + further_notes_bibkeys + crossref_bibkeys

    return ParsedBibEntry(
        id=row.id,
        bibkey=row.bibkey,
        title=row.title,
        notes=row.notes,
        crossref=row.crossref,
        further_note=row.further_note,
        further_references_raw=further_references_raw,
        depends_on_raw=depends_on_raw,
    )


def get_all_bibkeys(rows: list[INBibEntry]) -> list[str]:

    all_bibkeys = [row.bibkey for row in rows]

    return all_bibkeys


def process_bibentry(parsed_bibentry: ParsedBibEntry, all_bibkeys_list: list[str]) -> ProcessedBibEntry:
    further_references_good = []
    further_references_bad = []
    depends_on_good = []
    depends_on_bad = []

    for bibkey in parsed_bibentry.further_references_raw:
        if bibkey in all_bibkeys_list:
            further_references_good.append(bibkey)
        else:
            further_references_bad.append(bibkey)

    for bibkey in parsed_bibentry.depends_on_raw:
        if bibkey in all_bibkeys_list:
            depends_on_good.append(bibkey)
        else:
            depends_on_bad.append(bibkey)

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
    )


def main(filename: str, encoding: str, output_filename: str) -> None:
    rows = load_bibentries_csv(filename, encoding)
    parsed_rows = (parse_bibentry(row) for row in rows)
    all_bibkeys = get_all_bibkeys(rows)
    processed_rows = (process_bibentry(parsed_row, all_bibkeys) for parsed_row in parsed_rows)

    fieldnames = list(INBibEntry.__annotations__.keys()) + list(ProcessedBibEntry.__annotations__.keys())

    with open(output_filename, 'w', encoding=encoding) as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows([row.__dict__ for row in processed_rows])

    print(f"Processed {len(rows)} entries")

    return None


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Process a CSV file with BibTeX entries")

    parser.add_argument(
        "-f",
        "--filename",
        type=str,
        help="The CSV file to process. Needs to have the following columns: 'id', 'bibkey', 'title', 'notes', 'crossref', 'further_note'.",
        required=True,
    )

    parser.add_argument("-e", "--encoding", type=str, help="The encoding of the CSV file.", required=True)

    parser.add_argument("-o", "--output_filename", type=str, help="The output CSV file.", required=True)

    args = parser.parse_args()

    main(args.filename, args.encoding, args.output_filename)
