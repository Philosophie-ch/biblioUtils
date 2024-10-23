import os
from typing import Callable
from src.sdk.utils import remove_extra_whitespace
from src.sdk.types import Ok, Err


def file_in(file_path: str) -> Ok[list[str]] | Err:
    try:
        with open(file_path, "r") as file:
            lines = file.readlines()

            return Ok(out=lines)

    except Exception as e:
        err = Err(message=str(e), code=-1)
        return err


import re


def extract_citation_dependencies(input_str: str) -> Ok[list[str]] | Err:
    try:
        matches = re.findall(r"\\citet\{(.+?)\}|\\citep\{(.+?)\}", input_str)
        if matches:
            # Flatten the list of tuples and remove None values
            citation_keys = [remove_extra_whitespace(key) for match in matches for key in match if key]
            return Ok(out=citation_keys)

        return Err(message="No dependenceis found in line '{line}'", code=-1)

    except Exception as e:
        msg = f"Error while extracting dependencies from line '{input_str}': {e}"
        return Err(message=msg, code=-1)


def extract_field_curried(field: str) -> Ok[Callable[[str], Ok[str] | Err]] | Err:

    try:
        FIELD_POSITIONS = {
            "bibkey": 4,
            "title": 17,
            "crossref": 21,
            "note": 51,
        }

        if field not in FIELD_POSITIONS.keys():
            msg = f"Field {field} not found in FIELD_POSITIONS"
            return Err(message=msg, code=-1)

        position = FIELD_POSITIONS[field]

        def extract_field(line: str) -> Ok[str] | Err:
            try:
                parts = line.split("\t")
                field = parts[position]
                return Ok(out=field)

            except Exception as e:
                msg = f"Error while extracting field in position {position} from line '{line}': {str(e)}"
                return Err(message=msg, code=-1)

        return Ok(out=extract_field)

    except Exception as e:
        msg = f"Error while creating curried function for field {field}: {str(e)}"
        return Err(message=msg, code=-1)


extract_bibkey_r = extract_field_curried("bibkey")
if isinstance(extract_bibkey_r, Err):
    raise Exception(extract_bibkey_r.message)
extract_bibkey = extract_bibkey_r.out

extract_title_r = extract_field_curried("title")
if isinstance(extract_title_r, Err):
    raise Exception(extract_title_r.message)
extract_title = extract_title_r.out

extract_crossref_r = extract_field_curried("crossref")
if isinstance(extract_crossref_r, Err):
    raise Exception(extract_crossref_r.message)
extract_crossref = extract_crossref_r.out

extract_note_r = extract_field_curried("note")
if isinstance(extract_note_r, Err):
    raise Exception(extract_note_r.message)
extract_note = extract_note_r.out


def process_line(line: str) -> Ok[str] | Err:
    try:
        title_r, crossref_r, note_r = extract_title(line), extract_crossref(line), extract_note(line)

        title = title_r.out if isinstance(title_r, Ok) else ""

        if "crossref = {" in line:
            crossref_whtsp = crossref_r.out if isinstance(crossref_r, Ok) else ""
            crossref_str = remove_extra_whitespace(crossref_whtsp) if crossref_whtsp else ""
        else:
            crossref_str = ""

        crossref = [crossref_str] if crossref_str else []

        note = note_r.out if isinstance(note_r, Ok) else ""

        dependencies_title_r = extract_citation_dependencies(title)
        dependencies_note_r = extract_citation_dependencies(note)

        dependencies_title = dependencies_title_r.out if isinstance(dependencies_title_r, Ok) else []
        dependencies_note = dependencies_note_r.out if isinstance(dependencies_note_r, Ok) else []

        dependencies_l = dependencies_title + crossref + dependencies_note

        dependencies = ",".join(dependencies_l)

        bibkey_r = extract_bibkey(line)
        bibkey = bibkey_r.out if isinstance(bibkey_r, Ok) else f"Error parsing bibkey: {bibkey_r.message}"

        buffer = f"{dependencies};{bibkey}\n"

        return Ok(out=buffer)

    except Exception as e:
        msg = f"Error while processing line '{line}': {str(e)}"
        return Err(message=msg, code=-1)


def process_file(file_path: str) -> Ok[str] | Err:

    try:
        buffer = ""

        read_r = file_in(file_path)

        if isinstance(read_r, Err):
            print(f"Error reading file: {read_r.message}")
            return Err(message=read_r.message, code=read_r.code)

        for l in read_r.out:

            line_r = process_line(l)

            match line_r:

                case Ok(out=b):
                    buffer += b

                case Err(message=e):
                    buffer += f";;Error processing line: {e}\n"

        return Ok(out=buffer)

    except Exception as e:
        msg = f"Error while processing file '{file_path}': {str(e)}"
        return Err(message=msg, code=-1)


def console_out(buffer: str) -> None:
    print(buffer)


def file_out(buffer: str, out_file: str) -> Ok[None] | Err:
    try:
        # create folders if they don't exist
        out_dir = os.path.dirname(out_file)

        if not os.path.exists(out_dir):
            os.makedirs(out_dir)

        with open(out_file, "w") as file:
            file.write(buffer)

        return Ok(out=None)

    except Exception as e:
        return Err(message=str(e), code=-1)


def compute_process_line(line: str) -> None:
    try:
        result_r = process_line(line)

        match result_r:

            case Err(message=e):
                console_out(f"Error: {e}")

            case Ok(out=b):
                console_out(b)

    except Exception as e:
        console_out(f"Error: {e}")


def compute_process_file(file_path: str) -> None:
    try:
        result_r = process_file(file_path)

        match result_r:

            case Err(message=e):
                console_out(f"Error: {e}")

            case Ok(out=b):
                file_in_path = file_path
                basename = os.path.basename(file_in_path)
                name = os.path.splitext(basename)[0]
                extension = os.path.splitext(basename)[1]

                write_r = file_out(b, f"{name}-out-depends_on{extension}")

                match write_r:
                    case Err(message=e):
                        console_out(f"Error writing file: {e}")

                    case Ok(out=None):
                        console_out(f"File written to {name}-out-depends_on{extension}")

    except Exception as e:
        console_out(f"Error: {e}")


def cli() -> None:

    import argparse

    description = """
    Extracts 'depends_on' from a blumbib file; i.e., the additional bibkeys that an entry needs in a bibliography to make it self-contained.



    """

    parser = argparse.ArgumentParser(
        description="Extracts 'depends_on' from a blumbib file; i.e., the additional bibkeys that an entry needs in a bibliography to make it self-contained."
    )

    group = parser.add_mutually_exclusive_group()

    group.add_argument(
        "-f",
        "--file",
        type=str,
        help="File containing the bib entries to process.",
    )

    group.add_argument(
        "-l",
        "--line",
        type=str,
        help="Single line to process.",
    )

    args = parser.parse_args()

    if args.file:
        compute_process_file(args.file)

    elif args.line:
        compute_process_line(args.line)

    else:
        parser.print_help()
        return


if __name__ == "__main__":
    cli()
