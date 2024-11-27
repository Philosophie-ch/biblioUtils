import os
from pathlib import Path
import shutil
import subprocess
from dotenv import load_dotenv

from src.ref_pipe.models import EnvVars
from src.sdk.utils import lginf, get_logger
from src.sdk.ResultMonad import Err, Ok, runwrap, try_except_wrapper


lgr = get_logger("Setup")


@try_except_wrapper(lgr)
def load_env_vars(env_file: str) -> EnvVars:

    if not os.path.exists(env_file):
        raise FileNotFoundError(f"The '.env' file '{env_file}' does not exist.")

    load_dotenv(dotenv_path=env_file)

    arch = os.getenv("ARCH")
    dltc_biblio = os.getenv("DLTC_BIBLIO")
    dockerhub_token = os.getenv("DOCKERHUB_TOKEN")
    dockerhub_username = os.getenv("DOCKERHUB_USERNAME")
    dltc_workhouse_directory = os.getenv("DLTC_WORKHOUSE_DIRECTORY")
    container_dltc_workhouse_directory = os.getenv("CONTAINER_DLTC_WORKHOUSE_DIRECTORY")
    ref_pipe_dir_relative_path = os.getenv("REF_PIPE_DIR_RELATIVE_PATH")
    container_name = os.getenv("CONTAINER_NAME")
    docker_compose_file = os.getenv("DOCKER_COMPOSE_FILE")
    csl_file = os.getenv("CSL_FILE")

    if not (
        arch
        and dltc_biblio
        and dockerhub_token
        and dockerhub_username
        and dltc_workhouse_directory
        and container_dltc_workhouse_directory
        and ref_pipe_dir_relative_path
        and container_name
        and docker_compose_file
        and csl_file
    ):
        raise ValueError(
            f"The '.env' file must contain the following environment variables: {EnvVars.attribute_names()}."
        )

    if arch not in ["amd64", "arm64"]:
        raise ValueError(
            f"Invalid value '{arch}' for the 'ARCH' environment variable. It must be either 'amd64' or 'arm64'."
        )

    if not os.path.exists(dltc_workhouse_directory):
        raise FileNotFoundError(
            f"The workhouse directory '{dltc_workhouse_directory}' does not exist. Please provide a valid directory."
        )

    dltc_biblio_local_path = f"{dltc_workhouse_directory}/{dltc_biblio}"

    if not os.path.exists(dltc_biblio_local_path):
        raise FileNotFoundError(
            f"The bibliography file '{dltc_biblio}' does not exist in '{dltc_workhouse_directory}'."
        )

    dltc_ref_pipe_local_path = f"{dltc_workhouse_directory}/{ref_pipe_dir_relative_path}"

    # This is our working dir, so it can be created if it doesn't exist
    os.makedirs(dltc_ref_pipe_local_path, exist_ok=True)
    # But we do need it existing
    if not os.path.exists(dltc_ref_pipe_local_path):
        raise FileNotFoundError(
            f"The reference pipeline directory '{dltc_ref_pipe_local_path}' does not exist. Please provide a valid directory."
        )

    return EnvVars(
        ARCH=arch,
        DLTC_BIBLIO=dltc_biblio,
        DOCKERHUB_TOKEN=dockerhub_token,
        DOCKERHUB_USERNAME=dockerhub_username,
        DLTC_WORKHOUSE_DIRECTORY=dltc_workhouse_directory,
        CONTAINER_DLTC_WORKHOUSE_DIRECTORY=container_dltc_workhouse_directory,
        REF_PIPE_DIR_RELATIVE_PATH=ref_pipe_dir_relative_path,
        CONTAINER_NAME=container_name,
        DOCKER_COMPOSE_FILE=docker_compose_file,
        CSL_FILE=csl_file,
    )


