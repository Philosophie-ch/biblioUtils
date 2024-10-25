import csv
import os
from typing import Iterator, TypeAlias

from src.sdk.utils import handle_error, handle_unexpected_exception
from src.sdk.ResultMonad import Err, Ok, rbind, runwrap
from src.ref_pipe.models import File, Profile, Markdown, ProfileWithMD
from src.ref_pipe.utils import GMDLGR as lgr


def load_profiles_csv(input_file: str, encoding: str) -> Ok[list[Profile]] | Err:

    try:
        frame = f"load_profiles_csv"
        lgr.info(f"{frame}\n\tReading CSV file '{input_file}' with encoding '{encoding}'...")

        if not os.path.exists(input_file):
            return handle_error(frame, f"The input file '{input_file}' does not exist.", lgr, code=-2)

        with open(input_file, "r", encoding=encoding) as f:
            reader = csv.DictReader(f)

            required_columns = ["id", "lastname", "_biblio_name", "biblio_keys", "biblio_dependencies_keys"]

            if reader.fieldnames is None or not all(col in reader.fieldnames for col in required_columns):
                msg = f"The CSV file needs to have a header row with at least the following columns:\n\t{', '.join(required_columns)}."
                return handle_error(frame, msg, lgr, code=-3)

            rows = list(reader)  # Read all rows into memory

        output = [
            Profile(
                id=row["id"],
                lastname=row["lastname"],
                biblio_name=row["_biblio_name"],
                biblio_keys=row["biblio_keys"],
                biblio_dependencies_keys=row["biblio_dependencies_keys"],
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

MASTER_MD_TEMPLATE = """---
imports:
- ~%~%~%md_filename~%~%~%
volume: 99
issue: 9
date: October 2024
doi: 10.48106/dial.v77.i3.01
first-page: 1
---
"""


def prepare_md(profile: Profile, output_folder: str) -> Ok[ProfileWithMD] | Err:
    try:

        biblio_keys = profile.biblio_keys.split(",")

        biblio_keys_str = "\n\n".join([f"@{key}" for key in biblio_keys])

        main_content = MD_TEMPLATE.replace("~%~%~%PUT THE BIBKEYS HERE~%~%~%", biblio_keys_str)
        main_md = File(content=main_content, name=f"{profile.id}_{profile.lastname}.md")

        master_content = MASTER_MD_TEMPLATE.replace("~%~%~%md_filename~%~%~%", main_md.name)
        master_md = File(content=master_content, name=f"master.md")

        md = Markdown(
            base_dir=output_folder,
            main_file=main_md,
            master_file=master_md,
        )

        profile_with_md = ProfileWithMD(**profile.__dict__, markdown=md)

        return Ok(out=profile_with_md)

    except Exception as e:
        return handle_unexpected_exception(
            f"An error occurred while trying to prepare the markdown for profile [[ {profile.id} -- {profile.lastname} ]]:\n\t{e}",
            lgr,
        )


def write_md_file(profile: ProfileWithMD) -> Ok[ProfileWithMD] | Err:
    try:
        frame = f"write_md_file"
        md = profile.markdown

        lgr.debug(f"{frame}\n\tWriting markdown files for profile [[ {profile.id} -- {profile.lastname} ]]...")

        if not md:
            return handle_error(
                frame,
                f"The profile does not have the necessary markdown files.",
                lgr,
                code=-2,
            )

        os.makedirs(os.path.dirname(md.base_dir), exist_ok=True)

        lgr.debug(f"{frame}\n\tWriting markdown files for profile [[ {profile.id} -- {profile.lastname} ]]...")

        for file in [md.main_file, md.master_file]:
            if not file or not file.content or not file.name:
                return handle_error(
                    frame,
                    f"The markdown file '{file.name}' does not have content or a name.",
                    lgr,
                    code=-3,
                )


        main_file_path = md.main_file.file_path(md.base_dir)
        master_file_path = md.master_file.file_path(md.base_dir)

        # Create folders if they don't exist
        os.makedirs(os.path.dirname(main_file_path), exist_ok=True)
        os.makedirs(os.path.dirname(master_file_path), exist_ok=True)

        with open(main_file_path, "w") as f:
            f.write(md.main_file.content)

        with open(master_file_path, "w") as f:
            f.write(md.master_file.content)

        # consume the contents to save memory
        profile.markdown.main_file.content = ""
        profile.markdown.master_file.content = ""

        return Ok(out=profile)

    except Exception as e:
        return handle_unexpected_exception(f"An error occurred while trying to write the markdown file:\n\t{e}", lgr)


TMainReport: TypeAlias = Iterator[tuple[Profile, Ok[ProfileWithMD] | Err]]


def main(
    input_csv: str,
    encoding: str,
    output_folder: str,
) -> Ok[TMainReport] | Err:

    try:
        if (not input_csv) or (not output_folder) or (not encoding):
            return handle_error(
                frame="main",
                msg="Please provide the inputs that this function needs. Check its signature",
                logger=lgr,
                code=-2
            )

        # 1. Load profiles from CSV
        # unwrap fails if the result is an Err
        profiles = runwrap(load_profiles_csv(input_csv, encoding))

        # 2. Prepare markdown files
        profiles_with_mds = [prepare_md(profile, output_folder) for profile in profiles]

        zipped = zip(profiles, profiles_with_mds)

        return Ok(out=zipped)

    except Exception as e:
        return Err(message=f"An error occurred while trying to generate the markdown files:\n\t{e}", code=-1)


def generate_report(main_output: TMainReport, output_folder: str, encoding: str) -> Ok[None] | Err:
    try:
        frame = f"generate_report"
        lgr.info(f"{frame}\n\tGenerating report for the markdown file generation...")
        os.makedirs(output_folder, exist_ok=True)

        report_filename = f"{output_folder}/gen_md_report.csv"

        with open(report_filename, "w", encoding=encoding) as f:
            writer = csv.writer(f)
            writer.writerow(
                [
                    "id",
                    "lastname",
                    "biblio_keys",
                    "biblio_dependencies_keys",
                    "status",
                    "md_file",
                    "master_file",
                    "error_message",
                ]
            )

            for profile, write_result in main_output:
                match write_result:
                    case Ok():
                        status = "success"
                        err_msg = ""
                        md_file = write_result.out.markdown.main_file.name
                        master_file = write_result.out.markdown.master_file.name

                    case Err(message=message, code=code):
                        status = "error"
                        err_msg = message
                        md_file = ""
                        master_file = ""

                writer.writerow(
                    [
                        profile.id,
                        profile.lastname,
                        profile.biblio_keys,
                        profile.biblio_dependencies_keys,
                        status,
                        md_file,
                        master_file,
                        err_msg,
                    ]
                )

        lgr.info(f"Success! Report written to {report_filename}.")
        return Ok(out=None)

    except Exception as e:
        return Err(message=f"An error occurred while trying to generate the markdown files:\n{e}", code=-1)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate markdown files from a CSV file.")
    parser.add_argument("-i", "--input_csv", type=str, help="Path to the CSV file.", required=True)
    parser.add_argument(
        "-e", "--encoding", type=str, help="The encoding of the CSV file. 'utf-8' by default.", default="utf-8"
    )
    parser.add_argument("-o", "--output_folder", type=str, help="The folder where the markdown files will be saved.", required=True)

    args = parser.parse_args()

    res = main(args.input_csv, args.encoding, args.output_folder)

    match res:
        case Ok(out=out):
            # Unpack the zipped profiles and profiles_with_mds
            out_list = list(out)
            profiles = [tup[0] for tup in out_list]
            profiles_with_mds = [tup[1] for tup in out_list]

            # 1. Write markdown files to disk
            writes = [rbind(write_md_file, p) for p in profiles_with_mds]

            # 2. Produce report
            zipped = zip(profiles, writes)
            generate_report(zipped, args.output_folder, args.encoding)

        case Err(message=msg, code=code):
            pass
