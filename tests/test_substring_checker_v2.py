
import tempfile
from src.utils.substring_checker_v2 import check_substrings, load_data


def test_small_substring_checker() -> None:
    strings = (
        "`t Hooft, Gerard",
        "a Zamayón, Pelagius",
        "`t Hooft, Gerard"
    )

    result = check_substrings("t Hooft", strings, None)
    assert result == "`t Hooft, Gerard, `t Hooft, Gerard"


def test_small_substring_checker_array_with_indeces_to_ignore() -> None:
    strings = (
        "`t Hooft, Gerard",
        "a Zamayón, Pelagius",
        "`t Hooft, Gerard"
    )

    result = tuple(
        check_substrings(string, strings, index) for index, string in enumerate(strings)
    )

    assert result == ("`t Hooft, Gerard", "", "`t Hooft, Gerard")


def test_substring_checker_array_longer() -> None:

    strings = (
        "`t Hooft, Gerard",
        "a Zamayón, Pelagius",
        "A. Acharya",
        "Gerard `t Hooft",
        "Pelagius a Zamayón",
        "A. Fernández-Margarit",
        "A. Francisca Snoeck Henkemans",
        "Jan M. Żytkow",
        "Żytkow, Jan M."
    )

    try:
        # write strings to a tmp file
        tmp_filename = tempfile.mktemp() + ".csv"

        with open(tmp_filename, "w") as file:
            for string in strings:
                file.write(string + "\n")

        # read strings from the tmp file
        data = tuple(load_data(tmp_filename))

        result_from_file = tuple(
            check_substrings(string, data, index) for index, string in enumerate(data)
        )

        result_from_tuple = tuple(
            check_substrings(string, strings, index) for index, string in enumerate(strings)
        )

        expected_result_l = [""] * len(strings)
        expected_result_tup = tuple(expected_result_l)

        assert result_from_tuple == expected_result_tup
        assert result_from_file == expected_result_tup
    
    finally:
        import os
        os.remove(tmp_filename)


def test_whitespace_added_substring_checker() -> None:
    strings = (
        "Joseph A. Gallian",
    )

    result = check_substrings(" A. Galli ", strings, None)
    assert result == ""