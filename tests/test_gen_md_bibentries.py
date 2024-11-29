import tempfile
import os

from src.ref_pipe.filesystem_io import load_bibentities
from src.ref_pipe import gen_md as mdbib
from src.ref_pipe.models import BibEntity
from src.sdk.ResultMonad import Ok


TEST_PROFILES_CSV = """id,biblio_name,login,biblio_keys,biblio_keys_further_references,biblio_dependencies_keys
1,Doe,doe,"key1,key2,key23"
2,Smith,smith,"key4,key5,key6"
"""

TEST_DESIRED_MD_ONE = """---
title: "HTML References Pipeline"
bibliography: ../../../biblio.bib
---

@key1

@key2

@key23

# References
"""

TEST_DESIRED_MD_TWO = """---
title: "HTML References Pipeline"
bibliography: ../../../biblio.bib
---

@key4

@key5

@key6

# References
"""


def test_load_profiles_csv() -> None:

    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        f.write(TEST_PROFILES_CSV)
        temp_file_name = f.name

    try:
        output = load_bibentities(temp_file_name, "utf-8", "profile")

        assert isinstance(output, Ok)
        for profile in output.out:
            assert isinstance(profile, BibEntity)
            assert profile.id in ["1", "2"]
            assert profile.entity_key in ["Doe", "Smith"]
            assert profile.main_bibkeys == {"key1", "key2", "key23"} or profile.main_bibkeys == {"key4", "key5", "key6"}
            assert profile.depends_on == frozenset()

    # clean up
    finally:
        os.unlink(f.name)


def test_prepare_md() -> None:

    profile = BibEntity(
        id="1",
        entity_key="Doe",
        url_endpoint="doe",
        main_bibkeys=frozenset({"key1", "key2", "key23"}),
        further_references=frozenset(),
        depends_on=frozenset(),
    )

    temp_folder = tempfile.mkdtemp()

    try:
        output = mdbib.prepare_md(profile, temp_folder, "/test", temp_folder)

        assert isinstance(output, Ok)
        assert output.out.markdown is not None
        assert "key1" in output.out.markdown.main_file.content
        assert "key2" in output.out.markdown.main_file.content
        assert "key23" in output.out.markdown.main_file.content

    finally:
        os.rmdir(temp_folder)


def test_load_csv_and_prepare_md_pipe() -> None:

    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        f.write(TEST_PROFILES_CSV)
        temp_file_name = f.name

    try:
        temp_folder = tempfile.mkdtemp()

        step_one_output = load_bibentities(temp_file_name, "utf-8", "profile")

        assert isinstance(step_one_output, Ok)

        profiles = step_one_output.out

        for profile in profiles:

            step_two_output = mdbib.prepare_md(profile, temp_folder, "/test", temp_folder)

            assert isinstance(step_two_output, Ok)

            if profile.entity_key == "Doe":
                assert step_two_output.out.markdown is not None
                assert "key1" in step_two_output.out.markdown.main_file.content
                assert "key2" in step_two_output.out.markdown.main_file.content
                assert "key23" in step_two_output.out.markdown.main_file.content
            elif profile.entity_key == "Smith":
                assert step_two_output.out.markdown is not None
                assert "key4" in step_two_output.out.markdown.main_file.content
                assert "key5" in step_two_output.out.markdown.main_file.content
                assert "key6" in step_two_output.out.markdown.main_file.content

    # clean up
    finally:
        os.unlink(f.name)
        os.rmdir(temp_folder)
