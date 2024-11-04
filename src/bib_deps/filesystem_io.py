import csv
import os
from src.bib_deps.models import INBibEntry
from src.sdk.ResultMonad import try_except_wrapper
from src.sdk.utils import get_logger


lgr = get_logger("Filesystem I/O")


@try_except_wrapper(lgr)
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
