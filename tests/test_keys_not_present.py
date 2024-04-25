import os
import subprocess
from src.utils import keys_not_present
import tempfile


def test_no_keys() -> None:

    key_list = ["phil-perspectives:1997", "vanderveken_d:2005", "ajdukiewicz:1978"]

    text = "This is a text that does not contain any of the keys in the key list"

    output_generator = keys_not_present.main(key_list, text)
    output = list(output_generator)

    assert output.sort() == key_list.sort()


def test_some_keys() -> None:

    key_list = ["phil-perspectives:1997", "vanderveken_d:2005", "ajdukiewicz:1978"]

    text = "This is a text that contains some of the keys in the key list:\nphil-perspectives:1997\nand ajdukiewicz:1978 is wrapped in some text"

    output_generator = keys_not_present.main(key_list, text)
    output = list(output_generator)

    assert output == ["vanderveken_d:2005"]


def test_duplicate_keys() -> None:

    key_list = [
        "phil-perspectives:1997",
        "vanderveken_d:2005",
        "ajdukiewicz:1978",
        "phil-perspectives:1997",
        "vanderveken_d:2005",
        "ajdukiewicz:1978",
    ]

    text = "This is a text that contains some of the keys in the key list:\nphil-perspectives:1997\nand ajdukiewicz:1978 is wrapped in some text"

    output_generator = keys_not_present.main(key_list, text)
    output = list(output_generator)
    assert output == ["vanderveken_d:2005"]


def test_cli() -> None:

    with tempfile.NamedTemporaryFile(mode="w", delete=False) as key_file:
        key_file.write("phil-perspectives:1997\nvanderveken_d:2005\najdukiewicz:1978")
        key_file.seek(0)

        text = "This is a text that contains some of the keys in the key list:\nphil-perspectives:1997\nand ajdukiewicz:1978 is wrapped in some text"

        with tempfile.NamedTemporaryFile(mode="w") as text_file:
            text_file.write(text)
            text_file.seek(0)

            command = ["src/utils/keys_not_present.py", "--key-file", key_file.name, "--text-file", text_file.name]

            result = subprocess.run(command, capture_output=True, text=True)

            assert result.returncode == 0
            assert result.stdout.strip() == "vanderveken_d:2005"

        if os.path.exists(key_file.name):
            os.remove(key_file.name)
        if os.path.exists(text_file.name):
            os.remove(text_file.name)
