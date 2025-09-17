import shutil
import traceback
from pathlib import Path
from typing import List, Dict
import polars as pl

from aletk.ResultMonad import Err, Ok
from aletk.utils import get_logger


lgr = get_logger(__name__)


def read_mapping_file(mapping_file: str, encoding: str) -> List[Dict[str, str]]:
    """
    Read the ODS file containing the mapping between jstor_id and filename.
    Expected columns: id, a, bibkey, jstor_id, filename
    """
    path = Path(mapping_file)

    if not path.exists():
        raise FileNotFoundError(f"The mapping file '{mapping_file}' does not exist.")

    if path.suffix != ".ods":
        raise ValueError("The mapping file must be an ODS file.")

    lgr.info(f"Reading mapping file: {mapping_file}")

    # Read ODS file with headers
    df = pl.read_ods(
        mapping_file,
        has_header=True,
        drop_empty_rows=True,
        schema_overrides={"id": pl.Utf8, "a": pl.Utf8, "bibkey": pl.Utf8, "jstor_id": pl.Utf8, "filename": pl.Utf8},
    )

    # Check required columns exist
    required_columns = ("jstor_id", "filename")
    missing_columns = tuple(col for col in required_columns if col not in df.columns)

    if missing_columns:
        raise ValueError(
            f"The mapping file is missing required columns: {missing_columns}. " f"Available columns: {df.columns}"
        )

    # Convert to list of dictionaries, only keeping non-null entries
    mappings = []
    for row in df.iter_rows(named=True):
        if row["jstor_id"] and row["filename"] and str(row["jstor_id"]) != "None" and str(row["filename"]) != "None":
            mappings.append({"jstor_id": str(row["jstor_id"]), "filename": str(row["filename"])})

    lgr.info(f"Loaded {len(mappings)} valid mappings from the file")

    if not mappings:
        raise ValueError(
            f"No valid mappings found in '{mapping_file}'. "
            f"Ensure jstor_id and filename columns contain data. "
            f"First 5 rows: {df.head(5)}"
        )

    return mappings


def find_file_recursive(directory: Path, filename: str) -> Path | None:
    """
    Search for a file recursively in the given directory.
    Returns the first matching file path or None if not found.
    """
    for file_path in directory.rglob(filename):
        if file_path.is_file():
            return file_path
    return None


def process_file_renaming(
    mappings: List[Dict[str, str]], input_directory: Path, output_directory: Path
) -> tuple[int, int, List[str]]:
    """
    Process the file renaming based on the mappings.
    Returns: (successful_count, failed_count, list of errors)
    """
    successful = 0
    failed = 0
    errors = []

    # Create output directory if it doesn't exist
    output_directory.mkdir(parents=True, exist_ok=True)

    for idx, mapping in enumerate(mappings, 1):
        jstor_id = mapping["jstor_id"]
        new_filename = mapping["filename"]
        source_filename = f"{jstor_id}.pdf"

        if idx % 100 == 0:
            lgr.info(f"Processing entry {idx}/{len(mappings)}")

        # Search for the source file
        source_path = find_file_recursive(input_directory, source_filename)

        if source_path:
            destination_path = output_directory / new_filename

            try:
                # Copy the file with new name
                shutil.copy2(source_path, destination_path)
                lgr.debug(f"Copied: {source_path} -> {destination_path}")
                successful += 1

            except Exception as e:
                error_msg = f"Failed to copy {source_filename} to {new_filename}: {e}"
                lgr.warning(error_msg)
                errors.append(error_msg)
                failed += 1
        else:
            error_msg = f"File not found: {source_filename} (for rename to {new_filename})"
            lgr.debug(error_msg)
            errors.append(error_msg)
            failed += 1

    return successful, failed, errors


def main(mapping_file: str, input_directory: str, output_directory: str, encoding: str) -> Ok[str] | Err:
    try:
        lgr.info(f"Starting file renaming process")
        lgr.info(f"Mapping file: {mapping_file}")
        lgr.info(f"Input directory: {input_directory}")
        lgr.info(f"Output directory: {output_directory}")

        # Convert paths
        input_dir_path = Path(input_directory)
        output_dir_path = Path(output_directory)

        # Validate input directory
        if not input_dir_path.exists():
            raise FileNotFoundError(f"Input directory does not exist: {input_directory}")

        if not input_dir_path.is_dir():
            raise ValueError(f"Input path is not a directory: {input_directory}")

        # Read mappings
        mappings = read_mapping_file(mapping_file, encoding)

        lgr.info(f"Processing {len(mappings)} file mappings")

        # Process the renaming
        successful, failed, errors = process_file_renaming(mappings, input_dir_path, output_dir_path)

        # Prepare result summary
        result_lines = [
            f"File renaming completed:",
            f"  Successful: {successful}",
            f"  Failed: {failed}",
            f"  Total processed: {successful + failed}",
        ]

        if errors and len(errors) <= 20:
            result_lines.append("\nErrors encountered:")
            for error in errors:
                result_lines.append(f"  - {error}")
        elif errors:
            result_lines.append(f"\n{len(errors)} errors encountered:")
            for error in errors:
                result_lines.append(f"  - {error}")

        result = "\n".join(result_lines)

        lgr.info(f"Done. Successful: {successful}, Failed: {failed}")

        return Ok(out=result)

    except Exception as e:
        return Err(
            message=f"Unexpected error: {e}",
            code=-1,
            error_type=f"{e.__class__.__name__}",
            error_trace=f"{traceback.format_exc()}",
        )


def cli_presenter(result: Ok[str] | Err) -> None:

    match result:

        case Ok(out=out):
            print(out)

        case Err():
            lgr.error(
                f"An unexpected error occurred:\n\n"
                f"\tmessage: {result.message}\n"
                + f"\tcode: {result.code}\n"
                + f"\terror_type: {result.error_type}\n\n"
                + f"\t=> Error_trace: {result.error_trace}\n"
            )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Rename PDF files based on an ODS mapping file. "
        "Example usage: python file_rename.py -m mapping.ods -i /path/to/input -o /path/to/output -e utf-8"
    )

    parser.add_argument(
        "-m",
        "--mapping-file",
        type=str,
        help="ODS file containing the mapping between jstor_id and filename. "
        "Expected columns: id, a, bibkey, jstor_id, filename",
        required=True,
    )
    parser.add_argument(
        "-i",
        "--input-directory",
        type=str,
        help="Input directory to search for PDF files recursively",
        required=True,
    )
    parser.add_argument(
        "-o",
        "--output-directory",
        type=str,
        help="Output directory where renamed files will be copied",
        required=True,
    )
    parser.add_argument("-e", "--encoding", type=str, help="The encoding of the mapping file.", default='utf-8')

    args = parser.parse_args()

    cli_presenter(
        main(
            mapping_file=args.mapping_file,
            input_directory=args.input_directory,
            output_directory=args.output_directory,
            encoding=args.encoding,
        )
    )
