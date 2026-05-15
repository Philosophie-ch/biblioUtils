from pypdf import PdfReader, PdfWriter


def merge_pdfs(cover_pdf_path: str, submission_pdf_path: str, output_path: str) -> None:
    writer = PdfWriter()
    for path in [cover_pdf_path, submission_pdf_path]:
        reader = PdfReader(path)
        for page in reader.pages:
            writer.add_page(page)
    with open(output_path, "wb") as f:
        writer.write(f)
