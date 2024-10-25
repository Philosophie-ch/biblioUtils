import csv
from typing import List

from src.sdk.ResultMonad import Err, Ok
from src.sdk.utils import get_logger, remove_extra_whitespace


# Define here the delimiter used to separate nameblocks in the raw_nameblocks column
NAMEBLOCKS_DELIMITER = " and "

lgr = get_logger(__name__)


def raw_nameblock_parser(raw_nameblocks: str) -> List[str]:
    """
    Nameblocks have this structure: "Lastname, Firstname and Lastname2, Firstname2 and Lastname3, Firstname3 ...". The parser splits this string into a list of strings, where each string is a nameblock.
    """
    split = raw_nameblocks.split(NAMEBLOCKS_DELIMITER)
    stripped = [remove_extra_whitespace(name) for name in split]
    return stripped


def nameblock_formatter(nameblock: List[str]) -> str:
    """
    The formatter takes a list of strings and returns a string with the following structure: "Lastname, Firstname and Lastname2, Firstname2 and Lastname3, Firstname3 ...".
    """
    return NAMEBLOCKS_DELIMITER.join(nameblock)


def format_result_column(nameblock: str, not_found: str | None) -> str:
    match not_found:
        case None:
            return f"{nameblock}"
        case _:
            return f"{nameblock}\t{not_found}"


def main(input_file: str, replacement_table_file: str) -> Ok[str] | Err:
    try:
        replacement_table = {}
        with open(replacement_table_file, "r", encoding="utf-16") as f:
            reader = csv.DictReader(f)
            for row in reader:
                replacement_table[row["REPLACE"]] = row["WITH"]

        with open(input_file, "r", encoding="utf-16") as f:
            replaced_nameblocks_buffer = []
            reader = csv.DictReader(f)
            for row in reader:
                raw_nameblocks = row["raw_nameblocks"]
                nameblocks = raw_nameblock_parser(raw_nameblocks)
                replaced_nameblocks = []
                not_found_nameblocks = []
                for nameblock in nameblocks:
                    if nameblock in replacement_table:
                        replaced_nameblocks.append(replacement_table[nameblock])
                    else:
                        lgr.info(f"Nameblock not found in replacement table: {nameblock}")
                        replaced_nameblocks.append(nameblock)
                        not_found_nameblocks.append(nameblock)
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

    parser.add_argument("-i", "--input", type=str, help="Input CSV file", required=True)
    parser.add_argument("-r", "--replacement-table", type=str, help="Replacement table CSV file", required=True)

    args = parser.parse_args()

    result = main(input_file=args.input, replacement_table_file=args.replacement_table)

    cli_presenter(result)
