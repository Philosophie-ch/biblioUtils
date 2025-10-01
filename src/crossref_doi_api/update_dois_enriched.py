"""
Enriched DOI Update Script

Enhanced version of update_dois.py that integrates with the bibliography ODS file
to automatically enrich DOI update requests with full metadata.

Instead of requiring all fields in the CSV, you can now provide minimal data:
- bibkey: The unique identifier to look up in the bibliography
- link: The new URL for the DOI
- doi: (optional) If not provided, will be looked up from bibliography

All other metadata will be pulled from the bibliography ODS file.

Usage:
    python update_dois_enriched.py updates.csv [options]

Example minimal CSV:
    bibkey,link
    smith-2024-epistemology,https://philosophie.ch/new-url/smith-2024
    jones-2023-ethics,https://philosophie.ch/new-url/jones-2023

The script will look up each bibkey and enrich the data before updating Crossref.
"""

import os
import sys
import csv
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional, Union
from dotenv import load_dotenv
import argparse

# Import the original update functionality
from src.crossref_doi_api.update_dois import DOIUpdater
from src.crossref_doi_api.bibliography_enrichment import BibliographyEnricher, BIBKEY_COLUMN_NAME

# Journal ISSN constants - format: (issn, media_type)
JOURNAL_ISSNS = {
    "Dialectica": ("0012-2017", "print"),  # Print ISSN for Dialectica journal
}


