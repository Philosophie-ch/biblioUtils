from utils import title_case


def test_dummy_titles() -> None:

    raw_titles = ["tiTle One", "TiTle tWo", "Title Three"]
    clean_titles = ["Title One", "Title Two", "Title Three"]

    output_generator = title_case.main(raw_titles)
    output = list(output_generator)

    assert output == clean_titles
