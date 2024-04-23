import os
import subprocess
from occurenceCount import keys_not_present
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

            output = keys_not_present.main(key_list, text)

            assert output == key_list 

    if os.path.exists(key_file.name):
        os.remove(key_file.name)
    if os.path.exists(text_file.name):
        os.remove(text_file.name)


def test_key_count_some_keys() ->  None:
    
        key_list = ['phil-perspectives:1997', 'vanderveken_d:2005', 'ajdukiewicz:1978']
    
        with tempfile.NamedTemporaryFile(mode='w') as key_file:
            key_file.write('\n'.join(key_list))
            key_file.seek(0)
    
            text = 'This is a text that contains some of the keys in the key list:\nphil-perspectives:1997\nand ajdukiewicz:1978 is wrapped in some text'
    
            with tempfile.NamedTemporaryFile(mode='w') as text_file:
                text_file.write(text)
                text_file.seek(0)
    
                output = keys_not_present.main(key_list, text)
    
                assert output == ['vanderveken_d:2005']
    
        if os.path.exists(key_file.name):
            os.remove(key_file.name)
        if os.path.exists(text_file.name):
            os.remove(text_file.name)



def test_cli() -> None:

    with tempfile.NamedTemporaryFile(mode='w', delete=False) as key_file:
        key_file.write('phil-perspectives:1997\nvanderveken_d:2005\najdukiewicz:1978')
        key_file.seek(0)

        text = 'This is a text that contains some of the keys in the key list:\nphil-perspectives:1997\nand ajdukiewicz:1978 is wrapped in some text'

        with tempfile.NamedTemporaryFile(mode='w') as text_file:
            text_file.write(text)
            text_file.seek(0)

            command = ["occurenceCount/keys_not_present.py", "--key-file", key_file.name, "--text-file", text_file.name]

            result = subprocess.run(command, capture_output=True, text=True)

            assert result.returncode == 0
            assert result.stdout.strip() == "vanderveken_d:2005"

        if os.path.exists(key_file.name):
            os.remove(key_file.name)
        if os.path.exists(text_file.name):
            os.remove(text_file.name)


