import csv
from pathlib import Path
from typing import List
import polars as pl

from src.sdk.ResultMonad import Err, Ok
from src.sdk.utils import get_logger, remove_extra_whitespace


# Define here the delimiter used to separate nameblocks in the raw_nameblocks column
RAW_NAMEBLOCKS_DELIMITER = " and "
PROCESSED_NAMEBLOCKS_DELIMITER = ", "

lgr = get_logger(__name__)


def raw_nameblock_parser(raw_nameblocks: str) -> List[str]:
    """
    Nameblocks have this structure: "Lastname, Firstname and Lastname2, Firstname2 and Lastname3, Firstname3 ...". The parser splits this string into a list of strings, where each string is a nameblock.
    """
    split = raw_nameblocks.split(RAW_NAMEBLOCKS_DELIMITER)
    stripped = [remove_extra_whitespace(name) for name in split]
    return stripped


def nameblock_formatter(nameblock: List[str]) -> str:
    """
    The formatter takes a list of strings and returns a string with the following structure: "Lastname, Firstname and Lastname2, Firstname2 and Lastname3, Firstname3 ...".
    """
    return PROCESSED_NAMEBLOCKS_DELIMITER.join(nameblock)


def format_result_column(nameblock: str, not_found: str | None) -> str:
    match not_found:
        case None:
            return f"{nameblock}"
        case _:
            return f"{nameblock}\t{not_found}"


def read_replacement_table(replacement_table_file: str, encoding: str) -> dict[str, str]:

    path = Path(replacement_table_file)

    if not path.exists():
        raise FileNotFoundError("The input file does not exist.")

    extension = path.suffix

    match extension:

        case ".csv":
            with open(replacement_table_file, "r", encoding=encoding) as f:
                reader = csv.DictReader(f)
                replacement_table = {f"{row[0]}": f"{row[1]}" for row in reader}

        case ".ods":
            df = pl.read_ods(replacement_table_file, has_header=False, drop_empty_rows=True)

            replacement_table = {f"{row[0]}": f"{row[1]}" for row in df.iter_rows()}

        case _:
            raise ValueError("The replacement table must be a CSV or ODS file.")

    return replacement_table


def read_raw_nameblocks(input_file: str, column_name: str, encoding: str) -> List[str]:

    path = Path(input_file)

    if not path.exists():
        raise FileNotFoundError("The input file does not exist.")

    extension = path.suffix

    match extension:
        case ".csv":
            with open(input_file, "r", encoding=encoding) as f:
                reader = csv.DictReader(f)
                raw_nameblocks = [f"{row[column_name]}" for row in reader]

        case ".ods":
            df = pl.read_ods(input_file, has_header=True, drop_empty_rows=True)
            raw_nameblocks = [f"{row}" for row in df[column_name].to_list()]

        case _:
            raise ValueError("The input file must be a CSV or ODS file.")

    return raw_nameblocks


def main(input_file: str, replacement_table_file: str, column_name: str, encoding: str) -> Ok[str] | Err:
    try:
        replacement_table = read_replacement_table(replacement_table_file, encoding)

        replaced_nameblocks_buffer = []

        raw_nameblocks_list = read_raw_nameblocks(input_file, column_name, encoding)

        for raw_nameblocks in raw_nameblocks_list:
            nameblocks = raw_nameblock_parser(raw_nameblocks)
            replaced_nameblocks = []
            not_found_nameblocks = []
            for nameblock in nameblocks:
                if nameblock in replacement_table:
                    replaced_nameblocks.append(replacement_table[nameblock])
                else:
                    if nameblock is not None and nameblock != "None":
                        lgr.info(f"Nameblock not found in replacement table: {nameblock}")
                        replaced_nameblocks.append(nameblock)
                        not_found_nameblocks.append(nameblock)
                    else:
                        replaced_nameblocks.append("")
                        not_found_nameblocks.append("")


            raw_nameblocks_replaced = nameblock_formatter(replaced_nameblocks)
            replaced_nameblocks_buffer.append(f"{raw_nameblocks_replaced}\t{' -- '.join(not_found_nameblocks)}")

        result = "\n".join(replaced_nameblocks_buffer)

        return Ok(out=result)

    except Exception as e:
        return Err(message=f"Unexpected error: {e}", code=-1)


def cli_presenter(result: Ok[str] | Err) -> None:

    match result:

        case Ok(out=out):
            print(out)

        case Err(message=message, code=code):
            print(message)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Replace nameblocks in a CSV file with a replacement table")

    parser.add_argument(
        "-i",
        "--input",
        type=str,
        help="Input CSV file. Must have a column 'raw_nameblocks' with the nameblocks to be replaced.",
        required=True,
    )
    parser.add_argument(
        "-r",
        "--replacement-table",
        type=str,
        help="Replacement table file. Must be a CSV or ODS, in which the first column is the nameblock to be replaced and the second column is the replacement.",
        required=True,
    )
    parser.add_argument(
        "-c",
        "--column-name",
        type=str,
        help="The name of the column in the CSV or ODS file that contains the raw nameblocks you want to replace.",
        required=True,
    )
    parser.add_argument("-e", "--encoding", type=str, help="The encoding of the CSV file.", required=True)

    args = parser.parse_args()

    cli_presenter(
        main(
            input_file=args.input,
            replacement_table_file=args.replacement_table,
            column_name=args.column_name,
            encoding=args.encoding,
        )
    )
