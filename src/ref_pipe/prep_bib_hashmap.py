import os
import subprocess
from typing import Dict, FrozenSet, Generator, Iterable, Tuple

from bs4 import BeautifulSoup, Tag

from src.sdk.utils import get_logger, lginf
from src.sdk.ResultMonad import runwrap, try_except_wrapper
from src.ref_pipe.models import Bibliography, File, BibEntity, BibentityHTMLRawFile, Markdown


lgr = get_logger("Generate Markdown")


MD_TEMPLATE = """---
title: "HTML References Pipeline"
bibliography: biblio.bib
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
    pass


@try_except_wrapper(lgr)
def prepare_bib_md(
    markdown_filename: str,
    bibkeys: Iterable[str],
    local_base_dir: str,
    container_base_dir: str,
    relative_output_dir: str,
) -> Markdown:

    bibkeys_str = "\n\n".join(f"@{key}" for key in bibkeys)

    main_content = MD_TEMPLATE.replace("~%~%~%PUT THE BIBKEYS HERE~%~%~%", bibkeys_str)
    main_md = File(content=main_content, basename=f"{markdown_filename}.md")

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
    bib_md = prepared_md

    output_local_dir = f"{bib_md.local_base_dir}/{bib_md.relative_output_dir}"
    if not os.path.exists(output_local_dir):
        raise FileNotFoundError(f"The output directory '{output_local_dir}' does not exist.")

    for file in [bib_md.main_file, bib_md.master_file]:
        if not file or not file.content or not file.basename:
            raise ValueError(f"The markdown file '{file.basename}' does not have content or a name.")

    main_file_path = bib_md.main_file.full_file_path(output_local_dir)
    master_file_path = bib_md.master_file.full_file_path(output_local_dir)

    with open(main_file_path, "w") as f:
        f.write(bib_md.main_file.content)

    if not os.path.exists(main_file_path):
        raise FileNotFoundError(f"The markdown file '{main_file_path}' was not written successfully.")

    with open(master_file_path, "w") as f:
        f.write(bib_md.master_file.content)

    if not os.path.exists(master_file_path):
        raise FileNotFoundError(f"The markdown file '{master_file_path}' was not written successfully.")

    # consume the contents to save memory
    bib_md.main_file.content = ""
    bib_md.master_file.content = ""

    return bib_md


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


@try_except_wrapper(lgr)
def bs_get_div_bibkey(page_element: Tag) -> str:
    bs_getter = page_element.get('id')
    match bs_getter:
        case None:
            return ""
        case _:
            return get_bibkey_from_div_id(bs_getter.__str__())


def get_div_for_bibkey(bibkey: str, divs: Tuple[Tag, ...]) -> str:
    filtered = tuple(div for div in divs if runwrap(bs_get_div_bibkey(div)) == bibkey)

    if len(filtered) > 1:
        raise ValueError(f"Could not find a unique div for bibkey '{bibkey}'. Found {len(filtered)} divs for {bibkey}.")

    if len(filtered) == 0:
        lgr.warning(f"Could not find a div for bibkey '{bibkey}'.")
        return ""

    return filtered[0].__str__()


@try_except_wrapper(lgr)
def gen_bib_html_files(
    bibkeys: FrozenSet[str],
    local_base_dir: str,
    container_base_dir: str,
    relative_output_dir: str,
    container_name: str,
) -> Tuple[BibentityHTMLRawFile, ...]:

    frame = f"gen_bib_html_file"
    lginf(frame, f"Generating HTML file for the bibliography...", lgr)

    # if the length of bibkeys is > 2000000, then we break the process into smaller chunks

    bibkeys_list = tuple(bibkeys)
    chunks = tuple(bibkeys_list[i : i + 2000000] for i in range(0, len(bibkeys_list), 2000000))

    chunks_filenames = []

    for n, chunk in enumerate(chunks):
        lginf(frame, f"Processing chunk {n+1} of {len(chunks)}...", lgr)
        # Check if the chunk file already exists, if so, skip
        chunk_html_basename = f"biblio_{n}.html"
        chunk_local_output_directory = f"{local_base_dir}/{relative_output_dir}"
        chunk_html_filename = f"{chunk_local_output_directory}/{chunk_html_basename}"

        if os.path.exists(chunk_html_filename):
            lginf(frame, f"Chunk HTML file '{chunk_html_filename}' already exists. Skipping...", lgr)

        else:
            # Run the pipeline for the chunk
            chunk_bib_md = runwrap(prepare_bib_md(chunk, local_base_dir, container_base_dir, relative_output_dir))
            chunk_bib_md = runwrap(write_bib_md_files(chunk_bib_md))
            chunk_bib_html = runwrap(dltc_env_exec(chunk_bib_md, container_name))

            # move the chunk_bib_html to a different name to preserve it
            os.rename(chunk_bib_html.local_path, chunk_html_filename)

        lginf(frame, f"Chunk HTML file '{chunk_html_filename}' generated successfully.", lgr)
        chunks_filenames.append(chunk_html_filename)

    return tuple(BibentityHTMLRawFile(local_path=filename) for filename in chunks_filenames)


@try_except_wrapper(lgr)
def extract_divs(html_bib_file: BibentityHTMLRawFile) -> Generator[Tag, None, None]:

    with open(html_bib_file.local_path, "r") as f:
        bib_html_content = f.read()

    # 1. Parse the HTML content with BeautifulSoup and extract div Tag objects
    soup = BeautifulSoup(bib_html_content, features="html.parser")
    divs_all = soup.find_all('div')
    divs = (div for div in divs_all if isinstance(div, Tag))

    return divs


@try_except_wrapper(lgr)
def gen_bib_html_hashmap(
    bibliography: Bibliography,
    local_base_dir: str,
    container_base_dir: str,
    relative_output_dir: str,
    container_name: str,
) -> Dict[str, str]:

    frame = f"gen_bib_html_hashmap"
    lginf(frame, f"Generating HTML hashmap with bibkey: div, for the bibliography...", lgr)

    bibkeys = bibliography.bibkeys

    html_bib_files = runwrap(
        gen_bib_html_files(bibkeys, local_base_dir, container_base_dir, relative_output_dir, container_name)
    )

    all_divs = tuple(div for html_bib_file in html_bib_files for div in runwrap(extract_divs(html_bib_file)))

    # 2. Create a hashmap of bibkey: div
    result = {bibkey: get_div_for_bibkey(bibkey, all_divs) for bibkey in bibkeys}

    return result


# @try_except_wrapper(lgr)
# def prepare_md(
# bibentity: BibEntity, local_base_dir: str, container_base_dir: str, relative_output_dir: str
# ) -> BibEntityWithMD:

# biblio_keys = sorted(bibentity.main_bibkeys | bibentity.further_references | bibentity.depends_on)

# biblio_keys_str = "\n\n".join(tuple(f"@{key}" for key in biblio_keys))

# main_content = MD_TEMPLATE.replace("~%~%~%PUT THE BIBKEYS HERE~%~%~%", biblio_keys_str)
# main_md = File(content=main_content, basename=f"{bibentity.url_endpoint}.md")

# master_content = MASTER_MD_TEMPLATE.replace("~%~%~%md_filename~%~%~%", main_md.basename)
# master_md = File(content=master_content, basename=f"master.md")

# md = Markdown(
# local_base_dir=local_base_dir,
# container_base_dir=container_base_dir,
# relative_output_dir=relative_output_dir,
# main_file=main_md,
# master_file=master_md,
# )

# bibentity_with_md = BibEntityWithMD(
# id=bibentity.id,
# entity_key=bibentity.entity_key,
# url_endpoint=bibentity.url_endpoint,
# main_bibkeys=bibentity.main_bibkeys,
# further_references=bibentity.further_references,
# depends_on=bibentity.depends_on,
# markdown=md,
# )

# return bibentity_with_md


# @try_except_wrapper(lgr)
# def write_md_files(bibentity: BibEntityWithMD) -> BibEntityWithMD:
# md = bibentity.markdown

# if not md:
# raise ValueError(f"The markdown object for [[ {bibentity.id} -- {bibentity.entity_key} ]] is missing.")

# output_local_dir = f"{md.local_base_dir}/{md.relative_output_dir}"
# if not os.path.exists(output_local_dir):
# raise FileNotFoundError(f"The output directory '{output_local_dir}' does not exist.")

# for file in [md.main_file, md.master_file]:
# if not file or not file.content or not file.basename:
# raise ValueError(f"The markdown file '{file.basename}' does not have content or a name.")

# main_file_path = md.main_file.full_file_path(output_local_dir)
# master_file_path = md.master_file.full_file_path(output_local_dir)

# with open(main_file_path, "w") as f:
# f.write(md.main_file.content)

# if not os.path.exists(main_file_path):
# raise FileNotFoundError(f"The markdown file '{main_file_path}' was not written successfully.")

# with open(master_file_path, "w") as f:
# f.write(md.master_file.content)

# if not os.path.exists(master_file_path):
# raise FileNotFoundError(f"The markdown file '{master_file_path}' was not written successfully.")

## consume the contents to save memory
# bibentity.markdown.main_file.content = ""
# bibentity.markdown.master_file.content = ""

# return bibentity
