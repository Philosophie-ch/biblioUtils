import os
from typing import Callable
from src.ref_pipe.compile_html import dltc_env_exec, process_raw_html
from src.ref_pipe.gen_md import prepare_md, write_md_files
from src.ref_pipe.models import Profile, ProfileWithHTML, THTMLReport
from src.sdk.utils import get_logger
from src.sdk.ResultMonad import Err, Ok, rbind, runwrap, try_except_wrapper

from src.ref_pipe.setup import dltc_env_up, load_env_vars
from src.ref_pipe.filesystem_io import generate_report, load_profiles_csv


lgr = get_logger("Main Local")


@try_except_wrapper(lgr)
def ref_pipe(
    profile: Profile, local_base_dir: str, container_base_dir: str, relative_output_dir: str, container_name: str
) -> ProfileWithHTML:

    # 1. Prepare and write MD files
    profile_with_mds = runwrap(
        rbind(write_md_files, prepare_md(profile, local_base_dir, container_base_dir, relative_output_dir))
    )

    try:
        # 2. Produce the Raw HTML, process, and write
        profile_with_html = runwrap(rbind(process_raw_html, dltc_env_exec(profile_with_mds, container_name)))

        return profile_with_html

    finally:
        # Cleanup any dangling file
        md_main_file = profile_with_mds.markdown.main_file.basename
        md_master_file = profile_with_mds.markdown.master_file.basename
        local_dir = profile_with_mds.markdown.local_base_dir
        relative_path = profile_with_mds.markdown.relative_output_dir
        full_path = os.path.join(local_dir, relative_path)

        md_main_file_path = os.path.join(full_path, md_main_file)
        md_master_file_path = os.path.join(full_path, md_master_file)

        if os.path.exists(md_main_file_path):
            os.remove(md_main_file_path)

        if os.path.exists(md_master_file_path):
            os.remove(md_master_file_path)


@try_except_wrapper(lgr)
def main_process_local(input_csv: str, encoding: str, env_file: str) -> THTMLReport:

    # 1. Setup
    ## 1.1 Load environment variables
    v = runwrap(load_env_vars(env_file))

    ## 1.2 Start the container
    runwrap(dltc_env_up(v=v))

    ## 1.3 Load profiles
    profiles = runwrap(
        load_profiles_csv(input_csv, encoding)
    )  # TODO: abstract away from CSV in particular, inject from outside

    ## 1.4 Unpack environment variables for ref_pipe
    local_base_dir, container_base_dir, relative_output_dir, container_name = (
        v.DLTC_WORKHOUSE_DIRECTORY,
        v.CONTAINER_DLTC_WORKHOUSE_DIRECTORY,
        v.REF_PIPE_DIR_RELATIVE_PATH,
        v.CONTAINER_NAME,
    )

    # 2. Main processing
    profiles_with_htmls = [
        ref_pipe(profile, local_base_dir, container_base_dir, relative_output_dir, container_name)
        for profile in profiles
    ]

    return zip(profiles, profiles_with_htmls)


def cli_main_process_local() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Setup the dltc-env.")

    parser.add_argument("-i", "--input-csv", type=str, help="Path to the CSV file.", required=True)

    parser.add_argument(
        "-e", "--encoding", type=str, help="The encoding of the CSV file. 'utf-8' by default.", required=True
    )

    parser.add_argument("-v", "--env_file", type=str, help="Path to the environment file.", required=True)

    parser.add_argument(
        "-o",
        "--report-output-folder",
        type=str,
        help="The folder where to save the report files. Default is the current directory.",
        default=f"{os.getcwd()}/data",
    )

    args = parser.parse_args()

    curried_gen_report: Callable[[THTMLReport], Ok[None] | Err] = lambda out: generate_report(
        out, args.report_output_folder, args.encoding
    )

    rbind(curried_gen_report, main_process_local(args.input_csv, args.encoding, args.env_file))


if __name__ == "__main__":
    cli_main_process_local()
