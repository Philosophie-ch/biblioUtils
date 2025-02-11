
from src.utils.substring_checker import check_substrings


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

