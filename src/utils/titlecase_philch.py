#!/usr/bin/env python3

from typing import Generator, Iterable
from titlecase import titlecase

from src.utils.titlecase_constants import ALWAYS_SMALL


def _upper_first(str_in: str) -> str:
    """
    Capitalize the first letter of a string.
    """

    if len(str_in) > 1:
        result = f"{str_in[0].upper()}{str_in[1:]}"
    elif len(str_in) == 1:
        result = f"{str_in[0].upper()}"
    else:
        result = str_in

    return result


def _force_small(str_in: str, lower_caps_list: Iterable[str] = ALWAYS_SMALL) -> str:
    """
    Force some words to be lowercase, except for the first letter.
    """

    if " " in str_in:
        str_in_list = str_in.split(" ")
        result_list = [str_in_list[0]]

        for word_raw in str_in_list[1:]:
            brackets = "[]{}()"
            opening_b, closing_b = False, False
            word = ""

            if len(word_raw) == 0:
                result_list.append(word_raw)
                continue

            if word_raw[0] in brackets:
                word = word_raw[1:]
                opening_b = True

            if word_raw[-1] in brackets:
                word = word_raw[:-1]
                closing_b = True

            if not (word_raw[0] in brackets or word_raw[-1] in brackets):
                word = word_raw

            if word.lower() in lower_caps_list:
                word_processed = f"{word[0].lower()}{word[1:]}"

                if opening_b:
                    word_processed = f"{word_raw[0]}{word_processed}"

                if closing_b:
                    word_processed = f"{word}{word_raw[-1]}"

                result_list.append(word_processed)

            else:
                result_list.append(word_raw)

        result = " ".join(result_list)

    else:
        result = str_in

    return result


def _preserve_already_capitalized(original_str: str, str_in: str) -> str:
    """
    Preserves characters that are already capitalized
    """
    if len(str_in) > 1:
        result = "".join(
            [
                original_char if original_char.isupper() else new_char
                for original_char, new_char in zip(original_str, str_in)
            ]
        )

    else:
        result = str_in

    return result


def _preserve_latex_commands(original_str: str, str_in: str) -> str:
    """
    Preserves capitalization of LaTeX commands
    """
    if len(str_in) > 1:

        result = ""
        backslash = r"\ "[0]
        preserve_next = False

        for original_char, new_char in zip(original_str, str_in):

            if preserve_next:
                if original_char.islower():
                    result += original_char
                else:
                    result += new_char

                preserve_next = False
                continue

            if original_char == backslash:
                preserve_next = True
                result += original_char

            else:
                result += new_char

    else:
        result = str_in

    return result


def _preserve_bibkeys(original_str: str, str_in: str) -> str:
    """
    Preserves capitalization of bibkeys
    """
    result = str_in

    if " " in str_in:
        original_list = original_str.split(" ")
        str_in_list = str_in.split(" ")
        result_list = []

        for original_word, new_word in zip(original_list, str_in_list):
            if ":" in original_word[:-1]:
                """
                Bibkeys are usually in the form "author:year". If the ":" is at the end, then it's a subtitle marker, not a bibkey, so we ignore this case. As it's embedded LaTeX, words containing actual bibkeys will end with "}", never ":".
                """
                result_list.append(original_word)
            else:
                result_list.append(new_word)

        result = " ".join(result_list)

    return result


def _capitalize_subtitles_first_word(title_in: str) -> str:
    """
    Capitalize the first word of a subtitle. Will stop at the first subtitle marker found, in order of appearance:
    1. ": "
    2. " -- "
    """

    subtitle_markers = [": ", " -- "]
    result = title_in

    for m in subtitle_markers:

        if m in title_in:
            split_title = title_in.split(m)
            title = split_title[0]
            subtitle_list = split_title[1:]

            if len(subtitle_list) > 1:
                subtitle = m.join(subtitle_list)
                subtitle = _upper_first(subtitle)
                result = f"{title}{m}{subtitle}"

            elif len(subtitle_list) == 1:
                subtitle = _upper_first(subtitle_list[0])
                result = f"{title}{m}{subtitle}"

            else:
                result = title

            break

    return result


def titlecase_philch(title: str) -> str:
    """
    Convert a string to title case.
    """

    original_title = title

    lower_title = title.lower()

    result_pristined = _capitalize_subtitles_first_word(_force_small(_upper_first(titlecase(lower_title))))

    result_preserved_caps = _preserve_already_capitalized(original_title, result_pristined)

    result_preserved_latex = _preserve_latex_commands(original_title, result_preserved_caps)

    result_preserved_bibkeys = _preserve_bibkeys(original_title, result_preserved_latex)

    return result_preserved_bibkeys


def main(title_list: Iterable[str]) -> Generator[str, None, None]:
    """
    Loop over the main functionality. Returns a generator of title cased strings, as it's more memory-efficient than returning a list.
    """

    output = (titlecase_philch(title) for title in title_list)
    return output


def cli_presenter(output: Generator[str, None, None]) -> str:
    """
    Format the output for the command line interface: one title per line
    """

    return "".join(output)


def cli() -> None:

    # CLI inputs
    import argparse

    parser = argparse.ArgumentParser(
        description="Convert a list of strings to title case. Requires a file with one string per line. Outputs one title per line, directly to the standard output."
    )

    parser.add_argument(
        "-f",
        "--file",
        type=argparse.FileType("r"),
        required=True,
        help="File containing a list of strings to convert to title case. Each line of the file must be a string that we want to titlecase.",
    )

    titles_raw: Iterable[str] = parser.parse_args().file

    # Main
    titles = main(titles_raw)

    print(cli_presenter(titles))


if __name__ == "__main__":
    cli()
