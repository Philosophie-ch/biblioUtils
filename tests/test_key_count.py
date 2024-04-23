import os
from occurenceCount import key_count
import tempfile


def test_key_count_no_keys() -> None:

    key_list = ['phil-perspectives:1997', 'vanderveken_d:2005', 'ajdukiewicz:1978']

    with tempfile.NamedTemporaryFile(mode='w') as key_file:
        key_file.write('\n'.join(key_list))
        key_file.seek(0)

        text = 'This is a text that does not contain any of the keys in the key list'

        with tempfile.NamedTemporaryFile(mode='w') as text_file:
            text_file.write(text)
            text_file.seek(0)

            output = key_count.main(key_list, text)

            assert output == key_list 

    os.remove(key_file.name)
    os.remove(text_file.name)