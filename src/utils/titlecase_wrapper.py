#!/usr/bin/env python3

from typing import Generator, Iterable
from titlecase import titlecase


def titlecase_wrapper(title: str) -> str:
    """
    Convert a string to title case. Forces the `titlecase` method by converting the string to lowercase first.
    """
    lower_title = title.lower()
    out = titlecase(lower_title)
    out_str = str(out)

    return out_str

def main(title_list: Iterable[str]) -> Generator[str, None, None]:
    """
    Loop over the main functionality. Returns a generator of title cased strings, as it's more memory-efficient than returning a list.
    """

    output = (titlecase_wrapper(title) for title in title_list)
    return output


def cli_presenter(output: Generator[str, None, None]) -> str:
    """
    Format the output for the command line interface: one title per line
    """

    return "".join(output)


def cli() -> None:

    # CLI inputs
    import argparse

    parser = argparse.ArgumentParser(description="Convert a list of strings to title case.")

    parser.add_argument(
        "--file",
        type=argparse.FileType("r"),
        help="File containing a list of strings to convert to title case. Each line of the file must be a string that we want to titlecase.",
    )

    titles_raw: Iterable[str] = parser.parse_args().file

    # Main
    titles = main(titles_raw)

    print(cli_presenter(titles))


if __name__ == "__main__":
    cli()
