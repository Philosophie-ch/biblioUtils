import os
import subprocess
from src.sdk.utils import lginf, get_logger
from src.sdk.ResultMonad import runwrap, try_except_wrapper
from src.ref_pipe.models import ProfileWithHTML, ProfileWithMD, ProfileWithRawHTML, RefHTML

from bs4 import BeautifulSoup, Tag


lgr = get_logger("Compile HTML")


@try_except_wrapper(lgr)
def dltc_env_exec(profile: ProfileWithMD, container_name: str) -> ProfileWithRawHTML:

    frame = f"dltc_env_exec"
    lginf(frame, f"Preparing command to execute in the container...", lgr)

    container_base_dir = profile.markdown.container_base_dir
    relative_output_dir = profile.markdown.relative_output_dir

    container_output_directory = f"{container_base_dir}/{relative_output_dir}"

    command = "dltc-make offhtml"
    lginf(
        frame,
        f"Executing command within the container:\n\t`{command}`\n\tIn the container directory '{container_output_directory}'",
        lgr,
    )

    subprocess.run(
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
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    raw_html_name = f"{profile.markdown.main_file.basename.replace('.md', '.html')}"
    local_output_directory = f"{profile.markdown.local_base_dir}/{relative_output_dir}"
    raw_html_filename = f"{local_output_directory}/{raw_html_name}"

    if not os.path.exists(raw_html_filename):
        msg = f"The raw HTML file '{raw_html_filename}' was not generated for profile '{profile.biblio_name}'. Exiting."
        raise FileNotFoundError(msg)

    return ProfileWithRawHTML(**profile.__dict__, raw_html_filename=raw_html_filename)


@try_except_wrapper(lgr)
def bs_get_id(page_element: Tag) -> str:
    bs_getter = page_element.get('id')
    match bs_getter:
        case None:
            return ""
        case _:
            return bs_getter.__str__()


@try_except_wrapper(lgr)
def filter_divs(divs: list[Tag], bibkeys: list[str]) -> list[str]:
    nested = [[div.__str__() for div in divs if bibkey in runwrap(bs_get_id(div))] for bibkey in bibkeys]

    flat = [div for sublist in nested for div in sublist]

    return flat


@try_except_wrapper(lgr)
def process_raw_html(profile: ProfileWithRawHTML) -> ProfileWithHTML:

    try:
        frame = f"process_html"
        lginf(frame, f"Processing the raw HTML for '{profile.lastname}'...", lgr)

        raw_html_filename = profile.raw_html_filename

        # 0. Control flow: Check if the raw HTML file exists
        if not os.path.exists(raw_html_filename):
            msg = (
                f"The raw HTML file '{raw_html_filename}' for profile '{profile.biblio_name}' does not exist. Exiting."
            )
            raise FileNotFoundError(msg)

        with open(raw_html_filename, "r") as f:
            raw_html_content = f.read()

        # 1. Parse the raw HTML content with BeautifulSoup
        soup = BeautifulSoup(raw_html_content, features="html.parser")
        divs_all = soup.find_all('div')
        divs = [div for div in divs_all if isinstance(div, Tag)]

        bibkeys = profile.biblio_keys
        bibfurther = profile.biblio_keys_further_references
        bibdeps = profile.biblio_dependencies_keys

        # 2. Filter the divs by the bibkeys
        bibkeys_div = runwrap(filter_divs(divs, bibkeys))

        local_base_dir = profile.markdown.local_base_dir
        relative_output_dir = profile.markdown.relative_output_dir
        local_output_directory = f"{local_base_dir}/{relative_output_dir}"

        references_filename = f"{local_output_directory}/{profile.biblio_name}_references.html"

        with open(references_filename, "w") as f:
            f.write("\n".join(bibkeys_div))

        if not os.path.exists(references_filename):
            msg = f"The references HTML file '{references_filename}' was not generated for profile '{profile.biblio_name}'. Exiting."
            raise FileNotFoundError(msg)

        # 3. Branches for further references and dependencies
        if bibfurther != []:
            bibfurther_div = runwrap(filter_divs(divs, bibfurther))
            further_references_filename = f"{local_output_directory}/{profile.biblio_name}_further_references.html"

            with open(further_references_filename, "w") as f:
                f.write("\n".join(bibfurther_div))

            if not os.path.exists(further_references_filename):
                msg = f"The further references HTML file '{further_references_filename}' was not generated for profile '{profile.biblio_name}'. Exiting."
                raise FileNotFoundError(msg)

        else:
            further_references_filename = None

        if bibdeps != []:
            bibdeps_div = runwrap(filter_divs(divs, bibdeps))
            dependencies_filename = f"{local_output_directory}/{profile.biblio_name}_dependencies.html"

            with open(dependencies_filename, "w") as f:
                f.write("\n".join(bibdeps_div))

            if not os.path.exists(dependencies_filename):
                msg = f"The dependencies HTML file '{dependencies_filename}' was not generated for profile '{profile.biblio_name}'. Exiting."
                raise FileNotFoundError(msg)

        else:
            dependencies_filename = None

        ref_html = RefHTML(
            references_filename=references_filename,
            further_references_filename=further_references_filename,
            dependencies_filename=dependencies_filename,
        )

        return ProfileWithHTML(**profile.__dict__, html=ref_html)

    finally:
        # Cleanup the raw HTML file
        if os.path.exists(raw_html_filename):
            os.remove(raw_html_filename)
