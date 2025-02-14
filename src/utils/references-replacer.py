from pathlib import Path
from aletk.utils import remove_extra_whitespace, get_logger
from aletk.ResultMonad import main_try_except_wrapper
import csv

from typing import FrozenSet, Tuple
from dataclasses import dataclass


lgr = get_logger("References Replacer")


# Secondary side
def load_content(filename: str) -> str:
    if not Path(filename).exists():
        raise FileNotFoundError(f"The file '{filename}' does not exist.")

    with open(filename, "r") as f:
        content = f.read()

    return content


# Logic
def preprocess_html(html: str) -> str:
    """
    Preprocess html content by removing extra whitespace (new lines, tabs, multiple spaces in a row, etc.), and then adding back newlines after closing div tags.
    """
    return remove_extra_whitespace(html).replace('</div>', '</div>\n')

type TReplacementItem = Tuple[
    str, # original
    str  # replacement
]

type TReplacementTable = Tuple[TReplacementItem, ...]


def load_replacement_table(csv_filename: str, encoding: str) -> TReplacementTable:
    """
    Load a replacement table from a csv file.
    """
    with open(csv_filename, 'r', encoding=encoding) as f:
        reader = csv.DictReader(f)
        return tuple((f"{row['original']}", f"{row['replacement']}") for row in reader)
        

# Composite logic
@dataclass(frozen=True, slots=True)
class TReplaceStringsResult:
    was_changed: bool
    new_html: str
    replacements_used: FrozenSet[str]

def replace_strings(
    html_content: str,
    replacement_table: TReplacementTable,
) -> TReplaceStringsResult:
    """
    Replace strings in an html file according to a replacement table. Re-formats the HTML to be human readable in the process.
    """

    preprocessed_html = preprocess_html(html_content)
    was_changed = False
    replacements_used_l = []

    for original, replacement in replacement_table:
        new_html = preprocessed_html.replace(original, replacement)
        if new_html != preprocessed_html:
            was_changed = True
            preprocessed_html = new_html
            replacements_used_l.append(original)
        
    return TReplaceStringsResult(
        was_changed=was_changed,
        new_html=preprocessed_html,
        replacements_used=frozenset(replacements_used_l)
    )
    

# Primary side
def save_content(filename: str, content: str) -> None:
    with open(filename, "w") as f:
        f.write(content)


# Process
@main_try_except_wrapper(lgr)
def main(
    html_filenames_root_dir: str,
    replacement_table_csv: str,
    encoding: str,
) -> None:

    lgr.info(f"Replacing strings in HTML files in '{html_filenames_root_dir}' according to the replacement table '{replacement_table_csv}'.")

    if not Path(html_filenames_root_dir).exists():
        raise FileNotFoundError(f"The root directory '{html_filenames_root_dir}' does not exist.")

    html_filenames = tuple(
        f"{file}" for file in Path(html_filenames_root_dir).rglob("*.html")
        )
    lgr.info(f"Found {len(html_filenames)} HTML files.")

    lgr.info(f"Loading replacement table from '{replacement_table_csv}'...")
    replacement_table = load_replacement_table(replacement_table_csv, encoding)
    lgr.info(f"Replacement table loaded.")

    lgr.info(f"Starting replacements...")
    for index, html_filename in enumerate(html_filenames):
        lgr.info(f"Processing file {index + 1}/{len(html_filenames)}: '{html_filename}'.")
        html_content = load_content(html_filename)

        result = replace_strings(html_content, replacement_table)

        if result.was_changed:
            save_content(html_filename, result.new_html)
            lgr.info(f"Replacements made in '{html_filename}'.")
        else:
            lgr.info(f"No replacements made in '{html_filename}'.")

    return None


# Front-end
def cli() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Replace strings in HTML files according to a replacement table.")

    parser.add_argument(
        "-d",
        "--html-filenames-root-dir",
        type=str,
        help="The root directory where the HTML files are located.",
        required=True,
    )

    parser.add_argument(
        "-r",
        "--replacement-table-csv",
        type=str,
        help="The CSV file containing the replacement table. Must have columns 'original' and 'replacement'.",
        required=True,
    )

    parser.add_argument(
        "-e",
        "--encoding",
        type=str,
        help="The encoding of the replacement table file.",
        required=True,
    )

    args = parser.parse_args()

    main(
        html_filenames_root_dir = args.html_filenames_root_dir,
        replacement_table_csv = args.replacement_table_csv,
        encoding = args.encoding,
    )


if __name__ == "__main__":
    cli()



