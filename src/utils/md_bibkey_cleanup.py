"""
Read from a file containing a map of old_bibkey -> new_bibkey, and use it to replace in bulk any occurrence of old_bibkey in every markdown file present in any subdirectory of the root directory.

Divided by different functions, the script is as follows:
- `load_bibkey_map` reads the file containing the map of old_bibkey -> new_bibkey. Uses polars to read from a ODS file.
- `replace_bibkeys` gets a map as input, and replaces the old_bibkey with the new_bibkey in all markdown files present in the root directory and its subdirectories.
- `main` is the entry point of the script, and it calls the other functions.
- `cli` is the command-line interface of the script, and it parses the arguments and calls the `main` function. Inside this function we import argparse and define the arguments that the script will receive:
    + `-r` or `--root-dir` is the root directory where the markdown files are located.
    + `-m` or `--map-file` is the file containing the map of old_bibkey -> new_bibkey. Supported format: ODS only.
"""

from pathlib import Path
import polars as pl

from src.sdk.ResultMonad import Err, Ok, try_except_wrapper
from src.sdk.utils import get_logger

lgr = get_logger("Dialectica Markdown Bibkey Replacement")


def load_bibkey_map(map_file: str) -> dict[str, str]:

    path = Path(map_file)
    if not path.exists():
        raise FileNotFoundError("The map file does not exist.")

    extension = path.suffix

    match extension:
        case ".ods":
            df = pl.read_ods(map_file, has_header=True, drop_empty_rows=True)
            old_bibkeys = df['old_bibkey'].to_list()
            new_bibkeys = df['new_bibkey'].to_list()
            result = {old: new for old, new in zip(old_bibkeys, new_bibkeys)}

        case _:
            raise ValueError(f"Format '{extension}' not supported. Only ODS files are supported.")

    return result


def replace_bibkeys(root_dir: str, bibkey_map: dict[str, str]) -> Ok[None]:
    root_path = Path(root_dir)
    if not root_path.exists():
        raise FileNotFoundError("The root directory does not exist.")

    markdown_files = root_path.rglob("*.md")

    for file in markdown_files:
        with open(file, "r") as f:
            old_content = f.read()

        new_content = old_content
        for old_bibkey, new_bibkey in bibkey_map.items():
            new_content = new_content.replace(old_bibkey, new_bibkey)

        with open(file, "w") as f:
            f.write(new_content)

        if old_content != new_content:
            lgr.warning(f"Replacement was made in file '{file}'")

    return Ok(out=None)


@try_except_wrapper(lgr)
def main(root_dir: str, map_file: str) -> None:

    result = replace_bibkeys(root_dir, load_bibkey_map(map_file))

    if isinstance(result, Err):
        raise Exception(result.message)

    lgr.info("Success! All bibkeys replaced.")

    return None


def cli() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Replace old bibkeys with new bibkeys in markdown files")

    parser.add_argument(
        "-r",
        "--root-dir",
        type=str,
        help="The root directory where the markdown files are located.",
        required=True,
    )

    parser.add_argument(
        "-m",
        "--map-file",
        type=str,
        help="The file containing the map of old_bibkey -> new_bibkey. Supported format: ODS only.",
        required=True,
    )

    args = parser.parse_args()

    main(args.root_dir, args.map_file)

    return None


if __name__ == "__main__":
    cli()
