"""
Parse Crossref Submission Status XML and Update Entry CSV

This script parses Crossref submission status XML files and updates
a bibliographic entry CSV with submission status and error messages.

It matches records by DOI and updates the status and error_message
columns in the entry data CSV file directly.

Usage:
    python parse_submission_status.py status.xml data.csv [options]

Example:
    python parse_submission_status.py \\
        submission_status_philosophie-update-20251008-103303664314_20251008_104646.xml \\
        src/crossref_doi_api/data.csv
"""

import argparse
import csv
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, Optional, Tuple


def parse_submission_status_xml(xml_path: Path) -> Dict[str, Tuple[str, Optional[str]]]:
    """
    Parse Crossref submission status XML and extract DOI status information.

    Parameters
    ----------
    xml_path : Path
        Path to the XML status file

    Returns
    -------
    Dict[str, Tuple[str, Optional[str]]]
        Dictionary mapping DOI -> (status, error_message)
        status is "success" or "error"
        error_message is None for successful records, error text for errors
    """
    print(f"📖 Parsing submission status XML: {xml_path}")

    tree = ET.parse(xml_path)
    root = tree.getroot()

    # Dictionary to store results: doi -> (status, error_message)
    results: Dict[str, Tuple[str, Optional[str]]] = {}

    # Find all record_diagnostic elements
    for record in root.findall('.//record_diagnostic'):
        status_attr = record.get('status', '')
        doi_elem = record.find('doi')
        msg_elem = record.find('msg')

        if doi_elem is not None and doi_elem.text:
            doi = doi_elem.text.strip()

            if status_attr.lower() == 'success':
                results[doi] = ('success', None)
            else:  # Failure or any other status
                error_msg = msg_elem.text.strip() if msg_elem is not None and msg_elem.text else "Unknown error"
                results[doi] = ('error', error_msg)

    success_count = sum(1 for status, _ in results.values() if status == 'success')
    error_count = len(results) - success_count
    print(f"   Parsed {len(results)} records: {success_count} success, {error_count} error")

    return results


def detect_csv_encoding(csv_path: Path) -> str:
    """
    Detect CSV file encoding by checking BOM.

    Parameters
    ----------
    csv_path : Path
        Path to CSV file

    Returns
    -------
    str
        Detected encoding ('utf-16-le', 'utf-8-sig', or 'utf-8')
    """
    with open(csv_path, 'rb') as f:
        bom = f.read(3)

    if bom[:2] == b'\xff\xfe':
        return 'utf-16-le'
    elif bom[:3] == b'\xef\xbb\xbf':
        return 'utf-8-sig'
    else:
        return 'utf-8'


def update_csv_with_status(
    csv_path: Path,
    status_data: Dict[str, Tuple[str, Optional[str]]],
    doi_column: str = 'doi',
    status_column: str = 'status',
    error_column: str = 'error_message',
) -> Tuple[int, int, int]:
    """
    Update CSV file with submission status information in place.

    Parameters
    ----------
    csv_path : Path
        Path to CSV file (will be updated in place)
    status_data : Dict[str, Tuple[str, Optional[str]]]
        Dictionary mapping DOI -> (status, error_message)
    doi_column : str
        Name of DOI column in CSV
    status_column : str
        Name of status column to update
    error_column : str
        Name of error_message column to update

    Returns
    -------
    Tuple[int, int, int]
        (total_rows, updated_rows, not_found_rows)
    """
    # Detect encoding
    encoding = detect_csv_encoding(csv_path)
    print(f"\n📄 Reading CSV with encoding: {encoding}")

    # Read all rows
    with open(csv_path, 'r', encoding=encoding, newline='') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames

        if not fieldnames:
            raise ValueError("CSV file has no headers")

        if doi_column not in fieldnames:
            raise ValueError(f"CSV does not contain '{doi_column}' column. Available: {list(fieldnames)}")

        # Ensure status and error columns exist
        fieldnames = list(fieldnames)
        if status_column not in fieldnames:
            fieldnames.append(status_column)
        if error_column not in fieldnames:
            fieldnames.append(error_column)

        rows = list(reader)

    print(f"   Read {len(rows)} rows")

    # Update rows
    updated_count = 0
    not_found_count = 0

    for row in rows:
        doi = row.get(doi_column, '').strip()

        if doi and doi in status_data:
            status, error_msg = status_data[doi]
            row[status_column] = status
            row[error_column] = error_msg if error_msg else ''
            updated_count += 1
        elif doi and doi not in status_data:
            # DOI exists in CSV but not in status XML - mark as not found
            not_found_count += 1

    # Write updated CSV back (always UTF-8)
    print(f"\n💾 Writing updated CSV to: {csv_path}")

    with open(csv_path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"   ✅ Updated {updated_count} rows")
    if not_found_count > 0:
        print(f"   ⚠️  {not_found_count} DOIs in CSV not found in status XML")

    return len(rows), updated_count, not_found_count


