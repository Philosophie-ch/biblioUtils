from pathlib import Path
from aletk.utils import get_logger, lginf, pretty_format_frozenset
from aletk.ResultMonad import Err, Ok, main_try_except_wrapper
from typing import Dict, FrozenSet, Generator, Tuple
import polars as pl
from pypdf import PdfWriter

import os

file_basename = os.path.basename(__file__)

lgr = get_logger(file_basename)

import logging

# Silence pypdf internal AssertionError('mypy') warnings
logging.getLogger("pypdf.generic._data_structures").setLevel(logging.ERROR)


type TVolNum = Tuple[int, str]

type TEntryTup = Tuple[str, Tuple[int, ...]]  # issue_name, pub_ids
type TEntryGen = Generator[TEntryTup, None, None]
type TPubIds = FrozenSet[str]
type TIssueNames = FrozenSet[str]


def load_entry_data(input_file: str) -> Tuple[TEntryGen, TPubIds, TIssueNames]:

    df = pl.read_ods(input_file, has_header=True, drop_empty_rows=True)

    # Ensure the required columns are present
    required_columns = {"original_order", "volume", "number", "pub_id", "issue_name"}
    missing = {col for col in required_columns if col not in df.columns}
    if missing:
        raise ValueError(
            f"The input file must contain the following columns: {', '.join(required_columns)}. Missing columns: {', '.join(missing)}"
        )

    # Keep only rows that have either pub_id or issue_name
    df = df.filter(pl.col("pub_id").is_not_null() | pl.col("issue_name").is_not_null())

    # Merge issue_name onto pub rows by (volume, number)
    # Clean issue_name in df_issue
    df_issue = (
        df.filter(pl.col("issue_name").is_not_null())
        .select(["volume", "number", "issue_name"])
        .with_columns(
            pl.col("issue_name")
            .cast(pl.Utf8)  # ensure it's a string
            .str.replace_all(r"\s+", " ")  # collapse whitespace
            .str.strip_chars()  # remove leading/trailing whitespace
        )
    )

    # Clean pub_id in df_pub
    df_pub = (
        df.filter(pl.col("pub_id").is_not_null())
        .select(["volume", "number", "pub_id"])
        .with_columns(pl.col("pub_id").cast(pl.Utf8).str.replace_all(r"\s+", " ").str.strip_chars())
    )

    # Join pub rows with issue_name via (volume, number)
    df_joined = df_pub.join(df_issue, on=["volume", "number"], how="inner")

    # Group by issue_name and collect pub_ids as lists
    df_grouped = df_joined.group_by("issue_name").agg(pl.col("pub_id").unique().alias("pub_ids"))

    # Frozenset of all issue names
    all_issue_names = frozenset(df_grouped["issue_name"].unique().to_list())
    # Frozenset of all pub_ids
    all_pub_ids = frozenset(f"{pub_id}" for pub_id in df_pub["pub_id"].unique())

    # Convert grouped data to generator of tuples (issue_name, set_of_pub_ids)
    entry_gen = (
        (str(row["issue_name"]), tuple(sorted(set(int(pub_id) for pub_id in row["pub_ids"]))))
        for row in df_grouped.iter_rows(named=True)
    )

    return entry_gen, all_pub_ids, all_issue_names


type TFileIndex = Dict[str, str]


def index_files(target_dir: str, extension: str) -> TFileIndex:
    """
    Indexes files in the target directory with the given extension.
    Returns a dictionary where the keys are the file names without extension and the values are the full paths.
    """
    index = {p.stem: str(p) for p in Path(target_dir).rglob(f"*{extension}")}
    lgr.info(f"Indexed {len(index)} files with extension '{extension}' in directory '{target_dir}'")
    return index


def check_pub_ids_have_file(
    pub_ids: TPubIds,
    file_index: TFileIndex,
) -> None | FrozenSet[str]:
    """
    Asserts that the pub_id has a corresponding PDF file in the pdfs_index.
    Raises an AssertionError if the pub_id is not found in the pdfs_index.
    """
    not_found = frozenset(pub_id for pub_id in pub_ids if pub_id not in file_index)

    if len(not_found) > 0:
        res = pretty_format_frozenset(not_found)
        lgr.warning(f"Found {len(not_found)} pub_ids that do not have a corresponding PDF file.")

    else:
        lgr.info(f"All {len(pub_ids)} pub_ids have a corresponding PDF file.")

    return not_found


def merge_pdfs(
    entry_gen: TEntryGen,
    pdfs_index: TFileIndex,
    output_path: str,
) -> None:
    """
    Merges PDFs for each issue_name into a single PDF file.
    The output file is named as 'issue_name' and saved in the output_dir.
    """

    output_dir = Path(output_path)
    output_dir.mkdir(parents=True, exist_ok=True)

    count = 0
    for issue_name, pub_ids in entry_gen:
        output_file = output_dir / f"{issue_name}"
        with PdfWriter() as merger:
            for pub_id in pub_ids:
                merger.append(pdfs_index[str(pub_id)])
            merger.write(str(output_file))

        lgr.debug(f"Saved merged PDF for issue '{issue_name}' to '{output_file}'")

        if count % 30 == 0:
            lgr.info(f"Merged {count} issues so far. Last issue: '{issue_name}'")

        count += 1


@main_try_except_wrapper(lgr)
def main(
    dataset_path: str,
    pdfs_dir: str,
    output_dir: str,
) -> None:
    """
    Main function to load entry data, index files, check pub_ids, and merge PDFs.
    """
    frame = "main"

    lginf(frame, "Starting the PDF merging process", lgr)

    entry_gen, pub_ids, issue_names = load_entry_data(dataset_path)
    lginf(frame, f"Loaded {len(pub_ids)} pub_ids and {len(issue_names)} issue names from the dataset", lgr)

    pdfs_index = index_files(pdfs_dir, ".pdf")
    lginf(frame, f"Indexed {len(pdfs_index)} PDF files in '{pdfs_dir}'", lgr)

    file_check = check_pub_ids_have_file(pub_ids, pdfs_index)
    if file_check:
        raise AssertionError(
            f"Some pub_ids do not have a corresponding PDF file: {pretty_format_frozenset(file_check)}"
        )

    lginf(frame, "Merging PDFs for each issue_name", lgr)
    merge_pdfs(entry_gen, pdfs_index, output_dir)


def cli() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Merge PDFs based on issue names from a dataset.")

    parser.add_argument(
        "-d",
        "--dataset-path",
        type=str,
        help="Path to the dataset file (ODS format) containing issue names and pub_ids.",
        required=True,
    )

    parser.add_argument(
        "-p",
        "--pdfs-dir",
        type=str,
        help="Directory containing the PDF files to be merged.",
        required=True,
    )

    parser.add_argument(
        "-o",
        "--output-dir",
        type=str,
        help="Directory where the merged PDF files will be saved.",
        required=True,
    )

    args = parser.parse_args()

    res = main(args.dataset_path, args.pdfs_dir, args.output_dir)

    if isinstance(res, Err):
        lgr.error(f"An error occurred: {res.message}\nFull context: {res}")
    else:
        lgr.info("PDF merging completed successfully.")


if __name__ == "__main__":
    cli()
