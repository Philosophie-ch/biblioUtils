import csv
from dataclasses import dataclass
from typing import Generator

from src.sdk.return_types import Err, Ok


@dataclass
class Profile:
    id: str
    lastname: str
    biblio_keys: str
    biblio_keys_dependencies: str | None


def load_profiles_csv(input_file: str, encoding: str) -> Ok[Generator[Profile, None, None]] | Err:

    try:
        with open(input_file, "r", encoding=encoding) as f:
            reader = csv.DictReader(f)

            required_columns = ["id", "lastname", "_biblio_keys", "_biblio_keys_dependencies"]

            if reader.fieldnames is None or not all(col in reader.fieldnames for col in required_columns):
                return Err(
                    message="The CSV file needs to have a header row with at least 'id', 'lastname', '_biblio_keys', '_biblio_keys_dependencies'.",
                    code=-2,
                )

            rows = list(reader)  # Read all rows into memory

        output = (
            Profile(
                id=row["id"],
                lastname=row["lastname"],
                biblio_keys=row["_biblio_keys"],
                biblio_keys_dependencies=row["_biblio_keys_dependencies"],
            )
            for row in rows
        )

        return Ok(out=output)

    except Exception as e:
        return Err(message=f"An error occurred while trying to read the CSV file:\n\t{e}", code=-1)


MD_TEMPLATE = """---
title: "HTML References Pipeline"
bibliography: ../../../dialectica.bib
---

~%~%~%PUT THE BIBKEYS HERE~%~%~%

# References
"""


def prepare_md(profile: Profile) -> Ok[str] | Err:
    try:

        biblio_keys = profile.biblio_keys.split(",")

        biblio_keys_str = "\n\n".join([f"@{key}" for key in biblio_keys])

        md = MD_TEMPLATE.replace("~%~%~%PUT THE BIBKEYS HERE~%~%~%", biblio_keys_str)

        return Ok(out=md)

    except Exception as e:
        return Err(
            message=f"An error occurred while trying to prepare the markdown for profile [[ {profile.id} -- {profile.lastname} ]]:\n\t{e}",
            code=-1,
        )
