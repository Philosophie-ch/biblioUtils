import os
import subprocess
from dotenv import load_dotenv

from src.ref_pipe.models import EnvVars
from src.sdk.utils import handle_error, handle_unexpected_exception, lginf
from src.sdk.ResultMonad import Err, Ok, runwrap
from src.ref_pipe.utils import DTSLGR as lgr


def load_env_vars(env_file: str) -> Ok[EnvVars] | Err:
    try:
        frame = f"load_env_vars"
        lginf(frame, f"Loading environment variables from the '.env' file...", lgr)

        if not os.path.exists(env_file):
            return handle_error(frame, f"The '.env' file '{env_file}' does not exist.", lgr, -2)

        load_dotenv(dotenv_path=env_file)

        arch = os.getenv("ARCH")
        dltc_biblio = os.getenv("DLTC_BIBLIO")
        dockerhub_token = os.getenv("DOCKERHUB_TOKEN")
        dockerhub_username = os.getenv("DOCKERHUB_USERNAME")
        dltc_workhouse_directory = os.getenv("DLTC_WORKHOUSE_DIRECTORY")
        ref_pipe_directory = os.getenv("REF_PIPE_DIRECTORY")

        if not (
            arch
            and dltc_biblio
            and dockerhub_token
            and dockerhub_username
            and dltc_workhouse_directory
            and ref_pipe_directory
        ):
            return handle_error(
                frame,
                f"The '.env' file must contain the following environment variables: {EnvVars.attribute_names()}.",
                lgr,
                -2,
            )

        if arch not in ["amd64", "arm64"]:
            return handle_error(
                frame,
                f"Invalid value '{arch}' for the 'ARCH' environment variable. It must be either 'amd64' or 'arm64'.",
                lgr,
                -3,
            )

        if not os.path.exists(dltc_biblio):
            return handle_error(
                frame, f"The bibliography file '{dltc_biblio}' does not exist. Please provide a valid file.", lgr, -4
            )

        if not os.path.exists(dltc_workhouse_directory):
            return handle_error(
                frame,
                f"The workhouse directory '{dltc_workhouse_directory}' does not exist. Please provide a valid directory.",
                lgr,
                -5,
            )

        os.makedirs(ref_pipe_directory, exist_ok=True)
        if not os.path.exists(ref_pipe_directory):
            return handle_error(
                frame,
                f"The reference pipeline directory '{ref_pipe_directory}' does not exist. Please provide a valid directory.",
                lgr,
                -6,
            )

        return Ok(
            out=EnvVars(
                ARCH=arch,
                DLTC_BIBLIO=dltc_biblio,
                DOCKERHUB_TOKEN=dockerhub_token,
                DOCKERHUB_USERNAME=dockerhub_username,
                DLTC_WORKHOUSE_DIRECTORY=dltc_workhouse_directory,
                REF_PIPE_DIRECTORY=ref_pipe_directory,
            )
        )

    except Exception as e:
        return handle_unexpected_exception(
            f"An error occurred while trying to load the environment variables from the '.env' file:\n\t{e}", lgr, -1
        )


def dltc_env_up(v: EnvVars, compose_file: str) -> Ok[None] | Err:
    try:
        frame = f"main"
        lginf(frame, f"Setting up dltc-env...", lgr)

        if not os.path.exists(compose_file):
            return handle_error(
                frame, f"The docker-compose file '{compose_file}' does not exist. Please provide a valid file.", lgr, -2
            )

        # 1. Load environment variables
        DOCKER_IMAGE_TAG = f"{v.DOCKERHUB_USERNAME}/dltc-env:latest-{v.ARCH}"

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
            return handle_error(
                frame,
                f"An error occurred while trying to pull the container from DockerHub:\n\t{docker_login_pull_logout_r.stderr}",
                lgr,
                -2,
            )

        # 3. Double check that the image is in fact there
        docker_inspect_cmd = ["docker", "inspect", "--type=image", DOCKER_IMAGE_TAG]
        docker_inspect_r = subprocess.run(docker_inspect_cmd, capture_output=True, text=True)

        if docker_inspect_r.returncode != 0:
            return handle_error(
                frame,
                f"An error occurred while trying to inspect the Docker image '{DOCKER_IMAGE_TAG}':\n\t{docker_inspect_r.stderr}",
                lgr,
                -4,
            )

        # 4. Put down any running containers, then start them again
        lginf(frame, f"Putting down running containers...", lgr)
        docker_down_cmd = ["docker", "compose", "-f", f"{compose_file}", "down"]
        docker_down_r = subprocess.run(docker_down_cmd, capture_output=True, text=True)

        if docker_down_r.returncode != 0:
            return handle_error(
                frame,
                f"An error occurred while trying to stop the running containers:\n\t{docker_down_r.stderr}",
                lgr,
                -5,
            )

        lginf(frame, f"Starting the dltc-env container...", lgr)
        docker_up_cmd = ["docker", "compose", "-f", f"{compose_file}", "up", "-d"]
        docker_up_r = subprocess.run(docker_up_cmd, capture_output=True, text=True)

        if docker_up_r.returncode != 0:
            return handle_error(
                frame,
                f"An error occurred while trying to start the dltc-env container:\n\t{docker_up_r.stderr}",
                lgr,
                -6,
            )

        lginf(frame, f"Success! dltc-env is up and running.", lgr)
        return Ok(out=None)

    except subprocess.CalledProcessError as e:
        return handle_error(
            frame,
            f"An error occurred while running a docker command:\n\t{e.stderr}",
            lgr,
            -1,
        )

    except Exception as e:
        return Err(message=f"An error occurred while trying to setup dltc-env:\n\t{e}", code=-1)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Setup the dltc-env.")

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
