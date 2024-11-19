import csv
from pathlib import Path
import polars as pl
from src.bib_deps.models import BaseBibEntry
from src.sdk.ResultMonad import try_except_wrapper
from src.sdk.utils import get_logger


lgr = get_logger("Data Repository")


def load_bibentries_csv(filename: str, encoding: str) -> list[BaseBibEntry]:

    with open(filename, 'r', encoding=encoding) as f:
        csv_reader = csv.DictReader(f)
        rows = [
            BaseBibEntry(
                bibkey=row['bibkey'],
                title=row['title'],
                notes=row['note'],
                crossref=row['crossref'],
                further_note=row['further_note'],
            )
            for row in csv_reader
        ]

    return rows


def load_bibentries_ods(filename: str) -> list[BaseBibEntry]:

    df = pl.read_ods(filename, has_header=True, drop_empty_rows=True)

    required_columns = ['bibkey', 'title', 'note', 'crossref', 'further_note']
    if missing_columns := [col for col in required_columns if col not in df.columns]:
        raise ValueError(f"Fatal error! Missing the following columns in the ODS file: {missing_columns}")

    rows = [
        BaseBibEntry(
            bibkey=f"{bibkey}",
            title=f"{title}",
            notes=f"{note}",
            crossref=f"{crossref}",
            further_note=f"{further_note}",
        )
        for bibkey, title, note, crossref, further_note in zip(
            df['bibkey'].to_list(),
            df['title'].to_list(),
            df['note'].to_list(),
            df['crossref'].to_list(),
            df['further_note'].to_list(),
        )
    ]

    return rows


@try_except_wrapper(lgr)
def load_bibentries(filename: str, encoding: str | None) -> list[BaseBibEntry]:

    path = Path(filename)

    if not path.exists():
        raise FileNotFoundError(f"File '{filename}' not found")

    extension = path.suffix

    match (extension, encoding):
        case (".csv", encoding) if encoding is not None:
            return load_bibentries_csv(filename, encoding)

        case (".ods", _):
            return load_bibentries_ods(filename)

        case _:
            raise ValueError(
                "The input file must be a CSV or ODS file. If it is a CSV file, an encoding must be provided."
            )
