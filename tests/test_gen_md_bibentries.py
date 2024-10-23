import tempfile
import os

from src.ref_pipe import gen_md as mdbib
from src.sdk.types import Ok


TEST_PROFILES_CSV = """id,lastname,_biblio_keys,_biblio_keys_dependencies
1,Doe,"key1,key2,key23"
2,Smith,"key4,key5,key6"
"""

TEST_DESIRED_MD_ONE = """---
title: "HTML References Pipeline"
bibliography: ../../../dialectica.bib
---

@key1

@key2

@key23

# References
"""

TEST_DESIRED_MD_TWO = """---
title: "HTML References Pipeline"
bibliography: ../../../dialectica.bib
---

@key4

@key5

@key6

# References
"""


def test_load_profiles_csv() -> None:

    with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
        f.write(TEST_PROFILES_CSV)
        temp_file_name = f.name

    try:
        output = mdbib.load_profiles_csv(temp_file_name, "utf-8")

        assert isinstance(output, Ok)
        for profile in output.out:
            assert isinstance(profile, mdbib.Profile)
            assert profile.id in ["1", "2"]
            assert profile.lastname in ["Doe", "Smith"]
            assert profile.biblio_keys in "key1,key2,key23" or profile.biblio_keys in "key4,key5,key6"
            assert profile.biblio_keys_dependencies is None

    # clean up
    finally:
        os.unlink(f.name)


def test_prepare_md() -> None:

    profile = mdbib.Profile(id="1", lastname="Doe", biblio_keys="key1,key2,key23", biblio_keys_dependencies=None)

    temp_folder = tempfile.mkdtemp()

    try:
        output = mdbib.prepare_md(profile, temp_folder)

        assert isinstance(output, Ok)
        assert output.out.content == TEST_DESIRED_MD_ONE

    finally:
        os.rmdir(temp_folder)


def test_load_csv_and_prepare_md_pipe() -> None:

    with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
        f.write(TEST_PROFILES_CSV)
        temp_file_name = f.name

    try:
        temp_folder = tempfile.mkdtemp()

        step_one_output = mdbib.load_profiles_csv(temp_file_name, "utf-8")

        assert isinstance(step_one_output, Ok)

        profiles = step_one_output.out

        for profile in profiles:

            step_two_output = mdbib.prepare_md(profile, temp_folder)

            assert isinstance(step_two_output, Ok)

            if profile.lastname == "Doe":
                assert step_two_output.out.content == TEST_DESIRED_MD_ONE
            elif profile.lastname == "Smith":
                assert step_two_output.out.content == TEST_DESIRED_MD_TWO

    # clean up
    finally:
        os.unlink(f.name)
        os.rmdir(temp_folder)
