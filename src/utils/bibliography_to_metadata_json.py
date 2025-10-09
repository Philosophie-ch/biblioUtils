"""
Bibliography to Metadata JSON CSV Converter

Given a CSV or ODS file with a 'bibkey' column, looks up each entry in the
bibliography and generates a CSV with two columns:
- bibkey: The bibliography key (in same order as input)
- metadata_json: JSON string with publication metadata

Output CSV format:
bibkey,metadata_json
smith-2021,"{\"type\":\"article\",\"year\":\"2021\",...}"

Usage:
    python bibliography_to_metadata_json.py input.csv output.csv
    python bibliography_to_metadata_json.py input.ods output.csv
"""

import argparse
import csv
import json
import os
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
from dotenv import load_dotenv
import polars as pl

# Import from philch-bib-sdk for parsing
from philoch_bib_sdk.converters.plaintext.bibitem.date_parser import parse_date
from philoch_bib_sdk.converters.plaintext.bibitem.pages_parser import parse_pages as sdk_parse_pages
from philoch_bib_sdk.converters.plaintext.bibitem.parser import (
    _parse_keywords,
    _parse_entry_type,
    _parse_language_id,
    _parse_pubstate,
)
from philoch_bib_sdk.logic.models import TBibString
from aletk.ResultMonad import Ok, Err


# Journal metadata mappings
JOURNAL_ISSN_MAP = {
    "Dialectica": "1746-8361",
}

JOURNAL_LICENSE_MAP = {
    #    "Dialectica": "CC BY 4.0",
    "Dialectica": "",
}

# Language ID to ISO 639-1 code mapping
LANGUAGE_ID_TO_ISO_MAP = {
    "": "",
    "catalan": "ca",
    "czech": "cs",
    "danish": "da",
    "dutch": "nl",
    "english": "en",
    "french": "fr",
    "greek": "el",
    "italian": "it",
    "latin": "la",
    "lithuanian": "lt",
    "ngerman": "de",  # ngerman = German (new German orthography)
    "polish": "pl",
    "portuguese": "pt",
    "romanian": "ro",
    "russian": "ru",
    "slovak": "sk",
    "spanish": "es",
    "swedish": "sv",
    "unknown": "",
}


def parse_pages_to_dict(pages_str: Optional[str]) -> Dict[str, str]:
    """
    Parse page range into start and end pages using SDK parser.

    Parameters
    ----------
    pages_str : Optional[str]
        Page range like "123-145" or "123--145" or single page "123"

    Returns
    -------
    Dict[str, str]
        Dictionary with 'pages', 'start_page', 'end_page'
    """
    result = {'pages': '', 'start_page': '', 'end_page': ''}

    if not pages_str:
        return result

    pages_clean = str(pages_str).strip()
    result['pages'] = pages_clean

    # Try using SDK parser
    try:
        pages_result = sdk_parse_pages(pages_clean)
        if isinstance(pages_result, Ok) and pages_result.value:
            # Get first page range
            first_page_attr = pages_result.value[0]
            result['start_page'] = first_page_attr.start
            result['end_page'] = first_page_attr.end
            return result
    except Exception:
        pass

    # Fallback: manual parsing
    for sep in ['--', '-', '–', '—']:
        if sep in pages_clean:
            parts = pages_clean.split(sep, 1)
            if len(parts) == 2:
                result['start_page'] = parts[0].strip()
                result['end_page'] = parts[1].strip()
                return result

    # Single page
    result['start_page'] = pages_clean
    return result


def extract_year_from_date(date_str: Optional[str]) -> str:
    """
    Extract year from date string using philch-bib-sdk parser.

    Parameters
    ----------
    date_str : Optional[str]
        Date string from bibliography

    Returns
    -------
    str
        Year as string, or empty string if parsing fails
    """
    if not date_str:
        return ''

    try:
        # Parse date using SDK
        result = parse_date(TBibString(str(date_str)))
        if isinstance(result, Ok):
            date_obj = result.value
            if hasattr(date_obj, 'year') and date_obj.year:
                return str(date_obj.year)
        return ''
    except Exception:
        # Fallback: try to extract 4-digit year
        import re

        match = re.search(r'\b(19|20)\d{2}\b', str(date_str))
        if match:
            return match.group(0)
        return ''


