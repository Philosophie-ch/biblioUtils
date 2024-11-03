import os

from src.sdk.utils import get_logger
from src.sdk.ResultMonad import try_except_wrapper
from src.ref_pipe.models import File, Profile, Markdown, ProfileWithMD


lgr = get_logger("Generate Markdown")


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


@try_except_wrapper(lgr)
def prepare_md(
    profile: Profile, local_base_dir: str, container_base_dir: str, relative_output_dir: str
) -> ProfileWithMD:

    biblio_keys = profile.biblio_keys

    biblio_keys_str = "\n\n".join([f"@{key}" for key in biblio_keys])

    main_content = MD_TEMPLATE.replace("~%~%~%PUT THE BIBKEYS HERE~%~%~%", biblio_keys_str)
    main_md = File(content=main_content, basename=f"{profile.id}_{profile.lastname}.md")

    master_content = MASTER_MD_TEMPLATE.replace("~%~%~%md_filename~%~%~%", main_md.basename)
    master_md = File(content=master_content, basename=f"master.md")

    md = Markdown(
        local_base_dir=local_base_dir,
        container_base_dir=container_base_dir,
        relative_output_dir=relative_output_dir,
        main_file=main_md,
        master_file=master_md,
    )

    profile_with_md = ProfileWithMD(**profile.__dict__, markdown=md)

    return profile_with_md


@try_except_wrapper(lgr)
def write_md_files(profile: ProfileWithMD) -> ProfileWithMD:
    md = profile.markdown

    if not md:
        raise ValueError(f"The markdown object for profile [[ {profile.id} -- {profile.lastname} ]] is missing.")

    output_local_dir = f"{md.local_base_dir}/{md.relative_output_dir}"
    if not os.path.exists(output_local_dir):
        raise FileNotFoundError(f"The output directory '{output_local_dir}' does not exist.")

    for file in [md.main_file, md.master_file]:
        if not file or not file.content or not file.basename:
            raise ValueError(f"The markdown file '{file.basename}' does not have content or a name.")

    main_file_path = md.main_file.full_file_path(output_local_dir)
    master_file_path = md.master_file.full_file_path(output_local_dir)

    with open(main_file_path, "w") as f:
        f.write(md.main_file.content)

    if not os.path.exists(main_file_path):
        raise FileNotFoundError(f"The markdown file '{main_file_path}' was not written successfully.")

    with open(master_file_path, "w") as f:
        f.write(md.master_file.content)

    if not os.path.exists(master_file_path):
        raise FileNotFoundError(f"The markdown file '{master_file_path}' was not written successfully.")

    # consume the contents to save memory
    profile.markdown.main_file.content = ""
    profile.markdown.master_file.content = ""

    return profile


# def main(
# input_csv: str,
# encoding: str,
# output_folder: str,
# ) -> Ok[TMDReport] | Err:

# try:
# if (not input_csv) or (not output_folder) or (not encoding):
# return handle_error(
# frame="main",
# msg="Please provide the inputs that this function needs. Check its signature",
# logger=lgr,
# code=-2,
# )

## 1. Load profiles from CSV
## unwrap fails if the result is an Err
# profiles = runwrap(load_profiles_csv(input_csv, encoding))

## 2. Prepare markdown files
# profiles_with_mds = [prepare_md(profile, output_folder) for profile in profiles]

# zipped = zip(profiles, profiles_with_mds)

# return Ok(out=zipped)

# except Exception as e:
# return Err(message=f"An error occurred while trying to generate the markdown files:\n\t{e}", code=-1)


# if __name__ == "__main__":
# import argparse

# parser = argparse.ArgumentParser(description="Generate markdown files from a CSV file.")
# parser.add_argument("-i", "--input_csv", type=str, help="Path to the CSV file.", required=True)
# parser.add_argument(
# "-e", "--encoding", type=str, help="The encoding of the CSV file. 'utf-8' by default.", default="utf-8"
# )
# parser.add_argument(
# "-o", "--output_folder", type=str, help="The folder where the markdown files will be saved.", required=True
# )

# args = parser.parse_args()

# res = main(args.input_csv, args.encoding, args.output_folder)

# match res:
# case Ok(out=out):
## Unpack the zipped profiles and profiles_with_mds
# out_list = list(out)
# profiles = [tup[0] for tup in out_list]
# profiles_with_mds = [tup[1] for tup in out_list]

## 1. Write markdown files to disk
# writes = [rbind(write_md_files, p) for p in profiles_with_mds]

## 2. Produce report
# zipped = zip(profiles, writes)
# generate_report(zipped, args.output_folder, args.encoding, lgr)

# case Err(message=msg, code=code):
# pass
