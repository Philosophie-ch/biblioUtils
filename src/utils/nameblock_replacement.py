import csv
from pathlib import Path
import traceback
from typing import List
import polars as pl

from aletk.ResultMonad import Err, Ok
from aletk.utils import get_logger, remove_extra_whitespace


# Define here the delimiter used to separate nameblocks in the raw_nameblocks column
RAW_NAMEBLOCKS_DELIMITER = ""  # Leave empty to not split the raw nameblocks
PROCESSED_NAMEBLOCKS_DELIMITER = ""

lgr = get_logger(__name__)


def raw_nameblock_parser(raw_nameblocks: str) -> List[str]:
    """
    Nameblocks have this structure: "Lastname, Firstname and Lastname2, Firstname2 and Lastname3, Firstname3 ...". The parser splits this string into a list of strings, where each string is a nameblock.
    """
    split = raw_nameblocks.split(RAW_NAMEBLOCKS_DELIMITER) if RAW_NAMEBLOCKS_DELIMITER else [raw_nameblocks]
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
                reader = csv.reader(f, delimiter="\t")

                replacement_table = {f"{row[0]}": f"{row[1]}" for row in reader if len(row) >= 2}

                if not replacement_table:
                    raise ValueError(
                        f"The replacement table '{replacement_table_file}' is empty or does not contain the required columns. Expected at least two columns. Excerpt from the file: {list(csv.reader(f))[:5]}"
                    )

        case ".ods":
            df = pl.read_ods(replacement_table_file, has_header=False, drop_empty_rows=True)

            replacement_table = {f"{row[0]}": f"{row[1]}" for row in df.iter_rows()}

            if not replacement_table:
                raise ValueError(
                    f"The replacement table '{replacement_table_file}' is empty or does not contain the required columns. Expected at least two columns. Excerpt from the file: {df.head(5)}"
                )

        case _:
            raise ValueError("The replacement table must be a CSV or ODS file.")

    return replacement_table


def read_raw_nameblocks(input_file: str, column_name: str, encoding: str) -> List[str]:

    path = Path(input_file)

    if not path.exists():
        raise FileNotFoundError("The input file does not exist.")

    extension = path.suffix
    excerpt = ""

    match extension:
        case ".txt":
            with open(input_file, "r", encoding=encoding) as f:
                raw_nameblocks = [line.strip() for line in f.readlines()]
                excerpt = str(raw_nameblocks[:5])

        case ".csv":
            if not column_name:
                raise ValueError("Column name must be specified for CSV files.")
            with open(input_file, "r", encoding=encoding) as f:
                reader = csv.DictReader(f, delimiter="\t")
                excerpt = str(list(csv.reader(f))[5])
                lgr.info(f"Reading column '{column_name}' from CSV file")
                raw_nameblocks = [f"{row[column_name]}" for row in reader]
                lgr.info(f"Found {len(raw_nameblocks)} raw nameblocks in the CSV file")
                lgr.info(f"Example raw nameblock: {raw_nameblocks[0] if raw_nameblocks else 'None'}")

        case ".ods":
            if not column_name:
                raise ValueError("Column name must be specified for ODS files.")
            df = pl.read_ods(input_file, has_header=True, drop_empty_rows=True, schema_overrides={column_name: pl.Utf8})
            excerpt = str(f"{df[column_name].drop_nulls().head(5)}")
            raw_nameblocks = [f"{row}" for row in df[column_name].to_list()]

        case _:
            raise ValueError("The input file must be a CSV or ODS file.")

    if [nb for nb in raw_nameblocks if (nb and nb != "None" and nb != "")] == []:
        raise ValueError(
            f"The input file '{input_file}' (params: column_name={column_name}, encoding={encoding}) is empty or does not contain the required column. Please ensure the file exists and the column name is correct. Excerpt from the file: {excerpt}"
        )

    return raw_nameblocks


def main(
    input_file: str, replacement_table_file: str, column_name: str, encoding1: str, encoding2: str
) -> Ok[str] | Err:
    try:
        lgr.info(f"Reading replacement table from {replacement_table_file}")
        replacement_table = read_replacement_table(replacement_table_file, encoding2)

        lgr.info(
            f"Replacement table loaded with {len(replacement_table)} entries. Example entry: {list(replacement_table.items())[0]}"
        )

        lgr.info(f"Reading raw nameblocks from {input_file}")
        replaced_nameblocks_buffer = []
        lgr.info(f"Input file: {input_file}, Column name: {column_name}, Encoding: {encoding1}")

        lgr.info(f"Reading raw nameblocks from {input_file}")
        raw_nameblocks_list = read_raw_nameblocks(input_file, column_name, encoding1)
        lgr.info(f"Found {len(raw_nameblocks_list)} raw nameblocks")
        lgr.info(
            f"Example raw nameblock: {next(rnb for rnb in raw_nameblocks_list if rnb and rnb != "None") if raw_nameblocks_list else 'None'}"
        )

        lgr.info(f"Replacing nameblocks")
        count = 0
        for raw_nameblocks in raw_nameblocks_list:
            count += 1
            nameblocks = raw_nameblock_parser(raw_nameblocks)
            lgr.info(f"Processing raw nameblocks: {nameblocks}") if count % 10000 == 0 else None
            replaced_nameblocks = []
            not_found_nameblocks = []
            for nameblock in nameblocks:
                if nameblock in replacement_table:
                    replaced_nameblocks.append(replacement_table[nameblock])
                else:
                    if nameblock is not None and nameblock != "None":
                        # lgr.warning(f"Nameblock not found in replacement table: {nameblock}")
                        replaced_nameblocks.append(nameblock)
                        not_found_nameblocks.append(nameblock)
                    else:
                        replaced_nameblocks.append("")
                        not_found_nameblocks.append("")

            raw_nameblocks_replaced = nameblock_formatter(replaced_nameblocks)
            replaced_nameblocks_buffer.append(f"{raw_nameblocks_replaced}\t{' -- '.join(not_found_nameblocks)}")

        lgr.info(f"Formatting result")
        result = "\n".join(replaced_nameblocks_buffer)

        lgr.info(f"Done")
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
        description="Replace nameblocks in a CSV file with a replacement table, and prints the result to stdout. Example usage: python nameblock_replacement.py -i input.csv -r replacement_table.csv -c raw_nameblocks -e1 utf-8 -e2 utf-8"
    )

    parser.add_argument(
        "-i",
        "--input",
        type=str,
        help="Input CSV, ODS, or TXT file.",
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
        help="The name of the column in the input CSV or ODS file that contains the raw nameblocks you want to replace.",
    )
    parser.add_argument("-e1", "--encoding1", type=str, help="The encoding of the input file.", default='utf-8')
    parser.add_argument(
        "-e2", "--encoding2", type=str, help="The encoding of the replacement table file.", default='utf-8'
    )

    args = parser.parse_args()

    cli_presenter(
        main(
            input_file=args.input,
            replacement_table_file=args.replacement_table,
            column_name=args.column_name,
            encoding1=args.encoding1,
            encoding2=args.encoding2,
        )
    )
