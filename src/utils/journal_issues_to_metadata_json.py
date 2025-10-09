"""
Journal Issues to Metadata JSON CSV Converter

Given a CSV with journal issue entries, extracts metadata and generates a CSV
with bibkey and metadata_json columns.

Output metadata format:
{
    "type": "journal_issue",
    "issn": "1746-8361",
    "volume": "75",
    "issue": "2",
    "year": 2024,
    "license": "CC BY 4.0",
    "language": "en",
    "keywords": [],
    "publication_status": "published"
}

Usage:
    python journal_issues_to_metadata_json.py input.csv output.csv
"""

import argparse
import csv
import json
import os
import re
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv
import polars as pl


# Journal metadata mappings
JOURNAL_ISSN_MAP = {
    "Dialectica": "1746-8361",
}

JOURNAL_LICENSE_MAP = {
    "Dialectica": "",
}

# Language code to ISO 639-1 mapping
LANGUAGE_CODE_TO_ISO_MAP = {
    "en": "en",
    "en-UK": "en",
    "en-US": "en",
    "de": "de",
    "de-DE": "de",
    "fr": "fr",
    "fr-FR": "fr",
    "it": "it",
    "it-IT": "it",
    "es": "es",
    "es-ES": "es",
}


def parse_journal_issue_title(title: str) -> Dict[str, str]:
    """
    Parse journal issue title to extract volume, issue, and year.

    Expected formats:
    - "Dialectica 23(1), 1969"
    - "Dialectica 72(3), 2018"
    - "Journal Name 12(3-4), 2020"

    Parameters
    ----------
    title : str
        Journal issue title

    Returns
    -------
    Dict[str, str]
        Dictionary with 'journal', 'volume', 'issue', 'year'
    """
    result = {'journal': '', 'volume': '', 'issue': '', 'year': ''}

    if not title:
        return result

    # Pattern: "Journal Name Volume(Issue), Year"
    # Examples: "Dialectica 23(1), 1969" or "Dialectica 72(3), 2018"
    pattern = r'^(.+?)\s+(\d+)\(([^)]+)\),\s*(\d{4})$'
    match = re.match(pattern, title.strip())

    if match:
        result['journal'] = match.group(1).strip()
        result['volume'] = match.group(2)
        result['issue'] = match.group(3)
        result['year'] = match.group(4)

    return result


def extract_special_issue_title(lead_text: str) -> str:
    """
    Extract special issue title from lead_text.

    Expected format: 'special issue "Title Here", guest ed. ...'

    Parameters
    ----------
    lead_text : str
        Lead text from CSV

    Returns
    -------
    str
        Special issue title if found, empty string otherwise
    """
    if not lead_text:
        return ''

    # Look for 'special issue' followed by text in quotes
    pattern = r'special issue\s+"([^"]+)"'
    match = re.search(pattern, lead_text, re.IGNORECASE)

    if match:
        return match.group(1).strip()

    return ''


