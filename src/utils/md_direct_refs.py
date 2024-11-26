import csv
from pathlib import Path
import polars as pl
import mistune
import re
from typing import Dict, List, Tuple

from src.sdk.ResultMonad import Err, try_except_wrapper
from src.sdk.utils import get_logger, remove_extra_whitespace

lgr = get_logger("Markdown Direct References Finder")


def load_all_bibkeys(bibliography_file: str) -> tuple[str, ...]:

    path = Path(bibliography_file)
    if not path.exists():
        raise FileNotFoundError("The bibliography file does not exist.")

    extension = path.suffix

    match extension:
        case ".ods":
            df = pl.read_ods(bibliography_file, has_header=True, drop_empty_rows=True)
            bibkeys_l = df['bibkey'].to_list()
            bibkeys = tuple(remove_extra_whitespace(f"{bibkey}") for bibkey in bibkeys_l)

        case _:
            raise ValueError(f"Format '{extension}' not supported. Only ODS files are supported.")

    return bibkeys


def read_file(file_path: Path) -> str:
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    return content


def remove_yaml_front_matter(content: str) -> str:
    if content.startswith('---'):
        # Split YAML front matter from the rest of the content
        yaml_delimiter = content.find('\n---', 3)  # Look for the closing '---'
        if yaml_delimiter != -1:
            return content[yaml_delimiter + 3 :].lstrip()  # Strip YAML block
        elif yaml_delimiter := content.find('\n...', 3):
            if yaml_delimiter != -1:
                return content[yaml_delimiter + 3 :].lstrip()
    return content


def get_text_bits(md_content: str, parser: mistune.Markdown) -> tuple[str]:

    tokens = parser.parse(md_content)

    children_nested = (token.get('children') for token in tokens[0] if token.get('children') is not None)

    children = (item for sublist in children_nested for item in sublist)

    text_bits = tuple(c.get('raw') for c in children if c.get('raw') is not None)

    return text_bits


def get_citations(text_bits: tuple[str], citation_pattern: re.Pattern[str]) -> set[str]:
    citations: List[str] = []

    # Iterate through tokens to find citations in text content
    for t in text_bits:
        matches = citation_pattern.findall(t)
        for match in matches:
            citations.append(f"{match[1]}")

    return set(citations)


def is_non_key(k: str) -> bool:
    no_colon = not ":" in k
    is_section = k.lower().startswith("sec:") or "-sec:" in k
    is_definition = k.lower().startswith("def:")
    is_figure = k.lower().startswith("fig:")
    is_lemma = k.lower().startswith("lem:")
    is_theorem = k.lower().startswith("thm:") or "-thm:" in k.lower()
    is_equation = k.lower().startswith("eq:")
    is_statement = k.lower().startswith("sta:")
    is_table = k.lower().startswith("tbl:")
    is_rem = k.lower().startswith("rem:")
    is_proposition = k.lower().startswith("prop:")

    return any(
        (
            no_colon,
            is_section,
            is_definition,
            is_figure,
            is_lemma,
            is_theorem,
            is_equation,
            is_statement,
            is_table,
            is_rem,
            is_proposition,
        )
    )


def key_cleaner(k: str) -> str:
    key = k

    # Remove trailing whitespace
    key = remove_extra_whitespace(key)

    # Remove triple dashes and anything that comes after them, if any
    if "---" in key:
        key = key[: key.find("---")]

    # Remove double dashes and anything that comes after them, if any
    if "--" in key:
        key = key[: key.find("--")]

    # Remove trailing dots, if any
    if key.endswith("."):
        key = key[:-1]

    # Remove trailing colons, if any
    if key.endswith(":"):
        key = key[:-1]

    # Remove colons at the beginning of the key, if any
    if key.startswith(":"):
        key = key[1:]

    return key


def get_keys(citations: set[str]) -> tuple[set[str], set[str]]:

    non_keys = {n for n in citations if is_non_key(n)}

    apparent_keys = citations - non_keys

    cleaned_apparent_keys = {key_cleaner(k) for k in apparent_keys}

    return non_keys, cleaned_apparent_keys


def biblio_keys(keys: set[str], all_bibkeys: tuple[str, ...]) -> tuple[set[str], set[str]]:

    bibkeys = {bk for bk in keys if bk in all_bibkeys}

    non_bibkeys = keys - bibkeys

    return bibkeys, non_bibkeys


type TSegregatedKeys = Tuple[
    set[str],  # Direct references
    set[str],  # Bibkeys not in bibfile
    set[str],  # Non-bibkeys
]


