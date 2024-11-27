import os
import subprocess
from typing import Tuple
from src.sdk.utils import lginf, get_logger
from src.sdk.ResultMonad import runwrap, try_except_wrapper
from src.ref_pipe.models import BibEntityWithHTML, BibEntityWithMD, BibEntityWithRawHTML, RefHTML

from bs4 import BeautifulSoup, Tag


lgr = get_logger("Compile HTML")


@try_except_wrapper(lgr)
def dltc_env_exec(bibentity: BibEntityWithMD, container_name: str) -> BibEntityWithRawHTML:

    frame = f"dltc_env_exec"
    lginf(frame, f"{bibentity.entity_key} -- preparing compilation command to execute in the container...", lgr)

    container_base_dir = bibentity.markdown.container_base_dir
    relative_output_dir = bibentity.markdown.relative_output_dir

    container_output_directory = f"{container_base_dir}/{relative_output_dir}"

    command = "dltc-make offhtml"
    lginf(
        frame,
        f"Executing command within the container:\n\t`{command}`\n\tIn the container directory '{container_output_directory}'",
        lgr,
    )

    compilation_result = subprocess.run(
        [
            "docker",
            "exec",
            "--workdir",
            container_output_directory,
            container_name,
            "bash",
            "-c",
            command,
        ],
        capture_output=True,
    )

    if compilation_result.returncode != 0:
        msg = f"{compilation_result.stderr.decode('utf-8')}"
        if msg == "":
            msg = f"{compilation_result.stdout.decode('utf-8')}"
        if msg == "":
            msg = f"An unknown error occurred while executing the command '{command}' in the container '{container_name}'."

        raise RuntimeError(msg)

    lginf(frame, f"{compilation_result.stdout.decode('utf-8')}", lgr)

    raw_html_name = f"{bibentity.markdown.main_file.basename.replace('.md', '.html')}"
    local_output_directory = f"{bibentity.markdown.local_base_dir}/{relative_output_dir}"
    raw_html_filename = f"{local_output_directory}/{raw_html_name}"

    if not os.path.exists(raw_html_filename):
        msg = f"The raw HTML file '{raw_html_filename}' was not generated for '{bibentity.entity_key}'. Exiting."
        raise FileNotFoundError(msg)

    return BibEntityWithRawHTML(
        id=bibentity.id,
        entity_key=bibentity.entity_key,
        url_endpoint=bibentity.url_endpoint,
        main_bibkeys=bibentity.main_bibkeys,
        further_references=bibentity.further_references,
        depends_on=bibentity.depends_on,
        markdown=bibentity.markdown,
        raw_html_filename=raw_html_filename,
    )


def get_bibkey_from_div_id(div_id: str) -> str:
    """
    Extract the bibkey from the div ID. WARNING: if the HTML structure changes, this function will produce nonsense and will need update.

    This assumes IDs of the shape:
    `ref-<entity_key>-<bibkey>`, where <bibkey> can contain "-"

    For example:
    ref-c1-ashby_n:2002
    ref-c1-caruso_em-etal:2008
    """
    try:
        bibkey = "-".join(div_id.split('-')[2:])
    except IndexError:
        lgr.warning(f"Could not find bibkey in div ID '{div_id}'")
        bibkey = ""

    return bibkey


@try_except_wrapper(lgr)
def bs_get_div_bibkey(page_element: Tag) -> str:
    bs_getter = page_element.get('id')
    match bs_getter:
        case None:
            return ""
        case _:
            return get_bibkey_from_div_id(bs_getter.__str__())


@try_except_wrapper(lgr)
def filter_divs(divs: list[Tag], bibkeys: list[str]) -> Tuple[str, ...]:
    """
    Filter BeautifulSoup divs by the bibkeys in their ids, while keeping the order of the original divs.
    """
    divs_and_bibkeys = ((div.__str__(), runwrap(bs_get_div_bibkey(div))) for div in divs)

    filtered_divs = tuple(
        div for div, div_bibkey in divs_and_bibkeys if any(div_bibkey == bibkey for bibkey in bibkeys)
    )

    return filtered_divs


