import os
from src.ref_pipe import gen_md
from src.sdk.utils import handle_unexpected_exception, lginf
from src.sdk.ResultMonad import Err, Ok, runwrap

from src.ref_pipe.setup import dltc_env_up, load_env_vars
from src.ref_pipe.utils import MAINLGR as lgr


def main(input_csv: str, encoding: str, env_file: str, compose_file: str) -> Ok[None] | Err:
    try:
        frame = f"main"

        v = runwrap(load_env_vars(env_file))

        match dltc_env_up(v=v, compose_file=compose_file):
            case Err(message, code):
                return Err(message=message, code=code)

        gen_md_profiles = list(
            runwrap(
                gen_md.main(
                    input_csv=input_csv,
                    encoding=encoding,
                    output_folder=v.REF_PIPE_DIRECTORY,
                )
            )
        )

    except Exception as e:
        return Err(message=f"An error occurred while trying to setup dltc-env:\n\t{e}", code=-1)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Setup the dltc-env.")

    parser.add_argument("-e", "--env_file", type=str, help="Path to the environment file.", required=True)

    parser.add_argument("-c", "--compose_file", type=str, help="Path to the docker-compose file.", required=True)

    parser.add_argument("-i", "--input_csv", type=str, help="Path to the CSV file.")
    parser.add_argument(
        "-e", "--encoding", type=str, help="The encoding of the CSV file. 'utf-8' by default.", default="utf-8"
    )

    args = parser.parse_args()

    main(
        input_csv=args.input_csv,
        encoding=args.encoding,
        env_file=args.env_file,
        compose_file=args.compose_file,
    )