def lookup_bibkey_metadata(bibkey: str, bib_df: pl.DataFrame) -> Optional[Dict[str, Any]]:
    """
    Look up a bibkey in the bibliography and extract metadata.

    Parameters
    ----------
    bibkey : str
        Bibliography key to look up
    bib_df : pl.DataFrame
        Bibliography dataframe

    Returns
    -------
    Optional[Dict[str, Any]]
        Metadata dictionary, or None if bibkey not found
    """
    # Find the row with matching bibkey
    matching = bib_df.filter(pl.col('bibkey') == bibkey)

    if len(matching) == 0:
        return None

    row = matching.row(0, named=True)

    # Extract journal name for ISSN and license lookup
    journal = str(row.get('journal', '')) if row.get('journal') else ''

    # Parse entry type using SDK parser
    entry_type_raw = str(row.get('entry_type', '')) if row.get('entry_type') else ''
    entry_type = _parse_entry_type(entry_type_raw.replace("@", "").replace("{", "").strip()).lower()

    # Parse language using SDK parser and convert to ISO 639-1 code (default to 'en' if empty)
    langid_raw = str(row.get('_langid', '')) if row.get('_langid') else ''
    language_id = _parse_language_id(langid_raw) or 'english'
    language = LANGUAGE_ID_TO_ISO_MAP.get(language_id, 'en')

    # Parse keywords from the three keyword level columns
    kw_level1 = str(row.get('_kw-level1', '')).replace(";", "") if row.get('_kw-level1') else ''
    kw_level2 = str(row.get('_kw-level2', '')).replace(";", "") if row.get('_kw-level2') else ''
    kw_level3 = str(row.get('_kw-level3', '')).replace(";", "") if row.get('_kw-level3') else ''

    keywords_list = []
    keywords_attr = _parse_keywords(kw_level1, kw_level2, kw_level3)
    if keywords_attr:
        # Extract keyword names into a list
        if keywords_attr.level_1 and keywords_attr.level_1.name:
            keywords_list.append(keywords_attr.level_1.name)
        if keywords_attr.level_2 and keywords_attr.level_2.name:
            keywords_list.append(keywords_attr.level_2.name)
        if keywords_attr.level_3 and keywords_attr.level_3.name:
            keywords_list.append(keywords_attr.level_3.name)

    # Parse publication status using SDK parser
    pubstate_raw = str(row.get('pubstate', '')) if row.get('pubstate') else ''
    publication_status = _parse_pubstate(pubstate_raw)

    # Parse pages using SDK parser
    if row.get('pages'):
        page_info = parse_pages_to_dict(row.get('pages'))
        pages = page_info['pages']
        start_page = page_info['start_page']
        end_page = page_info['end_page']
    else:
        pages = ''
        start_page = ''
        end_page = ''

    # Extract metadata (keywords at the end)
    metadata: Dict[str, Any] = {
        'type': entry_type,
        'year': extract_year_from_date(row.get('date')),
        'issue': str(row.get('number', '')) if row.get('number') else '',
        'pages': pages,
        'start_page': start_page,
        'end_page': end_page,
        'volume': str(row.get('volume', '')) if row.get('volume') else '',
        'journal': journal,
        'license': JOURNAL_LICENSE_MAP.get(journal, ''),
        'language': language,
        'journal_issn': JOURNAL_ISSN_MAP.get(journal, ''),
        'publication_status': publication_status,
        'keywords': keywords_list,
    }

    return metadata


