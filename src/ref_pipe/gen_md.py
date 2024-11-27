import os

from src.sdk.utils import get_logger
from src.sdk.ResultMonad import try_except_wrapper
from src.ref_pipe.models import File, BibEntity, Markdown, BibEntityWithMD


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
    bibentity: BibEntity, local_base_dir: str, container_base_dir: str, relative_output_dir: str
) -> BibEntityWithMD:

    biblio_keys = bibentity.biblio_keys

    biblio_keys_str = "\n\n".join([f"@{key}" for key in biblio_keys])

    main_content = MD_TEMPLATE.replace("~%~%~%PUT THE BIBKEYS HERE~%~%~%", biblio_keys_str)
    main_md = File(content=main_content, basename=f"{bibentity.id}_{bibentity.entity_key}.md")

    master_content = MASTER_MD_TEMPLATE.replace("~%~%~%md_filename~%~%~%", main_md.basename)
    master_md = File(content=master_content, basename=f"master.md")

    md = Markdown(
        local_base_dir=local_base_dir,
        container_base_dir=container_base_dir,
        relative_output_dir=relative_output_dir,
        main_file=main_md,
        master_file=master_md,
    )

    bibentity_with_md = BibEntityWithMD(
        id=bibentity.id,
        entity_key=bibentity.entity_key,
        biblio_keys=bibentity.biblio_keys,
        biblio_keys_further_references=bibentity.biblio_keys_further_references,
        biblio_dependencies_keys=bibentity.biblio_dependencies_keys,
        markdown=md,
    )

    return bibentity_with_md


@try_except_wrapper(lgr)
def write_md_files(bibentity: BibEntityWithMD) -> BibEntityWithMD:
    md = bibentity.markdown

    if not md:
        raise ValueError(f"The markdown object for [[ {bibentity.id} -- {bibentity.entity_key} ]] is missing.")

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
    bibentity.markdown.main_file.content = ""
    bibentity.markdown.master_file.content = ""

    return bibentity
