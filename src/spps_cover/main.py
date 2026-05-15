import argparse
import csv
import os
import shutil
import tempfile
from pathlib import Path

from dotenv import load_dotenv

_ENV_PATH = Path(__file__).parent / ".env"

from aletk.utils import get_logger

from src.spps_cover.alexandria_client import lookup_spps_metadata
from src.spps_cover.base_types import SppsMetadata
from src.spps_cover.html_to_pdf import html_to_pdf
from src.spps_cover.pdf_merge import merge_pdfs
from src.spps_cover.template import render_cover_html

logger = get_logger(__name__)


def generate_spps_pdf(metadata: SppsMetadata, submission_pdf_path: str, output_path: str) -> None:
    cover_pdf_path: str | None = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            cover_pdf_path = tmp.name

        html = render_cover_html(metadata)
        html_to_pdf(html, cover_pdf_path)
        merge_pdfs(cover_pdf_path, submission_pdf_path, output_path)
        logger.info(f"Generated: {output_path}")
    finally:
        if cover_pdf_path and Path(cover_pdf_path).exists():
            Path(cover_pdf_path).unlink()


def _generate_test_cover_pages(output_dir: str) -> None:
    test_entries: list[SppsMetadata] = [
        SppsMetadata(
            title="Disbelieving The Sceptics Without Proving Them Wrong",
            authors=("Philipp Blum",),
            date_year=2008,
            number="20",
            how_to_cite_html=(
                'Blum, Philipp (2008). "Disbelieving The Sceptics Without Proving Them Wrong".'
                " <i>Swiss Philosophical Preprint Series</i>, no. 20."
                ' DOI: <a href="https://doi.org/10.60641/spps020">10.60641/spps020</a>.'
            ),
            license_name="CC BY 3.0",
            license_url="https://creativecommons.org/licenses/by/3.0/",
            copyright_holder="Philipp Blum",
        ),
        SppsMetadata(
            title="Biomacht im Politischen: Kontroversen zwischen Giorgio Agamben und Michel Foucault",
            authors=("Sahra Styger",),
            date_year=2015,
            number="168",
            how_to_cite_html=(
                'Styger, Sahra (2015). "Biomacht im Politischen: Kontroversen zwischen Giorgio Agamben'
                ' und Michel Foucault". <i>Swiss Philosophical Preprint Series</i>, no. 168.'
                ' DOI: <a href="https://doi.org/10.60641/spps168">10.60641/spps168</a>.'
            ),
            license_name="CC BY 3.0",
            license_url="https://creativecommons.org/licenses/by/3.0/",
            copyright_holder="Sahra Styger",
        ),
        SppsMetadata(
            title="Jahresbroschüre 2020: Digitalisierung",
            authors=(
                "Anja Leser",
                "Demian Berger",
                "Till Nessmann",
                "Anna W. von Huber",
                "Carole Berset",
                "Ilaria Fornacciari",
            ),
            date_year=2020,
            number="266",
            how_to_cite_html=(
                "Leser, Anja; Berger, Demian; Nessmann, Till; von Huber, Anna W.; Berset, Carole;"
                ' Fornacciari, Ilaria (2020). "Jahresbroschüre 2020: Digitalisierung".'
                " <i>Swiss Philosophical Preprint Series</i>, no. 266."
                ' DOI: <a href="https://doi.org/10.60641/spps266">10.60641/spps266</a>.'
            ),
            license_name="CC BY 3.0",
            license_url="https://creativecommons.org/licenses/by/3.0/",
            copyright_holder="Anja Leser, Demian Berger, Till Nessmann, Anna W. von Huber, Carole Berset, Ilaria Fornacciari",
        ),
    ]

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    for i, meta in enumerate(test_entries, 1):
        cover_pdf_path: str | None = None
        try:
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                cover_pdf_path = tmp.name

            html = render_cover_html(meta)
            html_to_pdf(html, cover_pdf_path)

            final_path = str(out / f"test_cover_{i}.pdf")
            shutil.move(cover_pdf_path, final_path)
            cover_pdf_path = None
            logger.info(f"Test cover page {i}/3: {final_path}")
        finally:
            if cover_pdf_path and Path(cover_pdf_path).exists():
                Path(cover_pdf_path).unlink()

    logger.info(f"3 test cover pages written to {out}")