@try_except_wrapper(lgr)
def dltc_env_up(v: EnvVars) -> None:
    try:
        frame = f"main"

        compose_file = v.DOCKER_COMPOSE_FILE
        if not os.path.exists(compose_file):
            # Don't trust anyone
            raise FileNotFoundError(
                f"The docker-compose file '{compose_file}' does not exist. Please provide a valid file."
            )

        # 1. Load environment variables
        DOCKER_IMAGE_TAG = f"{v.DOCKERHUB_USERNAME}/{v.CONTAINER_NAME}:latest-{v.ARCH}"

        # If container is running, return early
        docker_ps_cmd = ["docker", "ps", "--format", "{{.Names}}"]
        docker_ps_r = subprocess.run(docker_ps_cmd, capture_output=True, text=True)

        if docker_ps_r.returncode == 0 and v.CONTAINER_NAME in docker_ps_r.stdout:
            lginf(frame, f"The container '{v.CONTAINER_NAME}' is already running. Skipping container setup.", lgr)
            return None

        # 2. Login to DockerHub, pull, and logout
        lginf(frame, f"Logging in to DockerHub...", lgr)
        docker_login_pull_logout_cmd = f"""
            echo {v.DOCKERHUB_TOKEN} | docker login -u {v.DOCKERHUB_USERNAME} --password-stdin && \
            docker pull {DOCKER_IMAGE_TAG} && \
            docker logout
            """
        docker_login_pull_logout_r = subprocess.run(
            docker_login_pull_logout_cmd, shell=True, capture_output=True, text=True
        )

        if docker_login_pull_logout_r.returncode != 0:
            raise ValueError(
                f"An error occurred while trying to pull the container from DockerHub:\n\t{docker_login_pull_logout_r.stderr}"
            )

        # 3. Double check that the image is in fact there
        docker_inspect_cmd = ["docker", "inspect", "--type=image", DOCKER_IMAGE_TAG]
        docker_inspect_r = subprocess.run(docker_inspect_cmd, capture_output=True, text=True)

        if docker_inspect_r.returncode != 0:
            raise ValueError(
                f"An error occurred while trying to inspect the Docker image '{DOCKER_IMAGE_TAG}':\n\t{docker_inspect_r.stderr}"
            )

        # 4. Put down any running containers, then start them again
        lginf(frame, f"Putting down running containers...", lgr)
        docker_down_cmd = ["docker", "compose", "-f", f"{compose_file}", "down"]
        docker_down_r = subprocess.run(docker_down_cmd, capture_output=True, text=True)

        if docker_down_r.returncode != 0:
            raise ValueError(
                f"An error occurred while trying to stop the running containers:\n\t{docker_down_r.stderr}"
            )

        lginf(frame, f"Starting the container...", lgr)
        docker_up_cmd = ["docker", "compose", "-f", f"{compose_file}", "up", "-d"]
        docker_up_r = subprocess.run(docker_up_cmd, capture_output=True, text=True)

        if docker_up_r.returncode != 0:
            raise ValueError(f"An error occurred while trying to start the container:\n\t{docker_up_r.stderr}")

        return None

    except subprocess.CalledProcessError as e:
        raise ValueError(f"An error occurred while running a docker command:\n\t{e.stderr}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Setup the container where to execute the compilation commands.")

    parser.add_argument(
        "-e",
        "--env_file",
        type=str,
        help="The path to the '.env' file containing the environment variables.",
        default=".env",
    )

    parser.add_argument(
        "-c",
        "--compose_file",
        type=str,
        help="The path to the docker-compose file.",
        default="docker-compose.yml",
    )

    args = parser.parse_args()

    env_vars = runwrap(load_env_vars(args.env_file))

    dltc_env_up(
        v=env_vars,
        compose_file=args.compose_file,
    )


@try_except_wrapper(lgr)
def override_csl_file(original_csl_file: str) -> None:
    """
    Override the CSL file with the one in the current directory.
    """

    path = Path(original_csl_file)
    os.makedirs(path.parent, exist_ok=True)

    if os.path.exists(original_csl_file):
        shutil.move(original_csl_file, f"{original_csl_file}.bak")

    cfp = Path(__file__)
    current_file_dir = cfp.parent
    csl_files = list(current_file_dir.glob("*.csl"))

    if len(csl_files) == 0:
        raise FileNotFoundError("No CSL files found in the current directory.")

    if len(csl_files) > 1:
        lgr.warning(
            f"More than one CSL file found in the current directory: {csl_files}. Using the first one: '{csl_files[0]}'"
        )

    csl_file = csl_files[0]

    with open(original_csl_file, "w") as f:
        with open(csl_file, "r") as csl:
            f.write(csl.read())


@try_except_wrapper(lgr)
def restore_csl_file(original_csl_file: str) -> None:
    """
    Cleans up the CSL file by restoring the original one.
    """

    if not os.path.exists(f"{original_csl_file}.bak"):
        return None

    if os.path.exists(original_csl_file):
        os.remove(original_csl_file)

    shutil.move(f"{original_csl_file}.bak", original_csl_file)

