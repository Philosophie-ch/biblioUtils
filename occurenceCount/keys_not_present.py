#!/usr/bin/env python3

from typing import Generator, List


def not_appears_in_text(text: str, key: str) -> bool:
    """
    Check if a key does not appear in a text
    """
    return key not in text


def main(key_list: List[str], text: str) -> Generator[str, None, None]:
    """
    From a list of keys, return the keys that do not appear in the text.
    The keys that do not appear in the text are returned in a list with no duplicates.
    Returns a generator, for memory efficiency.
    """

    key_list_uniq = list(set(key_list))

    output = (key for key in key_list_uniq if not_appears_in_text(text, key))

    return output


def cli_presenter(output: Generator[str, None, None]) -> str:
    """
    Format the output for the command line interface: one key per line to be printed to stdout
    """
    return "\n".join(output)


def cli() -> None:
    """
    Command line interface for the key-count.py script
    """

    import argparse

    parser = argparse.ArgumentParser(description='Count the number of times a key appears in a text')
    parser.add_argument('--key-file', type=str, help='The file containing the keys to search for')
    parser.add_argument('--text-file', type=str, help='The file containing the text to search')

    args = parser.parse_args()

    with open(args.key_file, 'r') as f:
        keys = f.readlines()

    keys = [key.strip() for key in keys]

    with open(args.text_file, 'r') as f:
        text = f.read()

    output = main(keys, text)

    print(cli_presenter(output))


if __name__ == '__main__':
    cli()