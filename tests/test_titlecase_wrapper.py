from src.utils import titlecase_wrapper


def test_dummy_titles() -> None:

    raw_titles = ["tiTle One", "TiTle tWo", "Title Three"]
    clean_titles = ["Title One", "Title Two", "Title Three"]

    output_generator = titlecase_wrapper.main(raw_titles)
    output = list(output_generator)

    assert output == clean_titles
