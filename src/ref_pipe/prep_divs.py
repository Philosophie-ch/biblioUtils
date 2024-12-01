import os
import subprocess
from typing import FrozenSet, Generator, Tuple

from bs4 import BeautifulSoup, Tag

from src.sdk.utils import get_logger, lginf
from src.sdk.ResultMonad import runwrap, try_except_wrapper
from src.ref_pipe.models import BibDiv, BibentityHTMLRawFile, Bibliography, File, BibEntity, Markdown


lgr = get_logger("Prepare Divs")


SMALL_BIB_NAME = "biblio.bib"

MD_TEMPLATE = f"""---
title: "HTML References Pipeline"
bibliography: {SMALL_BIB_NAME}
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
def prepare_small_bib(
    bib_entity: BibEntity,
    bibliography: Bibliography,
    local_base_dir: str,
    relative_output_dir: str,
) -> None:
    """
    Generates a small bibliography file containing only the lines of the bibkeys in the bib_entity.
    """
    bibkeys_needed = bib_entity.main_bibkeys | bib_entity.further_references | bib_entity.depends_on

    # Assert all the bibentity bibkeys are in the bibliography
    if not bibkeys_needed.issubset(bibliography.bibkeys):
        missing_bibkeys = bibkeys_needed - bibliography.bibkeys
        raise ValueError(
            f"Missing bibkeys for {bib_entity.entity_key} in the bibliography: {', '.join(sorted(missing_bibkeys))}"
        )

    bibkeys_index_dict = bibliography.bibkey_index_dict

    indexes_needed = tuple(bibkeys_index_dict[bibkey] for bibkey in bibkeys_needed)

    small_bib_content = tuple(bibliography.content[i] for i in indexes_needed)

    small_bib_filename = f"{local_base_dir}/{relative_output_dir}/{SMALL_BIB_NAME}"

    with open(small_bib_filename, "w") as f:
        f.write("".join(small_bib_content))

    if not os.path.exists(small_bib_filename):
        raise FileNotFoundError(
            f"The small bibliography file '{small_bib_filename}' was not generated successfully for '{bib_entity.entity_key}'."
        )

    return None


@try_except_wrapper(lgr)
def prepare_md(
    markdown_basename: str,
    bibkeys: FrozenSet[str],
    local_base_dir: str,
    container_base_dir: str,
    relative_output_dir: str,
) -> Markdown:

    bibkeys_str = "\n\n".join(f"@{key}" for key in bibkeys)

    main_content = MD_TEMPLATE.replace("~%~%~%PUT THE BIBKEYS HERE~%~%~%", bibkeys_str)
    main_md = File(content=main_content, basename=f"{markdown_basename}.md")

    master_content = MASTER_MD_TEMPLATE.replace("~%~%~%md_filename~%~%~%", main_md.basename)
    master_md = File(content=master_content, basename=f"master.md")

    md = Markdown(
        local_base_dir=local_base_dir,
        container_base_dir=container_base_dir,
        relative_output_dir=relative_output_dir,
        main_file=main_md,
        master_file=master_md,
    )

    return md


@try_except_wrapper(lgr)
def write_bib_md_files(prepared_md: Markdown) -> Markdown:
    refs_md = prepared_md

    output_local_dir = f"{refs_md.local_base_dir}/{refs_md.relative_output_dir}"
    if not os.path.exists(output_local_dir):
        raise FileNotFoundError(f"The output directory '{output_local_dir}' does not exist.")

    for file in [refs_md.main_file, refs_md.master_file]:
        if not file or not file.content or not file.basename:
            raise ValueError(f"The markdown file '{file.basename}' does not have content or a name.")

    main_file_path = refs_md.main_file.full_file_path(output_local_dir)
    master_file_path = refs_md.master_file.full_file_path(output_local_dir)

    with open(main_file_path, "w") as f:
        f.write(refs_md.main_file.content)

    if not os.path.exists(main_file_path):
        raise FileNotFoundError(f"The markdown file '{main_file_path}' was not written successfully.")

    with open(master_file_path, "w") as f:
        f.write(refs_md.master_file.content)

    if not os.path.exists(master_file_path):
        raise FileNotFoundError(f"The markdown file '{master_file_path}' was not written successfully.")

    # consume the contents to save memory
    refs_md.main_file.content = ""
    refs_md.master_file.content = ""

    return refs_md


@try_except_wrapper(lgr)
def dltc_env_exec(prepared_md: Markdown, container_name: str) -> BibentityHTMLRawFile:

    frame = f"dltc_env_exec"
    lginf(frame, f"Preparing compilation command to execute in the container...", lgr)

    bib_md = prepared_md
    container_base_dir = bib_md.container_base_dir
    relative_output_dir = bib_md.relative_output_dir

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

    html_basename = f"{bib_md.main_file.basename.replace('.md', '.html')}"
    local_output_directory = f"{bib_md.local_base_dir}/{relative_output_dir}"
    html_filename = f"{local_output_directory}/{html_basename}"

    if not os.path.exists(html_filename):
        msg = f"The raw HTML file '{html_filename}' was not generated for the bibliography. Exiting."
        raise FileNotFoundError(msg)

    return BibentityHTMLRawFile(
        local_path=html_filename,
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


def bs_get_div_bibkey(page_element: Tag) -> str:
    bs_getter = page_element.get('id')
    match bs_getter:
        case None:
            return ""
        case _:
            return get_bibkey_from_div_id(bs_getter.__str__())


@try_except_wrapper(lgr)
def gen_raw_html_file(
    bibentity: BibEntity,
    bibliography: Bibliography,
    local_base_dir: str,
    container_base_dir: str,
    relative_output_dir: str,
    container_name: str,
) -> BibentityHTMLRawFile:

    frame = f"gen_bib_html_file"
    lginf(frame, f"Generating HTML file for the bibliography...", lgr)

    # We need the main bibkeys and the further references in the final HTML, but not the dependencies (those only go in the small bib)
    bibkeys = bibentity.main_bibkeys | bibentity.further_references

    files_basename = f"{bibentity.url_endpoint}"

    runwrap(prepare_small_bib(bibentity, bibliography, local_base_dir, relative_output_dir))

    md = runwrap(
        prepare_md(
            markdown_basename=files_basename,
            bibkeys=bibkeys,
            local_base_dir=local_base_dir,
            container_base_dir=container_base_dir,
            relative_output_dir=relative_output_dir,
        )
    )
    md = runwrap(write_bib_md_files(md))
    raw_html_file = runwrap(dltc_env_exec(md, container_name))

    lginf(frame, f"HTML file '{raw_html_file.local_path}' generated successfully.", lgr)

    return raw_html_file


@try_except_wrapper(lgr)
def extract_divs(html_bib_file: BibentityHTMLRawFile) -> Generator[BibDiv, None, None]:

    with open(html_bib_file.local_path, "r") as f:
        bib_html_content = f.read()

    # Parse the HTML content with extract div
    ### NOTE: this is married to the external library BeautifulSoup
    soup = BeautifulSoup(bib_html_content, features="html.parser")
    divs_all = soup.find_all('div')
    divs = (div for div in divs_all if isinstance(div, Tag))

    bibdivs = (
        BibDiv(div_id=bs_get_div_bibkey(div), content=div.__str__()) for div in divs if bs_get_div_bibkey(div) != ""
    )
    ### NOTE: marriage to BeautifulSoup ends here

    return bibdivs


@try_except_wrapper(lgr)
def gen_bib_html_divs(
    bibentity: BibEntity,
    bibliography: Bibliography,
    local_base_dir: str,
    container_base_dir: str,
    relative_output_dir: str,
    container_name: str,
) -> Tuple[BibDiv, ...]:

    try:
        frame = f"gen_bib_html_divs"
        lginf(frame, f"Generating divs for {bibentity.entity_key}...", lgr)

        main_bibkeys = bibentity.main_bibkeys

        if main_bibkeys == frozenset():
            # Skip if there are no main bibkeys
            return tuple()

        html_bib_file = runwrap(
            gen_raw_html_file(
                bibentity,
                bibliography,
                local_base_dir,
                container_base_dir,
                relative_output_dir,
                container_name,
            )
        )

        bibdivs = tuple(div for div in runwrap(extract_divs(html_bib_file)))

        lginf(frame, f"Divs generated successfully for {bibentity.entity_key}.", lgr)

        return bibdivs

    finally:
        # re-craft filenames in case of error
        base_filename = f"{bibentity.url_endpoint}"
        md_file = f"{local_base_dir}/{relative_output_dir}/{base_filename}.md"
        master_file = f"{local_base_dir}/{relative_output_dir}/master.md"
        html_file = f"{local_base_dir}/{relative_output_dir}/{base_filename}.html"
        bib_file = f"{local_base_dir}/{relative_output_dir}/{SMALL_BIB_NAME}"

        for file in [md_file, master_file, html_file, bib_file]:
            if os.path.exists(file):
                os.remove(file)
            if os.path.exists(file):
                lgr.warning(f"Could not remove file '{file}'.")
