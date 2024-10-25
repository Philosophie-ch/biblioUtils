import os
import subprocess
from src.sdk.utils import handle_error, handle_unexpected_exception
from src.sdk.ResultMonad import Err, Ok, rbind, runwrap, try_except_wrapper
from src.ref_pipe.models import EnvVars, File, Profile, ProfileWithHTML, ProfileWithMD, ProfileWithRawHTML
from src.ref_pipe.utils import CHLLGR as lgr


# Example of working docker exec command:
# docker exec dltc-env bash -c 'cd "/home/copyeditor/dltc-workhouse/2023/2023-03-issue/01-patterson" && dltc-make offhtml'


@try_except_wrapper(lgr)
def dltc_env_exec(profile: ProfileWithMD, container_name: str) -> ProfileWithRawHTML | Err:

    frame = f"dltc_env_exec"
    lgr.info(frame, f"Executing command in the dltc-env container...", lgr)

    directory = profile.markdown.base_dir

    if not os.path.exists(directory):
        return handle_error(
            frame,
            f"The base directory '{directory}' for the markdown file of '{profile.lastname}' does not exist.",
            lgr,
            -2,
        )

    command = f"'cd {directory} && dltc-make offhtml'"
    lgr.info(frame, f"Executing command: '{command}'...", lgr)

    subprocess.run(
        ["docker", "exec", container_name, "bash", "-c", command],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    raw_html_name = f"{profile.markdown.main_file.name.replace('.md', '.html')}"
    raw_html_filename = f"{directory}/{raw_html_name}"

    if not os.path.exists(raw_html_filename):
        return handle_error(frame, f"The raw HTML file '{raw_html_filename}' was not generated.", lgr, -2)

    with open(raw_html_filename, "r") as f:
        raw_html_content = f.read()

    raw_html_file = File(content=raw_html_content, name=raw_html_name)

    return ProfileWithRawHTML(**profile.__dict__, raw_html=raw_html_file)


@try_except_wrapper(lgr)
def process_html(profile: ProfileWithRawHTML) -> ProfileWithHTML | Err:

    frame = f"process_html"
    lgr.info(frame, f"Processing the raw HTML for '{profile.lastname}'...", lgr)

    raw_html = profile.raw_html

    if not raw_html:
        return handle_error(frame, f"The profile does not have the necessary raw HTML file.", lgr, -2)

    if not raw_html.content or not raw_html.name:
        return handle_error(frame, f"The raw HTML file does not have content or a name.", lgr, -3)

    