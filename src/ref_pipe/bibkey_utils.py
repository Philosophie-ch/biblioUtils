from typing import Iterable, Literal, NamedTuple

from src.sdk.utils import get_logger, remove_extra_whitespace

lgr = get_logger("Bibkey Utils")


class Bibkey(NamedTuple):
    first_author: str
    other_authors: str | None
    year: int | Literal["unpub", "forthcoming"] | str
    year_suffix: str


class BibkeyError(NamedTuple):
    text: str
    position: int
    error: str

    def __str__(self) -> str:
        return f"'{self.text}' at line {self.position} --- '{self.error}'"


def parse_bibkey(text: str, text_position_d: dict[str, int]) -> Bibkey | BibkeyError:
    """
    Return either a Bibkey object, or a BibkeyError object to indicate a parsing error.
    """

    try:
        parts = text.split(":")
        if len(parts) != 2:
            raise ValueError(f"Unexpected number of bibkey parts for '{text}': '{parts}'")

        author_parts = parts[0].split("-")
        year_parts = parts[1]

        if len(author_parts) == 1:
            first_author = author_parts[0]
            other_authors = None
        elif len(author_parts) == 2:
            first_author = author_parts[0]
            other_authors = author_parts[1]
        else:
            raise ValueError(f"Unexpected bibkey author parts for '{text}': '{author_parts}'")

        char_index_type_d = {i: (char, char.isdigit()) for i, char in enumerate(year_parts)}

        year_l: list[str] = []
        int_breakpoint = None
        for value in char_index_type_d.items():
            i, (char, is_digit) = value
            if is_digit:
                year_l.append(char)
                int_breakpoint = i
            else:
                break

        if year_l != []:
            year_int = int(f"{''.join(year_l)}")
        else:
            year_int = None

        if int_breakpoint is not None:
            year_suffix = year_parts[int_breakpoint + 1 :]

        else:
            # all characters are non-digits
            year_suffix = "".join(year_parts)

        if year_suffix != "" and year_suffix not in ["unpub", "forthcoming"]:
            if len(year_suffix) > 1:
                if "unpub" not in year_suffix and "forthcoming" not in year_suffix:
                    lgr.warning(f"Unexpected year suffix for '{text}': '{year_suffix}'")
            elif len(year_suffix) == 1:
                if year_suffix.isdigit():
                    lgr.warning(f"Unexpected year suffix for '{text}': '{year_suffix}'")

        if year_int is None and year_suffix is None:
            raise ValueError(f"Could not parse year for '{text}': '{year_parts}'")

        if year_int is None:
            return Bibkey(first_author=first_author, other_authors=other_authors, year=year_suffix, year_suffix="")

        else:
            return Bibkey(
                first_author=first_author, other_authors=other_authors, year=year_int, year_suffix=year_suffix
            )

    except ValueError as e:
        return BibkeyError(text, text_position_d[text] + 1, str(e))


def validate_bibkeys(bibkeys: Iterable[str], bibkey_position_d: dict[str, int]) -> None:
    """
    Validates an array of bibkeys. Raises a ValueError if any of them is invalid.
    """

    parse_result = tuple(parse_bibkey(bk, bibkey_position_d) for bk in bibkeys)
    error_results = tuple(r for r in parse_result if isinstance(r, BibkeyError))

    if error_results:
        error_results_str = "\n".join(str(error_result) for error_result in error_results)
        error_results_len = len(error_results)
        raise ValueError(f"Found {error_results_len} errors while parsing bibkeys:\n{error_results_str}")
    else:
        return None


def _extract_bibkey(line: str) -> str:
    bracket_split = line.split("{")
    comma_split = bracket_split[1].split(",")
    bibkey = comma_split[0]
    return remove_extra_whitespace(bibkey)


def load_validate_bibliography_bibkeys(bibliography_file: str) -> tuple[frozenset[str], dict[str, int]]:
    with open(bibliography_file, "r") as f:
        bibkey_linenum_d = {_extract_bibkey(line): i for i, line in enumerate(f.readlines())}

    with open(bibliography_file, "r") as f:
        bibkeys = frozenset({_extract_bibkey(line) for line in f.readlines()})

    with open(bibliography_file, "r") as f:
        bibliography_len = len(f.readlines())

    bibkeys_len = len(bibkeys)

    # Sanitize bibliography
    if bibkeys_len != len(bibkey_linenum_d):
        raise ValueError(
            f"The number of bibkeys and the number of line numbers should be the same. This means that bibkeys are not unique. Found {len(bibkeys)} bibkeys but {len(bibkey_linenum_d)} line numbers in the bibliography. Fix the consistency of your bibliography and try again."
        )

    if bibkeys_len != bibliography_len:
        raise ValueError(
            f"The number of bibkeys ({bibkeys_len}) should be the same as the number of lines in the bibliography ({bibliography_len}). This means that some lines didn't contain bibkeys at all, or your bibliography file is not a valid bib file. Fix the consistency of your bibliography and try again."
        )

    # Assert that all bibkeys have the standard structure
    validate_bibkeys(bibkeys, bibkey_linenum_d)

    return bibkeys, bibkey_linenum_d