def main(
    xml_file: Path,
    csv_file: Path,
    doi_column: str = 'doi',
    status_column: str = 'status',
    error_column: str = 'error_message',
) -> Dict[str, int]:
    """
    Main function for parsing submission status and updating CSV.

    Parameters
    ----------
    xml_file : Path
        Crossref submission status XML file
    csv_file : Path
        Bibliography entry CSV file (will be updated in place)
    doi_column : str
        Name of DOI column (default: doi)
    status_column : str
        Name of status column (default: status)
    error_column : str
        Name of error column (default: error_message)

    Returns
    -------
    Dict[str, int]
        Dictionary with summary statistics
    """
    # Validate input files
    if not xml_file.exists():
        raise FileNotFoundError(f"XML file not found: {xml_file}")

    if not csv_file.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_file}")

    # Parse XML
    status_data = parse_submission_status_xml(xml_file)

    if not status_data:
        print("⚠️  No records found in XML file")
        return {}

    # Update CSV in place
    total, updated, not_found = update_csv_with_status(csv_file, status_data, doi_column, status_column, error_column)

    # Calculate summary
    success_count = sum(1 for status, _ in status_data.values() if status == 'success')
    error_count = len(status_data) - success_count

    return {
        'total_csv_rows': total,
        'updated_rows': updated,
        'not_found_rows': not_found,
        'success_count': success_count,
        'error_count': error_count,
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Parse Crossref submission status XML and update entry CSV",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Update CSV in place with status from XML
  python parse_submission_status.py status.xml data.csv

  # Use custom column names
  python parse_submission_status.py status.xml data.csv \\
      --doi-column my_doi_field \\
      --status-column submission_status \\
      --error-column submission_error
        """,
    )

    parser.add_argument('xml_file', type=Path, help='Crossref submission status XML file')
    parser.add_argument('csv_file', type=Path, help='Bibliography entry CSV file')
    parser.add_argument('--doi-column', default='doi', help='Name of DOI column (default: doi)')
    parser.add_argument('--status-column', default='status', help='Name of status column (default: status)')
    parser.add_argument('--error-column', default='error_message', help='Name of error column (default: error_message)')

    args = parser.parse_args()

    try:
        # Call main function
        results = main(
            xml_file=args.xml_file,
            csv_file=args.csv_file,
            doi_column=args.doi_column,
            status_column=args.status_column,
            error_column=args.error_column,
        )

        # Print summary
        print("\n" + "=" * 60)
        print("SUMMARY")
        print("=" * 60)
        print(f"Total CSV rows: {results['total_csv_rows']}")
        print(f"Updated rows: {results['updated_rows']}")
        if results['not_found_rows'] > 0:
            print(f"DOIs not in status XML: {results['not_found_rows']}")

        print(f"\nCrossref submission results:")
        print(f"  ✅ Success: {results['success_count']}")
        print(f"  ❌ Error: {results['error_count']}")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