@try_except_wrapper(lgr)
def process_raw_html(bibentity: BibEntityWithRawHTML, cleanup: bool = True) -> BibEntityWithHTML:

    try:
        frame = f"process_html"
        lginf(frame, f"Processing the raw HTML for '{bibentity.entity_key}'...", lgr)

        raw_html_filename = bibentity.raw_html_filename

        # 0. Control flow: Check if the raw HTML file exists
        if not os.path.exists(raw_html_filename):
            msg = f"The raw HTML file '{raw_html_filename}' for '{bibentity.entity_key}' does not exist. Exiting."
            raise FileNotFoundError(msg)

        with open(raw_html_filename, "r") as f:
            raw_html_content = f.read()

        # 1. Parse the raw HTML content with BeautifulSoup and extract div Tag objects
        soup = BeautifulSoup(raw_html_content, features="html.parser")
        divs_all = soup.find_all('div')
        divs = tuple(div for div in divs_all if isinstance(div, Tag))

        bibkeys = bibentity.main_bibkeys
        bibfurther = bibentity.further_references
        bibdeps = bibentity.depends_on

        # 2. Filter the divs by the bibkeys
        bibkeys_div = runwrap(filter_divs(divs, bibkeys))

        local_base_dir = bibentity.markdown.local_base_dir
        relative_output_dir = bibentity.markdown.relative_output_dir
        local_output_directory = f"{local_base_dir}/{relative_output_dir}"

        references_filename = f"{local_output_directory}/{bibentity.url_endpoint}-references.html"

        with open(references_filename, "w") as f:
            f.write("\n".join(bibkeys_div))

        if not os.path.exists(references_filename):
            msg = f"The references HTML file '{references_filename}' was not generated for '{bibentity.entity_key}'. Exiting."
            raise FileNotFoundError(msg)

        # 3. Branches for further references and dependencies
        if bibfurther != frozenset():
            bibfurther_div = runwrap(filter_divs(divs, bibfurther))
            further_references_filename = f"{local_output_directory}/{bibentity.url_endpoint}-further-references.html"

            with open(further_references_filename, "w") as f:
                f.write("\n".join(bibfurther_div))

            if not os.path.exists(further_references_filename):
                msg = f"The further references HTML file '{further_references_filename}' was not generated for '{bibentity.entity_key}'. Exiting."
                raise FileNotFoundError(msg)

        else:
            further_references_filename = None

        if bibdeps != frozenset():
            bibdeps_div = runwrap(filter_divs(divs, bibdeps))
            dependencies_filename = f"{local_output_directory}/{bibentity.url_endpoint}-dependencies.html"

            with open(dependencies_filename, "w") as f:
                f.write("\n".join(bibdeps_div))

            if not os.path.exists(dependencies_filename):
                msg = f"The dependencies HTML file '{dependencies_filename}' was not generated for '{bibentity.entity_key}'. Exiting."
                raise FileNotFoundError(msg)

        else:
            dependencies_filename = None

        ref_html = RefHTML(
            references_filename=references_filename,
            further_references_filename=further_references_filename,
            dependencies_filename=dependencies_filename,
        )

        return BibEntityWithHTML(
            id=bibentity.id,
            entity_key=bibentity.entity_key,
            url_endpoint=bibentity.url_endpoint,
            main_bibkeys=bibentity.main_bibkeys,
            further_references=bibentity.further_references,
            depends_on=bibentity.depends_on,
            markdown=bibentity.markdown,
            raw_html_filename=bibentity.raw_html_filename,
            html=ref_html,
        )

    finally:
        if cleanup:
            # Cleanup the raw HTML file
            if os.path.exists(raw_html_filename):
                os.remove(raw_html_filename)
