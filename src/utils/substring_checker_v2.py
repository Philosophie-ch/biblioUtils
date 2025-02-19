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
def check_substrings_pl(string_to_match: str, strings: Tuple[str, ...], string_to_match_index: int | None) -> str:

    df = pl.DataFrame({"strings": list(strings)})

    if string_to_match_index is not None:
        # Take out the string to match from the list
        df = df.slice(0, string_to_match_index).vstack(df.slice(string_to_match_index + 1))

    # Use .str.contains to check if string_to_match is a substring 
    matches = df.with_columns(
        pl.col("strings").str.contains(string_to_match, literal=True).alias("match")
    )  # this thing omits trailing whitespace even if you say "literal=True"

    matched_strings = matches.filter(pl.col("match")).select("strings")
    result_strings = matched_strings["strings"].to_list()

    result = ", ".join(result_strings) if result_strings else ""

    # Return a comma-separated string of matches, or "" if no matches
    return result


def check_substrings(string_to_match: str, data: Tuple[str, ...], string_to_match_index: int | None) -> str:
    """
    Returns the indices of the strings in the tuple that contain the substring.
    """

    if string_to_match_index is not None:
        if string_to_match_index == 1:
            lgr.info(f"string to match: [[{repr(string_to_match)}]]")
        # Take out the string to match from the list
        array_data = data[0:string_to_match_index] + data[string_to_match_index+1:]
    else:
        array_data = data
        
    results = (
        matched for matched in array_data if string_to_match in matched
    )

    result = ", ".join(f"{string}" for string in results)

    return result


# Secondary side
def load_data(
    filename: str
) -> Tuple[str, ...]:
    """
    Loads the data from the file and returns it as a tuple of strings.
    """

    file_path = Path(filename)

    with open(file_path, "r") as file:
        data = tuple(
            "".join(line.split("\n")) for line in file
        )

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
    strings_filename: str,
    strings_to_match_filename: str,
    output_filename: str,
) -> None:
    """
    Main process.
    """

    lgr.info(f"Reading data from {strings_filename}...")
    data = tuple(load_data(strings_filename))
    strings_to_match = tuple(load_data(strings_to_match_filename))

    lgr.info("Computing generator...")
    result = (
       check_substrings(
           string_to_match=string,
           data=data,
           string_to_match_index=index
        ) for index, string in enumerate(strings_to_match)
    )

    lgr.info(f"Streaming result to {output_filename}...")
    write_output(output_filename, result)

    lgr.info("Done!")


# Primary side
def cli() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Check for substrings in a list of strings.")

    parser.add_argument(
        "-s",
        "--strings-filename",
        type=str,
        required=True,
        help="The filename of the file containing the strings to match. One string per line.",
    )

    parser.add_argument(
        "-m",
        "--strings-to-match-filename",
        type=str,
        required=True,
        help="The filename of the file containing the strings to match. One string per line. For the indices to work, it has to be a subset of the strings in the first file, starting at the same index.",
    )

    parser.add_argument(
        "-o",
        "--output-filename",
        type=str,
        required=True,
        help="The output filename.",
    )

    args = parser.parse_args()

    main(
        strings_filename = args.strings_filename,
        strings_to_match_filename = args.strings_to_match_filename,
        output_filename = args.output_filename,
    )



if __name__ == "__main__":
    cli()
