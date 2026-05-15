import weasyprint


def html_to_pdf(html_content: str, output_path: str) -> None:
    doc = weasyprint.HTML(string=html_content)
    doc.write_pdf(output_path)
