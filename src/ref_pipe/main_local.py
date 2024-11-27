import os
from typing import Callable
from src.ref_pipe.compile_html import dltc_env_exec, process_raw_html
from src.ref_pipe.gen_md import prepare_md, write_md_files
from src.ref_pipe.models import BibEntity, BibEntityWithHTML, BibEntityWithRawHTML, THTMLReport
from src.sdk.utils import get_logger
from src.sdk.ResultMonad import Err, Ok, rbind, runwrap, try_except_wrapper

from src.ref_pipe.setup import dltc_env_up, load_env_vars, override_csl_file, restore_csl_file
from src.ref_pipe.filesystem_io import generate_report, load_bibentities_csv


lgr = get_logger("Main Local")


@try_except_wrapper(lgr)
def ref_pipe(
    bibentity: BibEntity,
    local_base_dir: str,
    container_base_dir: str,
    relative_output_dir: str,
    container_name: str,
    cleanup: bool = True,
) -> BibEntityWithHTML:

    # 1. Prepare and write MD files
    bibentity_with_mds = runwrap(
        rbind(write_md_files, prepare_md(bibentity, local_base_dir, container_base_dir, relative_output_dir))
    )

    try:

        type TProcessRaw = Callable[[BibEntityWithRawHTML], Ok[BibEntityWithHTML] | Err]
        process_raw_curr: TProcessRaw = lambda be: process_raw_html(be, cleanup)

        # 2. Produce the Raw HTML, process, and write
        bibentity_with_html = runwrap(rbind(process_raw_curr, dltc_env_exec(bibentity_with_mds, container_name)))

        return bibentity_with_html

    finally:
        if cleanup:
            # Cleanup any dangling file
            md_main_file = bibentity_with_mds.markdown.main_file.basename
            md_master_file = bibentity_with_mds.markdown.master_file.basename
            local_dir = bibentity_with_mds.markdown.local_base_dir
            relative_path = bibentity_with_mds.markdown.relative_output_dir
            full_path = os.path.join(local_dir, relative_path)

            md_main_file_path = os.path.join(full_path, md_main_file)
            md_master_file_path = os.path.join(full_path, md_master_file)

            if os.path.exists(md_main_file_path):
                os.remove(md_main_file_path)

            if os.path.exists(md_master_file_path):
                os.remove(md_master_file_path)


@try_except_wrapper(lgr)
def main_process_local(input_csv: str, encoding: str, env_file: str, cleanup: bool = True) -> THTMLReport:

    # 1. Setup
    ## 1.1 Load environment variables
    v = runwrap(load_env_vars(env_file))

    ## 1.2 Override the CSL file
    runwrap(override_csl_file(v.CSL_FILE))

    ## 1.3 Start the container
    runwrap(dltc_env_up(v))

    ## 1.4 Load the bibentities
    bibentities = runwrap(
        load_bibentities_csv(input_csv, encoding)
    )  # TODO: abstract away from CSV in particular, inject from outside

    ## 1.5 Unpack environment variables for ref_pipe
    local_base_dir, container_base_dir, relative_output_dir, container_name = (
        v.DLTC_WORKHOUSE_DIRECTORY,
        v.CONTAINER_DLTC_WORKHOUSE_DIRECTORY,
        v.REF_PIPE_DIR_RELATIVE_PATH,
        v.CONTAINER_NAME,
    )

    # 2. Main processing
    bibentities_with_htmls = [
        ref_pipe(bibentity, local_base_dir, container_base_dir, relative_output_dir, container_name, cleanup)
        for bibentity in bibentities
    ]

    # 3. Cleanup
    csl_cleanup_result = restore_csl_file(v.CSL_FILE)
    if isinstance(csl_cleanup_result, Err):
        # Don't fail the whole process if the CSL file could not be restored, just log the error
        lgr.warning(f"Error restoring the CSL file '{v.CSL_FILE}': {csl_cleanup_result.message}")

    return zip(bibentities, bibentities_with_htmls)


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

    parser.add_argument(
        "-k",
        "--keep-files",
        action="store_false",
        help="If passed, the pipe will not cleanup temporary files while processing",
        default=True,
    )

    args = parser.parse_args()

    curried_gen_report: Callable[[THTMLReport], Ok[None] | Err] = lambda out: generate_report(
        out, args.report_output_folder, args.encoding
    )

    cleanup = args.keep_files

    rbind(curried_gen_report, main_process_local(args.input_csv, args.encoding, args.env_file, cleanup))


if __name__ == "__main__":
    cli_main_process_local()
