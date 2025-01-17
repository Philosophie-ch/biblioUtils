import os
from typing import Callable, Generator, NamedTuple
from bs4 import BeautifulSoup, Tag

from aletk.ResultMonad import light_error_handler, main_try_except_wrapper
from aletk.utils import get_logger, lginf


lgr = get_logger("DLTC Web Postprocessor")


###### Main logic
type TFixFootnotes = Callable[[str], str]
type TRemoveReferences = Callable[[str], str]
######


###### Composite Logic
class Content(NamedTuple):
    location: str
    content: str


def postprocess_html(
    raw_content: Content, fix_footnotes: TFixFootnotes, remove_references: TRemoveReferences
) -> Content:

    fixed = remove_references(fix_footnotes(raw_content.content))
    return Content(location=raw_content.location, content=fixed)


######

###### Abstract Process
type TProcessInput = Generator[Content, None, None]

type TContentReader[ReaderIn] = Callable[[ReaderIn], TProcessInput]

type TProcessOutput = Generator[Content, None, None]

type TContentWriter[WriterIn] = Callable[[TProcessOutput, WriterIn], None]


@light_error_handler(True)
def abstract_process[
    I, O
](
    content_reader: TContentReader[I],
    reader_input: I,
    fix_footnotes: TFixFootnotes,
    remove_references: TRemoveReferences,
    content_writer: TContentWriter[O],
    writer_input: O,
) -> None:
    frame = f"Main Process"
    lginf(frame, "Reading content", lgr)

    raw_content = content_reader(reader_input)

    lginf(frame, "Processing content", lgr)
    processed = (
        postprocess_html(raw_content=raw, fix_footnotes=fix_footnotes, remove_references=remove_references)
        for raw in raw_content
    )

    lginf(frame, "Writing content", lgr)
    content_writer(processed, writer_input)

    lginf(frame, "Done", lgr)
    return None


######


###### Concrete Implementations for modular functions


## Logic w/ bs4
def bs_fix_footnotes(file_content: str) -> str:
    soup = BeautifulSoup(file_content, 'html.parser')
    footnotes = soup.find('section', id='footnotes')
    if footnotes and isinstance(footnotes, Tag):
        # replace the "section" tag by "aside"
        # this fixes the issue with the footnote numbers rendering weirdly in the portal
        footnotes.name = "aside"

    return str(soup)


def bs_remove_references(file_content: str) -> str:
    soup = BeautifulSoup(file_content, 'html.parser')

    references = soup.find('div', id="c1-refs")
    if references and isinstance(references, Tag):
        references.decompose()

    references_header = soup.find('h1', string='References')
    if references_header and isinstance(references_header, Tag):
        references_header.decompose()

    return str(soup)


## I/O w/ filesystem
def read_file(file_path: str) -> Content:
    with open(file_path, 'r') as file:
        return Content(location=file_path, content=file.read())


def filesystem_content_reader(input_dirname: str) -> TProcessInput:

    frame = "Filesystem Content Reader"

    file_paths = frozenset(
        os.path.join(input_dirname, file_name) for file_name in os.listdir(input_dirname) if file_name.endswith('.html')
    )

    missing_files = frozenset(file_path for file_path in file_paths if not os.path.exists(file_path))

    if missing_files != frozenset():
        raise FileNotFoundError(f"The following input files were not found: {missing_files}")
    
    lginf(frame, f"Reading {len(file_paths)} files from {input_dirname}", lgr)

    process_input = (read_file(file_path) for file_path in file_paths)

    return process_input


def write_file(processed_content: Content) -> None:
    with open(processed_content.location, 'w') as file:
        file.write(processed_content.content)


def filesystem_content_writer(processed_contents: TProcessOutput, output_dirname: str) -> None:

    frame = "Filesystem Content Writer"

    output_dir_swap = tuple(
        Content(
            location=os.path.join(output_dirname, os.path.basename(processed_content.location)),
            content=processed_content.content,
        )
        for processed_content in processed_contents
    )

    missing_dirs = frozenset(
        output_content.location
        for output_content in output_dir_swap
        if not os.path.exists(os.path.dirname(output_content.location))
    )

    if missing_dirs != frozenset():
        raise FileNotFoundError(f"The following output directories were not found: {missing_dirs}")

    lginf(frame, f"Writing {len(output_dir_swap)} files to {output_dirname}", lgr)

    for output_content in output_dir_swap:
        write_file(output_content)

        if not os.path.exists(output_content.location):
            raise FileNotFoundError(f"Unknown error: failed to write to {output_content.location}")


###### Concrete Process Implementation
## Process w/ bs4 and filesystem
@main_try_except_wrapper(lgr)
def main_bs4_fs(input_dirname: str, output_dirname: str) -> None:

    abstract_process(
        content_reader=filesystem_content_reader,
        reader_input=input_dirname,
        fix_footnotes=bs_fix_footnotes,
        remove_references=bs_remove_references,
        content_writer=filesystem_content_writer,
        writer_input=output_dirname,
    )


######


###### Interface
## CLI
def cli() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Postprocess HTML files for DLTC web portal")

    parser.add_argument(
        "-i",
        "--input_dirname",
        help="Directory containing HTML files to postprocess.",
        required=True,
    )

    parser.add_argument(
        "-o",
        "--output_dirname",
        help="Directory to write postprocessed HTML files.",
        required=True,
    )

    args = parser.parse_args()

    main_bs4_fs(input_dirname=args.input_dirname, output_dirname=args.output_dirname)


##


###### Script Entry Point
if __name__ == "__main__":
    cli()
######