def process_input_file(input_path: Path, bib_df: pl.DataFrame, bibkey_column: str = 'bibkey') -> List[Dict[str, Any]]:
    """
    Process input file and generate metadata for each bibkey.

    Parameters
    ----------
    input_path : Path
        Path to input CSV or ODS file
    bib_df : pl.DataFrame
        Bibliography dataframe
    bibkey_column : str
        Name of the column containing bibkeys

    Returns
    -------
    List[Dict[str, Any]]
        List of result dictionaries with bibkey, metadata, status, and error_message
    """
    # Load input file
    print(f"📖 Reading input file: {input_path}")

    if input_path.suffix.lower() == '.ods':
        df = pl.read_ods(str(input_path), has_header=True)
    elif input_path.suffix.lower() == '.csv':
        df = pl.read_csv(str(input_path))
    else:
        raise ValueError(f"Unsupported file format: {input_path.suffix}")

    if bibkey_column not in df.columns:
        raise ValueError(f"Input file must contain '{bibkey_column}' column. Found: {list(df.columns)}")

    print(f"   Found {len(df)} entries")

    # Process each bibkey
    results = []
    success_count = 0
    error_count = 0

    for row in df.iter_rows(named=True):
        bibkey = row.get(bibkey_column)

        # Handle missing or empty bibkey (vacuous success)
        if not bibkey or str(bibkey).strip() == '':
            results.append({'bibkey': '', 'metadata': None, 'status': 'success', 'message': 'Missing bibkey'})
            success_count += 1
            continue

        bibkey_str = str(bibkey).strip()

        # Try to lookup metadata
        try:
            metadata = lookup_bibkey_metadata(bibkey_str, bib_df)

            if metadata:
                results.append({'bibkey': bibkey_str, 'metadata': metadata, 'status': 'success', 'message': ''})
                success_count += 1
            else:
                results.append(
                    {
                        'bibkey': bibkey_str,
                        'metadata': None,
                        'status': 'error',
                        'message': f'Bibkey not found in bibliography: {bibkey_str}',
                    }
                )
                error_count += 1
        except Exception as e:
            # Catch any errors during metadata lookup
            results.append(
                {
                    'bibkey': bibkey_str,
                    'metadata': None,
                    'status': 'error',
                    'message': f'Error processing bibkey: {str(e)}',
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
    bibliography_path: Optional[Path] = None,
    bibkey_column: str = 'bibkey',
) -> None:
    """
    Main function to convert bibliography entries to CSV with JSON metadata.

    Parameters
    ----------
    input_file : Path
        Input CSV or ODS file with bibkey column
    output_file : Path
        Output CSV file path
    bibliography_path : Optional[Path]
        Path to bibliography ODS file (uses BIBLIOGRAPHY_ODS_PATH if not provided)
    bibkey_column : str
        Name of bibkey column in input file
    """
    # Load bibliography
    if bibliography_path is None:
        load_dotenv()
        bib_path_str = os.getenv('BIBLIOGRAPHY_ODS_PATH')
        if not bib_path_str:
            raise ValueError(
                "Bibliography path not provided. Set BIBLIOGRAPHY_ODS_PATH environment "
                "variable or use --bibliography argument."
            )
        bibliography_path = Path(bib_path_str)

    if not bibliography_path.exists():
        raise FileNotFoundError(f"Bibliography file not found: {bibliography_path}")

    print(f"📚 Loading bibliography from: {bibliography_path}")
    bib_df = pl.read_ods(str(bibliography_path), has_header=True, drop_empty_rows=True)
    print(f"   Loaded {len(bib_df)} entries")

    # Check for bibkey column
    if 'bibkey' not in bib_df.columns:
        raise ValueError("Bibliography ODS must contain 'bibkey' column")

    # Process input file
    results = process_input_file(input_file, bib_df, bibkey_column)

    # Write output as CSV with bibkey, metadata_json, status, and message columns
    print(f"\n💾 Writing output to: {output_file}")
    with open(output_file, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['bibkey', 'metadata_json', 'status', 'message'])

        for result in results:
            bibkey = result['bibkey']
            status = result['status']
            message = result['message']

            # Convert metadata to compact JSON string (empty string if None)
            if result['metadata'] is None:
                metadata_json = ''
            else:
                metadata_json = json.dumps(result['metadata'], ensure_ascii=False, separators=(',', ':'))

            writer.writerow([bibkey, metadata_json, status, message])

    print(f"✅ Done! Wrote {len(results)} entries to {output_file}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Convert bibliography entries to CSV with JSON metadata",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage
  python bibliography_to_metadata_json.py input.csv output.csv

  # Specify bibliography path
  python bibliography_to_metadata_json.py input.csv output.csv --bibliography /path/to/bib.ods

  # Custom bibkey column name
  python bibliography_to_metadata_json.py input.csv output.csv --bibkey-column my_bibkey

Environment variables:
  BIBLIOGRAPHY_ODS_PATH - Path to bibliography ODS file

Output format:
  CSV with four columns:
  - bibkey: Bibliography key (same order as input)
  - metadata_json: Compact JSON string with metadata (empty if error)
  - status: "success" or "error"
  - message: Description (e.g., error message or "Missing bibkey")
        """,
    )

    parser.add_argument('input_file', type=Path, help='Input CSV or ODS file with bibkey column')
    parser.add_argument('output_file', type=Path, help='Output CSV file')
    parser.add_argument('--bibliography', type=Path, help='Path to bibliography ODS file')
    parser.add_argument('--bibkey-column', default='bibkey', help='Name of bibkey column (default: bibkey)')

    args = parser.parse_args()

    try:
        main(
            input_file=args.input_file,
            output_file=args.output_file,
            bibliography_path=args.bibliography,
            bibkey_column=args.bibkey_column,
        )
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
