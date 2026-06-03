from src.utils.md_direct_refs import (
    remove_yaml_front_matter,
    get_citations,
    get_keys,
    get_segregated_keys,
    is_non_key,
    key_cleaner,
    gen_dltc_filename,
)
import re
from pathlib import Path

CITATION_PATTERN = re.compile(
    r'(?<!\w)\[?([-]?)@{?([a-zA-Z0-9_.:$/%&+?<>~#-]+)}?(?:,?\s*(pp?\.\s[^\];]+|sec\.\s[^\];]+|chap\.\s[^\];]+)?)?(?:,\s*([^\];]+))?\]?'
)

ALL_BIBKEYS = (
    "huemer_m:2013c",
    "dreier_j:1990",
    "harman_gh:1996",
    "wong_db:1984",
    "street_s:2008a",
    "mackie_jl:1977",
    "streumer:2017",
    "blackburn_s:1998",
    "gibbard_af:2003",
    "smith_j:2020",
)


def test_remove_yaml_front_matter_strips_yaml() -> None:
    content = "---\ntitle: Test\nauthor: Someone\n---\n\nBody text here."
    result = remove_yaml_front_matter(content)
    assert result == "Body text here."


def test_remove_yaml_front_matter_no_yaml() -> None:
    content = "Body text with no front matter."
    result = remove_yaml_front_matter(content)
    assert result == content


def test_remove_yaml_front_matter_dots_delimiter() -> None:
    content = "---\ntitle: Test\n...\n\nBody text here."
    result = remove_yaml_front_matter(content)
    assert result == "Body text here."


def test_citations_in_paragraph() -> None:
    text = "As argued by @smith_j:2020 and [-@huemer_m:2013c, 266], this is clear."
    citations = get_citations((text,), CITATION_PATTERN)
    assert "smith_j:2020" in citations
    assert "huemer_m:2013c" in citations


def test_citations_in_list_items() -> None:
    text = """Some intro text.

-   first point [*moral relativism* in the style of, e.g., @dreier_j:1990;
    @harman_gh:1996; @wong_db:1984], or

-   second point [*error-theory* à la @mackie_jl:1977; @streumer:2017], or

-   third point [as *non-cognitivists* hold, e.g., @blackburn_s:1998; @gibbard_af:2003].
"""
    citations = get_citations((text,), CITATION_PATTERN)
    assert "dreier_j:1990" in citations
    assert "harman_gh:1996" in citations
    assert "wong_db:1984" in citations
    assert "mackie_jl:1977" in citations
    assert "streumer:2017" in citations
    assert "blackburn_s:1998" in citations
    assert "gibbard_af:2003" in citations


def test_citations_in_blockquote() -> None:
    text = """> This is a blockquote with a citation [@huemer_m:2013c, 263]."""
    citations = get_citations((text,), CITATION_PATTERN)
    assert "huemer_m:2013c" in citations


def test_citations_suppress_author() -> None:
    text = "Smith's [-@smith_j:2020] argument fails."
    citations = get_citations((text,), CITATION_PATTERN)
    assert "smith_j:2020" in citations


def test_is_non_key_section_refs() -> None:
    assert is_non_key("sec:1") is True
    assert is_non_key("sta:antitorture-argument") is True
    assert is_non_key("fig:diagram") is True
    assert is_non_key("eq:1") is True
    assert is_non_key("thm:main") is True
    assert is_non_key("def:concept") is True
    assert is_non_key("lem:helper") is True
    assert is_non_key("tbl:data") is True
    assert is_non_key("prop:main") is True
    assert is_non_key("rem:note") is True


def test_is_non_key_no_colon() -> None:
    assert is_non_key("nokey") is True


def test_is_non_key_bibkey() -> None:
    assert is_non_key("smith_j:2020") is False
    assert is_non_key("huemer_m:2013c") is False


def test_key_cleaner_trailing_dots() -> None:
    assert key_cleaner("smith_j:2020.") == "smith_j:2020"


def test_key_cleaner_trailing_question_mark() -> None:
    assert key_cleaner("fine_k:2016?") == "fine_k:2016"


def test_key_cleaner_trailing_exclamation() -> None:
    assert key_cleaner("smith_j:2020!") == "smith_j:2020"


def test_key_cleaner_trailing_comma() -> None:
    assert key_cleaner("smith_j:2020,") == "smith_j:2020"


def test_key_cleaner_trailing_semicolon() -> None:
    assert key_cleaner("smith_j:2020;") == "smith_j:2020"


def test_key_cleaner_trailing_colons() -> None:
    assert key_cleaner("smith_j:2020:") == "smith_j:2020"


