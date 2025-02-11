"""
For every string in a tuple, checks if it is a substring of all other elements of the tuple, giving the indices of the elements that contain the substring.
"""


import polars as pl
from pathlib import Path
from typing import Generator, Iterable, Tuple
from aletk.utils import get_logger
from aletk.ResultMonad import try_except_wrapper

lgr = get_logger("Data Repository")

# Logic
import polars as pl
from typing import Tuple

def check_substrings(string_to_match: str, strings: Tuple[str, ...], string_to_match_index: int | None) -> str:
    # Convert string_to_match to lowercase for case-insensitive matching
    string_to_match_lower = string_to_match.lower()

    # Create a Polars DataFrame from the list of strings
    df = pl.DataFrame({"strings": list(strings)})

    # Use `.str.contains` to check if `string_to_match` is a substring (case-insensitive)
    matches = df.with_columns(
        pl.col("strings").str.to_lowercase().str.contains(string_to_match_lower).alias("match")
    )

    # Get the indices where the "match" is True
    indices = matches.filter(pl.col("match")).select(pl.col("strings").alias("index"))

    # Delete the row corresponding to string_to_match_index if it is not None
    if string_to_match_index is not None:
        indices = indices.filter(pl.col("index") != strings[string_to_match_index])

    # Extract and collect the indices as a list
    result_indices = indices.select(pl.col("index").alias("index")).to_series()

    # Return the indices as a comma-separated string
    return ", ".join(map(str, result_indices))

def check_substrings_pure(string_to_match: str, strings: Iterable[str], string_to_match_index: int | None) -> str:
    """
    Returns the indices of the strings in the tuple that contain the substring.
    """

    if string_to_match_index is not None:
        # Take out the string to match from the list
        array_to_match = list(strings)[0:string_to_match_index] + list(strings)[string_to_match_index+1:]
    else:
        array_to_match = list(strings)
        
    indices = tuple(
        index for index, string in enumerate(array_to_match) if string_to_match in string
    )

    result = ", ".join(f"{index}" for index in indices)

    return result


# Secondary side
def load_data(
    filename: str
) -> Tuple[str, ...]:
    """
    Loads the data from the file and returns it as a tuple of strings.
    """

    file_path = Path(filename)
    extension = file_path.suffix

    match extension:
        case ".txt":
            with open(file_path, "r") as file:
                data = tuple(
                    line.strip() for line in file
                )

        case ".csv":
            import csv

            with open(file_path, "r") as file:
                reader = csv.reader(file)
                data = tuple(row[0] for row in reader)

        case _:
            raise ValueError(f"File format '{extension}' not supported.")

    return data

def write_output(
    filename: str,
    data: Generator[str, None, None],
) -> None:
    """
    Writes the output to a file.
    """

    with open(filename, "w") as file:
        for line in data:
            file.write(f"{line}\n")


# Main process
@try_except_wrapper(lgr)
def main(
    input_filename: str,
    output_filename: str,
) -> None:
    """
    Main process.
    """

    data = tuple(load_data(input_filename))

    result = (
       check_substrings(
            string, data, index
        ) for index, string in enumerate(data)
    )

    # Write the output
    write_output(output_filename, result)


# Primary side
def cli() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Check for substrings in a list of strings.")

    parser.add_argument(
        "-i",
        "--input-filename",
        type=str,
        required=True,
        help="The input filename.",
    )

    parser.add_argument(
        "-o",
        "--output-filename",
        type=str,
        required=True,
        help="The output filename.",
    )

    args = parser.parse_args()

    main(args.input_filename, args.output_filename)


if __name__ == "__main__":
    cli()
