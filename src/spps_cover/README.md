# SPPS Cover Page Generator

Generates cover pages for the **Swiss Philosophical Preprint Series** (SPPS) and prepends them to submission PDFs.

## How it works

1. Reads a CSV with `bibkey` and `pdf1_asset` columns
2. Looks up publication metadata from Alexandria Nexus (title, authors, year, number, citation)
3. Renders an HTML cover page (Jinja2 template, STIX Two Text font, philosophie.ch logo)
4. Converts HTML to PDF via WeasyPrint
5. Prepends the cover page to the submission PDF via pypdf

## Setup

Copy `.env.example` to `.env` and fill in:

```
ALEXANDRIA_API_URL=http://localhost:8080
ALEXANDRIA_API_KEY=your_api_key
SPPS_ASSETS_DIR=/path/to/base/dir     # parent of the pdf1_asset paths
SPPS_OUTPUT_DIR=/path/to/output        # where final PDFs go
SPPS_TEST_OUTPUT_DIR=data/test_covers  # where test covers go
```

## Usage

### Generate cover pages from CSV

```bash
.venv/bin/python -m src.spps_cover.main data/spps.csv
```

The CSV must have `bibkey` and `pdf1_asset` columns. Rows with empty or `"empty"` `pdf1_asset` are skipped.

### Generate test cover pages (no API needed)

```bash
.venv/bin/python -m src.spps_cover.main -t
```

Produces 3 sample covers with hardcoded data in `SPPS_TEST_OUTPUT_DIR`.

## Module structure

| File | Purpose |
|------|---------|
| `main.py` | CLI, CSV processing, orchestration |
| `alexandria_client.py` | Alexandria Nexus API client (metadata lookup) |
| `template.py` | Jinja2 HTML template with embedded fonts and logo |
| `html_to_pdf.py` | WeasyPrint wrapper |
| `pdf_merge.py` | pypdf cover + submission merge |
| `base_types.py` | `SppsMetadata` dataclass, ISSN, license policy |
| `assets/` | Logo SVG, STIX Two Text TTF fonts |

## Notes

- ISSN: `1662-937X`
- License: CC BY 3.0 for publications before 2026, CC BY 4.0 from 2026 onward
- Authors are ordered by their `position` field in Alexandria
- DOI links use the philosophie.ch brand blue (`#337ab7`)
