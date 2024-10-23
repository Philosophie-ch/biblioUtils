import csv
from dataclasses import dataclass
import os
from typing import Generator, Iterator, TypeAlias

from src.sdk.utils import handle_error, handle_unexpected_exception
from src.sdk.types import Err, Ok, rbind, runwrap
from src.ref_pipe.utils import GMDLGR as lgr


@dataclass
class Profile:
    id: str
    lastname: str
    biblio_keys: str
    biblio_keys_dependencies: str | None


@dataclass
class MarkdownFile:
    content: str
    filename: str


def load_profiles_csv(input_file: str, encoding: str) -> Ok[list[Profile]] | Err:

    try:
        frame = f"load_profiles_csv"
        lgr.info(f"{frame}\n\tReading CSV file '{input_file}' with encoding '{encoding}'.")

        with open(input_file, "r", encoding=encoding) as f:
            reader = csv.DictReader(f)

            required_columns = ["id", "lastname", "_biblio_keys", "_biblio_keys_dependencies"]

            if reader.fieldnames is None or not all(col in reader.fieldnames for col in required_columns):
                msg = f"{frame}\n\tThe CSV file needs to have a header row with at least the following columns:\n\t{', '.join(required_columns)}."
                return handle_error(msg, lgr, code=-2)

            rows = list(reader)  # Read all rows into memory

        output = [
            Profile(
                id=row["id"],
                lastname=row["lastname"],
                biblio_keys=row["_biblio_keys"],
                biblio_keys_dependencies=row["_biblio_keys_dependencies"],
            )
            for row in rows
        ]

        return Ok(out=output)

    except Exception as e:
        return handle_unexpected_exception(f"An error occurred while trying to read the CSV file:\n\t{e}", lgr)


MD_TEMPLATE = """---
title: "HTML References Pipeline"
bibliography: ../../../dialectica.bib
---

~%~%~%PUT THE BIBKEYS HERE~%~%~%

# References
"""


def prepare_md(profile: Profile, output_folder: str) -> Ok[MarkdownFile] | Err:
    try:

        biblio_keys = profile.biblio_keys.split(",")

        biblio_keys_str = "\n\n".join([f"@{key}" for key in biblio_keys])

        content = MD_TEMPLATE.replace("~%~%~%PUT THE BIBKEYS HERE~%~%~%", biblio_keys_str)

        filename = os.path.join(output_folder, f"{profile.id}_{profile.lastname}.md")

        return Ok(out=MarkdownFile(content=content, filename=filename))

    except Exception as e:
        return handle_unexpected_exception(
            f"An error occurred while trying to prepare the markdown for profile [[ {profile.id} -- {profile.lastname} ]]:\n\t{e}",
            lgr,
        )


def write_md_file(md: MarkdownFile) -> Ok[None] | Err:
    try:
        frame = f"write_md_file"
        # Create folders if they don't exist
        os.makedirs(os.path.dirname(md.filename), exist_ok=True)

        with open(md.filename, "w") as f:
            f.write(md.content)

        return Ok(out=None)

    except Exception as e:
        return handle_unexpected_exception(f"An error occurred while trying to write the markdown file:\n\t{e}", lgr)


TMainReport: TypeAlias = Iterator[tuple[Profile, Ok[None] | Err]]


def generate_report(
    main_output: TMainReport, output_folder: str, encoding: str
) -> Ok[None] | Err:
    try:
        frame = f"generate_report"
        lgr.info(f"{frame}\n\tGenerating report for the markdown file generation...")
        os.makedirs(output_folder, exist_ok=True)

        report_filename = f"{output_folder}/gen_md_report.csv"

        with open(report_filename, "w", encoding=encoding) as f:
            writer = csv.writer(f)
            writer.writerow(["id", "lastname", "biblio_keys", "biblio_keys_dependencies", "status", "message"])

            for profile, write_result in main_output:
                status = "success" if isinstance(write_result, Ok) else "error"
                message = write_result.message if isinstance(write_result, Err) else ""

                writer.writerow(
                    [
                        profile.id,
                        profile.lastname,
                        profile.biblio_keys,
                        profile.biblio_keys_dependencies,
                        status,
                        message,
                    ]
                )

        lgr.info(f"Success! Report written to {report_filename}.")
        return Ok(out=None)

    except Exception as e:
        return handle_unexpected_exception(f"An error occurred while trying to generate the markdown files:\n{e}", lgr)


def main(
    input_csv: str,
    encoding: str,
    output_folder: str,
) -> Ok[TMainReport] | Err:

    try:
        # 1. Load profiles from CSV
        # unwrap fails if the result is an Err
        profiles = runwrap(load_profiles_csv(input_csv, encoding))

        # 2. Prepare markdown files
        mds = [prepare_md(profile, output_folder) for profile in profiles]

        # 3. Write markdown files to disk
        writes = [rbind(write_md_file, md) for md in mds]

        # 4. Produce report
        zipped = zip(profiles, writes)
        report_result = generate_report(zipped, output_folder, encoding)

        match report_result:
            case Ok():
                return Ok(out=zipped)
            case Err(message=message, code=code):
                lgr.error(f"An error occurred while trying to generate the report:\n\t{message}")
                lgr.info(
                    f"Regardless of the report error, the markdown files were successfully generated. Returning success without the report."
                )
                return Ok(out=zipped)

    except Exception as e:
        return handle_unexpected_exception(
            f"An error occurred while trying to generate the markdown files:\n\t{e}", lgr
        )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate markdown files from a CSV file.")
    parser.add_argument("-i", "--input_csv", type=str, help="Path to the CSV file.")
    parser.add_argument(
        "-e", "--encoding", type=str, help="The encoding of the CSV file. 'utf-8' by default.", default="utf-8"
    )
    parser.add_argument("-o", "--output_folder", type=str, help="The folder where the markdown files will be saved.")

    args = parser.parse_args()

    process_result = main(args.input_csv, args.encoding, args.output_folder)

    match process_result:
        case Ok():
            pass
        case Err(message=message, code=code):
            lgr.error(f"An error occurred:\n{message}")