def test_key_cleaner_leading_colons() -> None:
    assert key_cleaner(":smith_j:2020") == "smith_j:2020"


def test_key_cleaner_double_dashes() -> None:
    assert key_cleaner("smith_j:2020--268") == "smith_j:2020"


def test_key_cleaner_triple_dashes() -> None:
    assert key_cleaner("smith_j:2020---end") == "smith_j:2020"


def test_get_keys_separates_non_keys() -> None:
    citations = {"sec:1", "smith_j:2020", "fig:diagram", "huemer_m:2013c"}
    non_keys, apparent_keys = get_keys(citations)
    assert "sec:1" in non_keys
    assert "fig:diagram" in non_keys
    assert "smith_j:2020" in apparent_keys
    assert "huemer_m:2013c" in apparent_keys


def test_gen_dltc_filename() -> None:
    assert gen_dltc_filename(Path("francen-2024.md")) == "francen:2024"
    assert gen_dltc_filename(Path("mariscal_c-rondel-2024.md")) == "mariscal_c-rondel:2024"
    assert gen_dltc_filename(Path("pinheirodasilva-2024.md")) == "pinheirodasilva:2024"
    assert gen_dltc_filename(Path("blumson-joaquin-2024.md")) == "blumson-joaquin:2024"
    assert gen_dltc_filename(Path("demirli-zenker-2024.md")) == "demirli-zenker:2024"


def test_get_segregated_keys_paragraph() -> None:
    md = "---\ntitle: Test\n---\n\nSee @smith_j:2020 and @huemer_m:2013c for details."
    direct_refs, not_in_bibfile, non_keys = get_segregated_keys(ALL_BIBKEYS, md)
    assert "smith_j:2020" in direct_refs
    assert "huemer_m:2013c" in direct_refs


def test_get_segregated_keys_list_items() -> None:
    md = """---
title: Test
---

Some intro:

-   point A [@dreier_j:1990; @harman_gh:1996]
-   point B [@mackie_jl:1977]
"""
    direct_refs, not_in_bibfile, non_keys = get_segregated_keys(ALL_BIBKEYS, md)
    assert "dreier_j:1990" in direct_refs
    assert "harman_gh:1996" in direct_refs
    assert "mackie_jl:1977" in direct_refs


def test_get_segregated_keys_blockquote() -> None:
    md = """---
title: Test
---

> A quoted passage [@smith_j:2020, 42].
"""
    direct_refs, not_in_bibfile, non_keys = get_segregated_keys(ALL_BIBKEYS, md)
    assert "smith_j:2020" in direct_refs


def test_get_segregated_keys_nested_list_in_blockquote() -> None:
    md = """---
title: Test
---

> Some quote:
>
> -   nested item [@dreier_j:1990]
> -   another [@blackburn_s:1998; @gibbard_af:2003]
"""
    direct_refs, not_in_bibfile, non_keys = get_segregated_keys(ALL_BIBKEYS, md)
    assert "dreier_j:1990" in direct_refs
    assert "blackburn_s:1998" in direct_refs
    assert "gibbard_af:2003" in direct_refs


def test_get_segregated_keys_non_keys_filtered() -> None:
    md = """---
title: Test
---

See @sec:1 and @sta:antitorture-argument and @smith_j:2020.
"""
    direct_refs, not_in_bibfile, non_keys = get_segregated_keys(ALL_BIBKEYS, md)
    assert "smith_j:2020" in direct_refs
    assert "sec:1" in non_keys
    assert "sta:antitorture-argument" in non_keys


def test_get_segregated_keys_unknown_bibkey() -> None:
    md = """---
title: Test
---

See @unknown_author:2099 for details.
"""
    direct_refs, not_in_bibfile, non_keys = get_segregated_keys(ALL_BIBKEYS, md)
    assert "unknown_author:2099" in not_in_bibfile
    assert len(direct_refs) == 0


def test_get_segregated_keys_mixed_depths() -> None:
    md = """---
title: Test
---

Paragraph citation @huemer_m:2013c.

-   List citation [@dreier_j:1990; @harman_gh:1996]

> Blockquote citation [@smith_j:2020, 263]

1.  Numbered list citation @blackburn_s:1998.
"""
    direct_refs, not_in_bibfile, non_keys = get_segregated_keys(ALL_BIBKEYS, md)
    assert "huemer_m:2013c" in direct_refs
    assert "dreier_j:1990" in direct_refs
    assert "harman_gh:1996" in direct_refs
    assert "smith_j:2020" in direct_refs
    assert "blackburn_s:1998" in direct_refs