def extract_journal_issue_metadata(row: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Extract metadata from a journal issue CSV row.

    Parameters
    ----------
    row : Dict[str, Any]
        CSV row data

    Returns
    -------
    Optional[Dict[str, Any]]
        Metadata dictionary, or None if parsing fails
    """
    # Parse title to extract volume, issue, year
    title = str(row.get('title', '')) if row.get('title') else ''
    parsed = parse_journal_issue_title(title)

    if not parsed['journal']:
        return None

    journal = parsed['journal']
    volume = parsed['volume']
    issue = parsed['issue']
    year = parsed['year']

    # Parse language code
    language_code = str(row.get('language_code', '')) if row.get('language_code') else ''
    language = LANGUAGE_CODE_TO_ISO_MAP.get(language_code, 'en')

    # Extract publication status from 'published' field
    published = str(row.get('published', '')).lower() if row.get('published') else ''
    publication_status = 'published' if published == 'published' else ''

    # Extract special issue title from lead_text if present
    lead_text = str(row.get('lead_text', '')) if row.get('lead_text') else ''
    special_issue_title = extract_special_issue_title(lead_text)

    # Build metadata
    metadata: Dict[str, Any] = {
        'type': 'journal_issue',
        'issn': JOURNAL_ISSN_MAP.get(journal, ''),
        'volume': volume,
        'issue': issue,
        'year': int(year) if year else '',
        'license': JOURNAL_LICENSE_MAP.get(journal, ''),
        'language': language,
        'keywords': [],
        'publication_status': publication_status,
    }

    # Add title only if it's a special issue
    if special_issue_title:
        metadata['title'] = special_issue_title

    return metadata


def process_input_file(input_path: Path, doi_column: str = 'doi') -> List[Dict[str, Any]]:
    """
    Process input file and generate metadata for each journal issue.

    Parameters
    ----------
    input_path : Path
        Path to input CSV file
    doi_column : str
        Name of the column containing DOIs

    Returns
    -------
    List[Dict[str, Any]]
        List of result dictionaries with DOI, metadata, status, and message
    """
    # Load input file
    print(f"📖 Reading input file: {input_path}")

    if input_path.suffix.lower() == '.ods':
        df = pl.read_ods(str(input_path), has_header=True)
    elif input_path.suffix.lower() == '.csv':
        df = pl.read_csv(str(input_path))
    else:
        raise ValueError(f"Unsupported file format: {input_path.suffix}")

    if doi_column not in df.columns:
        raise ValueError(f"Input file must contain '{doi_column}' column. Found: {list(df.columns)}")

    print(f"   Found {len(df)} entries")

    # Process each row
    results = []
    success_count = 0
    error_count = 0

    for row in df.iter_rows(named=True):
        doi = row.get(doi_column)

        # Handle missing or empty DOI (vacuous success)
        if not doi or str(doi).strip() == '':
            results.append({'doi': '', 'metadata': None, 'status': 'success', 'message': 'Missing DOI'})
            success_count += 1
            continue

        doi_str = str(doi).strip()

        # Try to extract metadata
        try:
            metadata = extract_journal_issue_metadata(row)

            if metadata:
                results.append({'doi': doi_str, 'metadata': metadata, 'status': 'success', 'message': ''})
                success_count += 1
            else:
                results.append(
                    {
                        'doi': doi_str,
                        'metadata': None,
                        'status': 'error',
                        'message': f'Could not parse journal issue title: {row.get("title", "")}',
                    }
                )
                error_count += 1
        except Exception as e:
            # Catch any errors during metadata extraction
            results.append(
                {
                    'doi': doi_str,
                    'metadata': None,
                    'status': 'error',
                    'message': f'Error processing entry: {str(e)}',
                }
            )
            error_count += 1

    print(f"\n✅ Processed {len(results)} entries")
    print(f"   Success: {success_count}")
    print(f"   Errors: {error_count}")

    return results


def main(
    input_file: Path,
    output_file: Path,
    doi_column: str = 'doi',
) -> None:
    """
    Main function to convert journal issue entries to CSV with JSON metadata.

    Parameters
    ----------
    input_file : Path
        Input CSV or ODS file with journal issue data
    output_file : Path
        Output CSV file path
    doi_column : str
        Name of DOI column in input file
    """
    # Process input file
    results = process_input_file(input_file, doi_column)

    # Write output as CSV with DOI, metadata_json, status, and message columns
    print(f"\n💾 Writing output to: {output_file}")
    with open(output_file, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['DOI', 'metadata_json', 'status', 'message'])

        for result in results:
            doi = result['doi']
            status = result['status']
            message = result['message']

            # Convert metadata to compact JSON string (empty string if None)
            if result['metadata'] is None:
                metadata_json = ''
            else:
                metadata_json = json.dumps(result['metadata'], ensure_ascii=False, separators=(',', ':'))

            writer.writerow([doi, metadata_json, status, message])

    print(f"✅ Done! Wrote {len(results)} entries to {output_file}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Convert journal issue entries to CSV with JSON metadata",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage
  python journal_issues_to_metadata_json.py input.csv output.csv

  # Custom DOI column name
  python journal_issues_to_metadata_json.py input.csv output.csv --doi-column my_doi

Output format:
  CSV with four columns:
  - DOI: DOI identifier (same order as input)
  - metadata_json: Compact JSON string with metadata (empty if error)
  - status: "success" or "error"
  - message: Description (e.g., error message or "Missing DOI")
        """,
    )

    parser.add_argument('input_file', type=Path, help='Input CSV or ODS file with journal issue data')
    parser.add_argument('output_file', type=Path, help='Output CSV file')
    parser.add_argument('--doi-column', default='doi', help='Name of DOI column (default: doi)')

    args = parser.parse_args()

    try:
        main(
            input_file=args.input_file,
            output_file=args.output_file,
            doi_column=args.doi_column,
        )
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