class EnrichedDOIUpdater(DOIUpdater):
    """
    Enhanced DOI updater that enriches CSV data with bibliography metadata.

    Inherits from DOIUpdater and adds bibliography lookup capability.
    """

    def __init__(
        self,
        username: str,
        password: str,
        sandbox_username: Optional[str] = None,
        sandbox_password: Optional[str] = None,
        depositor_name: str = "Philosophie.ch",
        depositor_email: str = "philipp.blum@philosophie.ch",
        bibliography_path: Optional[str] = None,
        enable_enrichment: bool = True,
        csv_encoding: Optional[str] = None,
    ):
        """
        Initialize enriched DOI updater.

        Parameters
        ----------
        username : str
            Crossref production username
        password : str
            Crossref production password
        sandbox_username : str, optional
            Crossref sandbox username (if different)
        sandbox_password : str, optional
            Crossref sandbox password (if different)
        depositor_name : str
            Organization name for XML metadata
        depositor_email : str
            Contact email for XML metadata
        bibliography_path : str, optional
            Path to bibliography ODS file (uses BIBLIOGRAPHY_ODS_PATH env var if not provided)
        enable_enrichment : bool
            Enable bibliography enrichment (default: True)
        csv_encoding : str, optional
            CSV file encoding (default: auto-detect using chardet)
        """
        super().__init__(username, password, sandbox_username, sandbox_password, depositor_name, depositor_email)

        self.enable_enrichment = enable_enrichment
        self.csv_encoding = csv_encoding
        self.enricher = None

        if enable_enrichment:
            try:
                self.enricher = BibliographyEnricher(bibliography_path)
                print(f"✅ Bibliography enrichment enabled")
            except Exception as e:
                print(f"⚠️  Bibliography enrichment disabled: {e}")
                self.enable_enrichment = False

    def _create_enriched_update_csv(self, input_csv: Union[str, Path], bibkey_column: Optional[str] = None) -> Path:
        """
        Create a temporary enriched CSV file from the input CSV for updates.

        Parameters
        ----------
        input_csv : str or Path
            Original CSV file with minimal data (_article_bib_key + link)
        bibkey_column : str
            Name of the column containing bibkeys (default: "_article_bib_key")

        Returns
        -------
        Path
            Path to temporary enriched CSV file
        """
        if bibkey_column is None:
            bibkey_column = BIBKEY_COLUMN_NAME

        if not self.enricher:
            # No enrichment available, but still need to convert to UTF-8 for parent class
            print("\n📄 Converting CSV to UTF-8 (enrichment disabled)...")

            # Detect encoding
            if not hasattr(self, 'csv_encoding') or self.csv_encoding is None:
                import chardet

                with open(input_csv, 'rb') as f:
                    raw_data = f.read(100000)
                    detected = chardet.detect(raw_data)
                    encoding = detected['encoding'] or 'utf-8'
                    confidence = detected['confidence']
                    print(f"   Detected encoding: {encoding} (confidence: {confidence:.0%})")
            else:
                encoding = self.csv_encoding

            # If already UTF-8, return original
            if encoding.lower() in ['utf-8', 'utf8', 'ascii']:
                return Path(input_csv)

            # Convert to UTF-8
            temp_csv = Path(tempfile.mktemp(suffix=".csv", prefix="converted_"))
            input_df = pl.read_csv(str(input_csv), encoding=encoding)
            input_df.write_csv(str(temp_csv))
            print(f"   Converted to UTF-8: {temp_csv}")
            return temp_csv

        print("\n📚 Enriching CSV with bibliography metadata...")

        # Read input CSV
        import polars as pl

        # Detect encoding if not specified
        if not hasattr(self, 'csv_encoding') or self.csv_encoding is None:
            import chardet

            with open(input_csv, 'rb') as f:
                raw_data = f.read(100000)  # Read first 100KB
                detected = chardet.detect(raw_data)
                encoding = detected['encoding'] or 'utf-8'
                confidence = detected['confidence']
                print(f"   Detected encoding: {encoding} (confidence: {confidence:.0%})")
        else:
            encoding = self.csv_encoding

        try:
            input_df = pl.read_csv(str(input_csv), encoding=encoding)
        except Exception as e:
            print(f"   ⚠️  Failed to read with {encoding}, trying utf-8...")
            input_df = pl.read_csv(str(input_csv), encoding='utf-8')

        if bibkey_column not in input_df.columns:
            raise ValueError(
                f"CSV must contain bibkey column '{bibkey_column}'. " f"Available columns: {list(input_df.columns)}"
            )

        # Enrich each row
        enriched_rows = []
        total = len(input_df)

        for idx, row in enumerate(input_df.iter_rows(named=True)):
            bibkey = row.get(bibkey_column)

            if not bibkey:
                print(f"   ⚠️  Row {idx + 1}: No bibkey, skipping")
                continue

            # Get base data from input row
            base_metadata = {}
            if "doi" in row and row["doi"]:
                base_metadata["doi"] = str(row["doi"])
            if "link" in row and row["link"]:
                base_metadata["link"] = str(row["link"])
            if "title" in row and row["title"]:
                base_metadata["title"] = str(row["title"])
            if "assigned_authors" in row and row["assigned_authors"]:
                base_metadata["assigned_authors"] = str(row["assigned_authors"])
            if "update_type" in row and row["update_type"]:
                base_metadata["update_type"] = str(row["update_type"])
            if "update_reason" in row and row["update_reason"]:
                base_metadata["update_reason"] = str(row["update_reason"])

            # Enrich with bibliography data
            enriched = self.enricher.enrich_metadata(bibkey, base_metadata=base_metadata)

            if enriched:
                # Map enriched fields to update CSV format
                csv_row = self._map_enriched_to_update_format(enriched)
                enriched_rows.append(csv_row)

                if (idx + 1) % 10 == 0:
                    print(f"   Processed {idx + 1}/{total} entries")
            else:
                print(f"   ⚠️  Row {idx + 1}: Could not enrich bibkey '{bibkey}'")

        print(f"✅ Enriched {len(enriched_rows)}/{total} entries\n")

        # Create temporary CSV file with enriched data
        temp_csv = Path(tempfile.mktemp(suffix=".csv", prefix="enriched_updates_"))

        # Get fieldnames from first row
        if enriched_rows:
            fieldnames = list(enriched_rows[0].keys())

            with open(temp_csv, 'w', encoding='utf-8', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(enriched_rows)

            print(f"📄 Created enriched update CSV: {temp_csv}")

        return temp_csv

    def _map_enriched_to_update_format(self, enriched: Dict[str, Any]) -> Dict[str, str]:
        """
        Map enriched metadata to the CSV format expected for DOI updates.

        Parameters
        ----------
        enriched : Dict[str, Any]
            Enriched metadata from bibliography

        Returns
        -------
        Dict[str, str]
            CSV-formatted row for updates
        """
        csv_row = {}

        # Required for updates
        # Use existing_doi from bibliography if doi not in base metadata
        csv_row["doi"] = str(enriched.get("doi", enriched.get("existing_doi", "")))
        csv_row["link"] = str(enriched.get("link", enriched.get("url", "")))

        # Update metadata
        csv_row["update_type"] = str(enriched.get("update_type", "full"))
        if "update_reason" in enriched:
            csv_row["update_reason"] = str(enriched["update_reason"])

        # Full metadata for full updates
        if "title" in enriched:
            csv_row["title"] = str(enriched["title"])

        if "_year" in enriched:
            csv_row["_year"] = str(enriched["_year"])

        if "author_given_name" in enriched:
            csv_row["author_given_name"] = str(enriched["author_given_name"])

        if "author_surname" in enriched:
            csv_row["author_surname"] = str(enriched["author_surname"])

        if "journal_title" in enriched:
            csv_row["journal_title"] = str(enriched["journal_title"])

        if "volume" in enriched:
            csv_row["volume"] = str(enriched["volume"])

        if "issue" in enriched:
            csv_row["issue"] = str(enriched["issue"])

        if "first_page" in enriched:
            csv_row["first_page"] = str(enriched["first_page"])

        if "last_page" in enriched:
            csv_row["last_page"] = str(enriched["last_page"])

        # Journal ISSN - look up from journal name if available
        journal_title = enriched.get("journal_title", "")
        if journal_title and journal_title in JOURNAL_ISSNS:
            issn_info = JOURNAL_ISSNS[journal_title]
            csv_row["journal_issn"] = issn_info[0]  # ISSN number
            csv_row["issn_media_type"] = issn_info[1]  # "print" or "electronic"
        else:
            # Fallback if journal not in our mapping
            csv_row["journal_issn"] = enriched.get("journal_issn", "")
            csv_row["issn_media_type"] = "electronic"  # Default to electronic

        # Publication date media type - use "print" for print journals, "online" for electronic
        # This describes the publication medium, not the ISSN type
        csv_row["publication_date_media_type"] = issn_info[1] if journal_title in JOURNAL_ISSNS else "online"

        return csv_row

    def update_dois_from_csv(
        self,
        csv_file: Union[str, Path],
        use_sandbox: bool = True,
        dry_run: bool = False,
        use_csv_metadata: bool = True,
    ) -> Dict[str, Any]:
        """
        Update DOIs from CSV file with bibliography enrichment.

        This method adds enrichment capability to DOI updates.

        Parameters
        ----------
        csv_file : str or Path
            Input CSV file (can be minimal with just bibkey and link)
        use_sandbox : bool
            Use sandbox environment for testing
        dry_run : bool
            If True, only generate and display XML without submitting
        use_csv_metadata : bool
            If True, use enriched metadata from CSV/bibliography

        Returns
        -------
        Dict[str, Any]
            Detailed results of update processing
        """
        # Create enriched CSV if enrichment is enabled
        enriched_csv = csv_file
        if self.enable_enrichment:
            enriched_csv = self._create_enriched_update_csv(csv_file)

        # Process the CSV (enriched or original) using parent's process_updates method
        result = self.process_updates(
            csv_file=enriched_csv,
            use_sandbox=use_sandbox,
            dry_run=dry_run,
            use_csv_metadata=use_csv_metadata,
        )

        # Clean up temporary file if created
        if self.enable_enrichment and enriched_csv != Path(csv_file):
            try:
                Path(enriched_csv).unlink()
            except Exception:
                print(f"⚠️  Could not delete temporary file: {enriched_csv}")

        return result


def main() -> None:
    """Main entry point for enriched DOI updates."""
    parser = argparse.ArgumentParser(
        description="Update DOIs with automatic bibliography enrichment",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Dry run to inspect generated XML
  python update_dois_enriched.py updates.csv --dry-run

  # Sandbox testing with minimal CSV (just bibkey + link)
  python update_dois_enriched.py updates.csv --sandbox

  # Production updates
  python update_dois_enriched.py updates.csv

  # Disable enrichment (use full CSV directly)
  python update_dois_enriched.py updates.csv --no-enrichment

Example minimal CSV:
  bibkey,link
  smith-2024,https://philosophie.ch/smith-2024-new
  jones-2023,https://philosophie.ch/jones-2023-new

Environment variables required:
  CROSSREF_USERNAME - Crossref username
  CROSSREF_PASSWORD - Crossref password
  BIBLIOGRAPHY_ODS_PATH - Path to bibliography ODS file (for enrichment)
        """,
    )

    parser.add_argument("csv_file", help="Input CSV file with DOI updates")
    parser.add_argument("--sandbox", action="store_true", help="Use sandbox environment (default: production)")
    parser.add_argument("--dry-run", action="store_true", help="Generate XML without submitting")
    parser.add_argument("--no-enrichment", action="store_true", help="Disable bibliography enrichment")
    parser.add_argument("--bibliography", type=str, help="Bibliography ODS path (overrides env var)")
    parser.add_argument("--encoding", type=str, help="CSV file encoding (default: auto-detect)")
    parser.add_argument(
        "--use-csv-metadata",
        action="store_true",
        default=True,
        help="Use metadata from CSV (default, recommended for domain migration)",
    )

    args = parser.parse_args()

    # Load credentials
    load_dotenv()
    username = os.getenv("CROSSREF_USERNAME")
    password = os.getenv("CROSSREF_PASSWORD")
    sandbox_username = os.getenv("CROSSREF_SANDBOX_USERNAME")
    sandbox_password = os.getenv("CROSSREF_SANDBOX_PASSWORD")

    if not username or not password:
        print("❌ Error: CROSSREF_USERNAME and CROSSREF_PASSWORD must be set")
        sys.exit(1)

    # Initialize enriched updater
    try:
        updater = EnrichedDOIUpdater(
            username=username,
            password=password,
            sandbox_username=sandbox_username,
            sandbox_password=sandbox_password,
            bibliography_path=args.bibliography,
            enable_enrichment=not args.no_enrichment,
            csv_encoding=args.encoding,
        )
    except Exception as e:
        print(f"❌ Initialization error: {e}")
        sys.exit(1)

    # Confirm production use
    use_sandbox = args.sandbox
    if not use_sandbox and not args.dry_run:
        print("\n⚠️  WARNING: You are about to update DOIs in PRODUCTION!")
        print("   This will modify REAL DOIs permanently.")
        response = input("   Type 'YES' to continue: ")
        if response != "YES":
            print("Update cancelled.")
            sys.exit(0)

    # Run updates
    try:
        results = updater.update_dois_from_csv(
            csv_file=args.csv_file,
            use_sandbox=use_sandbox,
            dry_run=args.dry_run,
            use_csv_metadata=args.use_csv_metadata,
        )

        # Print summary
        print("\n" + "=" * 60)
        print("UPDATE SUMMARY")
        print("=" * 60)
        print(f"Success: {results.get('success', False)}")
        print(f"Total processed: {results.get('total', 0)}")
        print(f"Successful: {results.get('successful', 0)}")
        print(f"Failed: {results.get('failed', 0)}")

        if not results.get('success'):
            error = results.get('error', 'Unknown error')
            print(f"\n❌ Error: {error}")
            sys.exit(1)

    except KeyboardInterrupt:
        print("\n\n⚠️  Update interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error during update: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
