import os
from typing import Callable
from src.ref_pipe.compile_html import dltc_env_exec, process_raw_html
from src.ref_pipe.gen_md import prepare_md, write_md_files
from src.ref_pipe.models import Profile, ProfileWithHTML, THTMLReport
from src.sdk.utils import lginf
from src.sdk.ResultMonad import Err, Ok, rbind, runwrap, try_except_wrapper

from src.ref_pipe.setup import dltc_env_up, load_env_vars
from src.ref_pipe.utils import MAINLGR as lgr, generate_report, load_profiles_csv


@try_except_wrapper(lgr)
def ref_pipe(profile: Profile, output_dir: str, container_name: str) -> ProfileWithHTML:

    frame = f"ref_pipe_local"

    # 1. Prepare and write MD files
    profile_with_mds = runwrap(rbind(write_md_files, prepare_md(profile, output_dir)))

    # 2. Produce the Raw HTML, process, and write
    profile_with_html = runwrap(rbind(process_raw_html, dltc_env_exec(profile_with_mds, container_name)))

    lginf(frame, f"Profile '{profile.id}' processed successfully.", lgr)

    return profile_with_html


@try_except_wrapper(lgr)
def main_local(input_csv: str, encoding: str, env_file: str, compose_file: str) -> THTMLReport:

    frame = f"main"

    # 1. Setup
    v = runwrap(load_env_vars(env_file))
    runwrap(dltc_env_up(v=v, compose_file=compose_file))

    profiles = runwrap(load_profiles_csv(input_csv, encoding))

    output_dir = f"{v.DLTC_WORKHOUSE_DIRECTORY}/tests/test-issue/13-ref-pipe"
    os.makedirs(output_dir, exist_ok=True)

    # 2. Main processing
    profiles_with_htmls = [ref_pipe(profile, output_dir, v.CONTAINER_NAME) for profile in profiles]

    lginf(frame, f"Profiles processed successfully.", lgr)

    return zip(profiles, profiles_with_htmls)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Setup the dltc-env.")

    parser.add_argument("-v", "--env_file", type=str, help="Path to the environment file.", required=True)

    parser.add_argument("-c", "--compose_file", type=str, help="Path to the docker-compose file.", required=True)

    parser.add_argument("-i", "--input_csv", type=str, help="Path to the CSV file.")

    parser.add_argument(
        "-e", "--encoding", type=str, help="The encoding of the CSV file. 'utf-8' by default.", default="utf-8"
    )

    parser.add_argument(
        "-o", "--output_folder", type=str, help="The folder where the markdown files will be saved.", required=True
    )

    args = parser.parse_args()

    curried_gen_report: Callable[[THTMLReport], Ok[None] | Err] = lambda out: generate_report(
        out, args.output_folder, args.encoding
    )

    res = rbind(curried_gen_report, main_local(args.input_csv, args.encoding, args.env_file, args.compose_file))
