import os
from typing import Callable
from src.ref_pipe.generate_html import gen_html_files
from src.ref_pipe.prep_divs import gen_bib_html_divs
from src.ref_pipe.models import BibEntity, BibEntityWithHTML, Bibliography, THTMLReport, TSupportedEntity
from src.sdk.utils import get_logger
from src.sdk.ResultMonad import Err, Ok, rbind, runwrap, try_except_wrapper

from src.ref_pipe.setup import dltc_env_up, load_env_vars, override_csl_file, restore_csl_file
from src.ref_pipe.filesystem_io import generate_report_for_html_files, load_bibentities, load_bibliography


lgr = get_logger("Main Local")


@try_except_wrapper(lgr)
def ref_pipe(
    bibentity: BibEntity,
    bibliography: Bibliography,
    local_base_dir: str,
    container_base_dir: str,
    relative_output_dir: str,
    container_name: str,
) -> BibEntityWithHTML:

    # 1. Prepare divs for the bibentity
    bibdivs = runwrap(
        gen_bib_html_divs(
            bibentity,
            bibliography,
            local_base_dir,
            container_base_dir,
            relative_output_dir,
            container_name,
        )
    )

    # 2. Prepare html files per bibentity
    bibentity_with_html = runwrap(
        gen_html_files(
            bibentity,
            bibdivs,
            f"{local_base_dir}/{relative_output_dir}",
        )
    )

    return bibentity_with_html


@try_except_wrapper(lgr)
def main_process_local(
    input_csv: str,
    encoding: str,
    entity_type: TSupportedEntity,
    env_file: str,
) -> THTMLReport:

    # 1. Setup
    ## 1.1 Load environment variables
    v = runwrap(load_env_vars(env_file))

    ## 1.2 Override the CSL file
    runwrap(override_csl_file(v.CSL_FILE))

    ## 1.3 Start the container
    runwrap(dltc_env_up(v))

    ## 1.4 Unpack environment variables for ref_pipe
    local_base_dir, container_base_dir, relative_output_dir, container_name = (
        v.DLTC_WORKHOUSE_DIRECTORY,
        v.CONTAINER_DLTC_WORKHOUSE_DIRECTORY,
        v.REF_PIPE_DIR_RELATIVE_PATH,
        v.DOCKER_CONTAINER_NAME,
    )

    ## 1.5 Load the bibliography
    local_bibliography_filepth = f"{local_base_dir}/{v.BIBLIOGRAPHY_BASE_FILENAME}"
    bibliography = runwrap(load_bibliography(local_bibliography_filepth))

    ## 1.6 Load the bibentities
    bibentities = runwrap(
        load_bibentities(input_csv, encoding, entity_type, bibliography)
    )  # TODO: abstract away from CSV in particular, inject from outside

    # 2. Main processing
    bibentities_with_htmls = [
        ref_pipe(
            bibentity,
            bibliography,
            local_base_dir,
            container_base_dir,
            relative_output_dir,
            container_name,
        )
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

    parser.add_argument(
        "-t",
        "--entity-type",
        type=str,
        help="The type of the entity to process. Must be one of 'profile' or 'article'.",
        required=True,
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

    curried_gen_report: Callable[[THTMLReport], Ok[None] | Err] = lambda out: generate_report_for_html_files(
        out, args.report_output_folder, args.encoding
    )

    rbind(
        curried_gen_report,
        main_process_local(
            args.input_csv,
            args.encoding,
            args.entity_type,
            args.env_file,
        ),
    )


if __name__ == "__main__":
    cli_main_process_local()
