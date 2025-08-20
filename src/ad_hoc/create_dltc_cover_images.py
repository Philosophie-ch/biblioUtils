from pathlib import Path
from aletk.utils import get_logger, lginf
from aletk.ResultMonad import Err, Ok, main_try_except_wrapper
from typing import Dict, Generator, Tuple
from pypdf import PdfReader, PdfWriter
from pdf2image import convert_from_path
from src.ad_hoc.merge_dltc_issue_pdfs import index_files

import tempfile
import os
import logging


file_basename = os.path.basename(__file__)
lgr = get_logger(file_basename)

# Silence pypdf internal warnings
logging.getLogger("pypdf.generic._data_structures").setLevel(logging.ERROR)


type TFileIndex = Dict[str, str]
type TEntryGen = Generator[Tuple[str, str], None, None]  # (stem, file path)


def extract_first_page_pdf(input_pdf: str) -> str | None:
    """
    Extracts the first page from a PDF and writes it to a temporary PDF file.
    Returns the path to the temporary PDF file or None if extraction failed.
    """
    try:
        reader = PdfReader(input_pdf)
        if len(reader.pages) == 0:
            lgr.warning(f"No pages found in PDF: {input_pdf}")
            return None

        writer = PdfWriter()
        writer.add_page(reader.pages[0])

        tmp_fd, tmp_path = tempfile.mkstemp(suffix=".pdf")
        os.close(tmp_fd)  # We only need the path
        with open(tmp_path, "wb") as f:
            writer.write(f)

        return tmp_path

    except Exception as e:
        lgr.warning(f"Failed to extract first page from '{input_pdf}': {e}")
        return None


def convert_pdf_first_page_to_png(input_pdf: str, output_png: str) -> bool:
    """
    Converts the first page of a PDF file to a PNG image.
    Returns True if successful, False otherwise.
    """
    try:
        images = convert_from_path(input_pdf, first_page=1, last_page=1)
        if not images:
            lgr.warning(f"No image rendered from first page of PDF: {input_pdf}")
            return False

        images[0].save(output_png, "PNG")
        return True

    except Exception as e:
        lgr.warning(f"Failed to convert PDF to PNG for '{input_pdf}': {e}")
        return False


@main_try_except_wrapper(lgr)
def main(input_dir: str, output_dir: str) -> None:
    """
    Main function to index PDFs, extract first pages, and convert them to PNG.
    """
    frame = "main"

    lginf(frame, f"Starting PNG conversion from PDFs in '{input_dir}'", lgr)

    pdfs_index = index_files(input_dir, ".pdf")

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    count = 0
    for stem, pdf_path in pdfs_index.items():
        tmp_pdf = extract_first_page_pdf(pdf_path)
        if tmp_pdf is None:
            continue

        out_png = output_path / f"{stem}.png"
        success = convert_pdf_first_page_to_png(tmp_pdf, str(out_png))

        try:
            os.remove(tmp_pdf)
        except Exception as e:
            lgr.warning(f"Failed to delete temporary file '{tmp_pdf}': {e}")

        if success:
            lgr.debug(f"Generated PNG preview: {out_png}")
            count += 1

        if count % 10 == 0 and count > 0:
            lgr.info(f"Processed {count} PDFs so far.")

    lginf(frame, f"Finished processing {count} PDFs", lgr)


def cli() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Generate PNG previews from the first page of PDFs.")

    parser.add_argument(
        "-i",
        "--input-dir",
        type=str,
        help="Directory containing the issue_name PDFs.",
        required=True,
    )

    parser.add_argument(
        "-o",
        "--output-dir",
        type=str,
        help="Directory where the PNG previews will be saved.",
        required=True,
    )

    args = parser.parse_args()

    res = main(args.input_dir, args.output_dir)

    if isinstance(res, Err):
        lgr.error(f"An error occurred: {res.message}\nFull context: {res}")
    else:
        lgr.info("PNG generation completed successfully.")


if __name__ == "__main__":
    cli()