def get_segregated_keys(
    all_bibkeys: tuple[str, ...],
    md_content: str,
) -> TSegregatedKeys:

    md_content_pruned = remove_yaml_front_matter(md_content)

    parser = mistune.create_markdown(renderer="ast")

    text_bits = get_text_bits(md_content_pruned, parser)

    citation_pattern = re.compile(
        # Matches this structure: [-]@{bibkey}[pp. 1-2, sec. 3, chap. 4]
        r'(?<!\w)\[?([-]?)@{?([a-zA-Z0-9_.:$/%&+?<>~#-]+)}?(?:,?\s*(pp?\.\s[^\];]+|sec\.\s[^\];]+|chap\.\s[^\];]+)?)?(?:,\s*([^\];]+))?\]?'
    )

    citations = get_citations(text_bits, citation_pattern)
    non_keys, apparent_keys = get_keys(citations)
    direct_refs, non_biblio_bibkeys = biblio_keys(apparent_keys, all_bibkeys)

    return direct_refs, non_biblio_bibkeys, non_keys


type TResultDict = Dict[
    str,
    TSegregatedKeys,
]


def validate_output_path(output_file: str) -> Path:
    path = Path(output_file)
    if not path.exists():
        raise FileNotFoundError("The output file does not exist.")

    extension = path.suffix
    if extension != ".csv":
        raise ValueError(f"Format '{extension}' not supported. Only CSV files are supported.")
    return path


def write_output_csv(
    output_path: Path,
    result_dict: TResultDict,
) -> None:

    with open(output_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["bibkey", "direct_references", "bibkey_not_in_bibfile", "non_bibkey"])

        writer.writeheader()
        writer.writerows(
            {
                "bibkey": bibkey,
                "direct_references": ", ".join(direct_refs),
                "bibkey_not_in_bibfile": ", ".join(bibkey_not_in_bibfile),
                "non_bibkey": ", ".join(non_bibkey),
            }
            for bibkey, (direct_refs, bibkey_not_in_bibfile, non_bibkey) in result_dict.items()
        )

    return None


def gen_dltc_filename(path: Path) -> str:
    stem = path.stem
    stripped = remove_extra_whitespace(stem)

    # Replace the last occurrence of "-" with ":"
    last_hyphen = stripped.rfind("-")

    if last_hyphen != -1:
        return f"{stripped[:last_hyphen]}:{stripped[last_hyphen + 1:]}"
    else:
        return stripped


@try_except_wrapper(lgr)
def main(bibliography_file: str, root_dir: str, output_file: str) -> None:

    root_path = Path(root_dir)
    if not root_path.exists():
        raise FileNotFoundError("The root directory does not exist.")

    output_path = validate_output_path(output_file)

    lgr.info(f"Loading bibkeys from '{bibliography_file}'...")
    all_bibkeys = load_all_bibkeys(bibliography_file)
    lgr.info(f"Loaded {len(all_bibkeys)} bibkeys.")

    lgr.info(f"Looking for markdown files in '{root_dir}'...")
    all_markdown_files = list(root_path.rglob("*.md"))
    lgr.info(f"Found {len(all_markdown_files)} markdown files.")
    # lgr.info(
    # f"Printing up to the first 10 markdown files: {tuple(zip(
    # tuple(f.name for f in all_markdown_files[:10]),
    # tuple(f.stem for f in all_markdown_files[:10]),
    # ))}"
    # )
    markdown_files = [f for f in all_markdown_files if gen_dltc_filename(f) in all_bibkeys]
    lgr.info(f"Found {len(markdown_files)} markdown articles.")
    # lgr.info(f"Printing the markdown files found: {tuple(f.stem for f in markdown_files)}")

    if len(markdown_files) == 0:
        raise ValueError("No markdown files found.")

    if len(set(markdown_files)) != len(markdown_files):
        raise ValueError("Duplicate markdown files found.")

    lgr.info(f"Processing {len(markdown_files)} markdown files...")
    result_dict: TResultDict = {f"{f.stem}": get_segregated_keys(all_bibkeys, read_file(f)) for f in markdown_files}

    lgr.info(f"Writing output to '{output_file}'...")
    write_output_csv(output_path, result_dict)

    lgr.info("Success! All articles processed.")

    return None


def cli() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Find direct references in markdown files.")

    parser.add_argument(
        "-b",
        "--bibliography-file",
        type=str,
        help="The bibliography file in ODS format.",
        required=True,
    )

    parser.add_argument(
        "-r",
        "--root-dir",
        type=str,
        help="The root directory where the markdown files are located.",
        required=True,
    )

    parser.add_argument(
        "-o",
        "--output-file",
        type=str,
        help="The output file in CSV format.",
        required=True,
    )

    args = parser.parse_args()

    result = main(args.bibliography_file, args.root_dir, args.output_file)

    if isinstance(result, Err):
        lgr.error("An error occured. Please check the logs for more information.")

    return None


if __name__ == "__main__":
    cli()
