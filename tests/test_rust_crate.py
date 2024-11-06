import rust_crate as rc


def test_rust_crate_is_working() -> None:

    result = rc.sum_as_string(1, 1)

    assert result == "2"