def cli() -> int:
    load_dotenv(_ENV_PATH)

    parser = argparse.ArgumentParser(
        description="Generate SPPS cover pages and prepend them to submission PDFs.",
    )
    parser.add_argument("csv_file", nargs="?", help="Input CSV (expects 'bibkey' and 'pdf1_asset' columns)")
    parser.add_argument(
        "--api-url", default=os.getenv("ALEXANDRIA_API_URL", "http://localhost:8080"), help="Alexandria Nexus base URL"
    )
    parser.add_argument("--api-key", default=os.getenv("ALEXANDRIA_API_KEY", ""), help="Alexandria Nexus API key")
    parser.add_argument(
        "--assets-dir",
        default=os.getenv("SPPS_ASSETS_DIR", ""),
        help="Base directory where pdf1_asset paths are resolved (or SPPS_ASSETS_DIR env var)",
    )
    parser.add_argument(
        "--output-dir",
        default=os.getenv("SPPS_OUTPUT_DIR", ""),
        help="Output directory for generated PDFs (or SPPS_OUTPUT_DIR env var)",
    )
    parser.add_argument(
        "-t", "--test", action="store_true", help="Generate 3 test cover pages with sample data (no API/CSV needed)"
    )
    parser.add_argument(
        "--test-output-dir",
        default=os.getenv("SPPS_TEST_OUTPUT_DIR", "data/test_covers"),
        help="Output directory for test cover pages (default: data/test_covers, or SPPS_TEST_OUTPUT_DIR env var)",
    )

    args = parser.parse_args()

    if args.test:
        logger.info("Generating test cover pages...")
        _generate_test_cover_pages(args.test_output_dir)
        return 0

    if not args.csv_file:
        parser.error("csv_file is required (unless using --test / -t)")

    if not args.api_key:
        logger.error("API key required. Set ALEXANDRIA_API_KEY in .env or pass --api-key.")
        return 1

    if not args.assets_dir:
        logger.error("Assets dir required. Set SPPS_ASSETS_DIR in .env or pass --assets-dir.")
        return 1

    if not args.output_dir:
        logger.error("Output dir required. Set SPPS_OUTPUT_DIR in .env or pass --output-dir.")
        return 1

    assets_dir = Path(args.assets_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    csv_path = Path(args.csv_file)
    if not csv_path.exists():
        logger.error(f"CSV file not found: {csv_path}")
        return 1

    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row_num, row in enumerate(reader, start=2):
            bibkey = row.get("bibkey", "").strip()
            pdf1_asset = row.get("pdf1_asset", "").strip()

            if not bibkey:
                logger.warning(f"Row {row_num}: missing bibkey, skipping")
                continue

            if not pdf1_asset or pdf1_asset == "empty":
                logger.warning(f"Row {row_num} ({bibkey}): no pdf1_asset, skipping")
                continue

            submission_pdf = assets_dir / pdf1_asset
            if not submission_pdf.exists():
                logger.error(f"Row {row_num} ({bibkey}): submission PDF not found: {submission_pdf}")
                continue

            output_pdf = output_dir / Path(pdf1_asset).name

            try:
                logger.info(f"Row {row_num}: looking up {bibkey}...")
                metadata = lookup_spps_metadata(args.api_url, bibkey, args.api_key)
                generate_spps_pdf(metadata, str(submission_pdf), str(output_pdf))
            except Exception as e:
                logger.error(f"Row {row_num} ({bibkey}): {e}")

    return 0


if __name__ == "__main__":
    raise SystemExit(cli())
