"""
Enriched Batch DOI Registration

This is an enhanced version of batch_doi_registration.py that integrates with
the bibliography ODS file to automatically enrich minimal CSV data with full
metadata before DOI registration.

Usage is identical to batch_doi_registration.py, but the CSV can now contain
just 'bibkey' and 'link' columns - all other metadata will be pulled from the
bibliography ODS file configured in BIBLIOGRAPHY_ODS_PATH.

Example CSV (minimal format):
    bibkey,link
    smith-2024-epistemology,https://philosophie.ch/smith-2024-epistemology
    jones-2023-ethics,https://philosophie.ch/jones-2023-ethics

The script will look up each bibkey in the bibliography and extract:
- Authors (parsed from "family, given and family, given" format)
- Title, journal, volume, issue, pages
- Year, publisher, and all other Crossref-relevant metadata
"""

import os
import sys
import csv
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional, Union
from dotenv import load_dotenv

# Import the original batch registration
from src.crossref_doi_api.batch_doi_registration import BatchDOIRegistration
from src.crossref_doi_api.bibliography_enrichment import BibliographyEnricher, enrich_csv_with_bibliography, BIBKEY_COLUMN_NAME


class EnrichedBatchDOIRegistration(BatchDOIRegistration):
    """
    Enhanced batch DOI registration that enriches CSV data with bibliography metadata.

    Inherits from BatchDOIRegistration and adds bibliography lookup capability.
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
        Initialize enriched batch DOI registration.

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

    def _create_enriched_csv(self, input_csv: Union[str, Path], bibkey_column: Optional[str] = None) -> Path:
        """
        Create a temporary enriched CSV file from the input CSV.

        Parameters
        ----------
        input_csv : str or Path
            Original CSV file with minimal data
        bibkey_column : str
            Name of the column containing bibkeys (default: "article_bib_key")

        Returns
        -------
        Path
            Path to temporary enriched CSV file
        """
        if bibkey_column is None:
            bibkey_column = BIBKEY_COLUMN_NAME

        if not self.enricher:
            # No enrichment available, return original
            return Path(input_csv)

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
        except Exception:
            print(f"   ⚠️  Failed to read with {encoding}, trying utf-8...")
            input_df = pl.read_csv(str(input_csv), encoding='utf-8')

        if bibkey_column not in input_df.columns:
            raise ValueError(
                f"CSV must contain bibkey column '{bibkey_column}'. "
                f"Available columns: {list(input_df.columns)}"
            )

        # Enrich each row
        enriched_rows = []
        total = len(input_df)

        for idx, row in enumerate(input_df.iter_rows(named=True)):
            bibkey = row.get(bibkey_column)

            if not bibkey:
                print(f"   ⚠️  Row {idx + 1}: No bibkey, skipping")
                continue

            # Get DOI and link from input row if present
            base_metadata = {}
            if "doi" in row and row["doi"]:
                base_metadata["doi"] = str(row["doi"])
            if "link" in row and row["link"]:
                base_metadata["link"] = str(row["link"])
            if "url" in row and row["url"]:
                base_metadata["link"] = str(row["url"])

            # Enrich with bibliography data
            enriched = self.enricher.enrich_metadata(bibkey, base_metadata=base_metadata)

            if enriched:
                # Map enriched fields to CSV format expected by CSVToXMLConverter
                csv_row = self._map_enriched_to_csv_format(enriched)
                enriched_rows.append(csv_row)

                if (idx + 1) % 10 == 0:
                    print(f"   Processed {idx + 1}/{total} entries")
            else:
                print(f"   ⚠️  Row {idx + 1}: Could not enrich bibkey '{bibkey}'")

        print(f"✅ Enriched {len(enriched_rows)}/{total} entries\n")

        # Create temporary CSV file with enriched data
        temp_csv = Path(tempfile.mktemp(suffix=".csv", prefix="enriched_"))

        # Get fieldnames from first row
        if enriched_rows:
            fieldnames = list(enriched_rows[0].keys())

            with open(temp_csv, 'w', encoding='utf-8', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(enriched_rows)

            print(f"📄 Created enriched CSV: {temp_csv}")

        return temp_csv

    def _map_enriched_to_csv_format(self, enriched: Dict[str, Any]) -> Dict[str, str]:
        """
        Map enriched metadata to the CSV format expected by CSVToXMLConverter.

        Parameters
        ----------
        enriched : Dict[str, Any]
            Enriched metadata from bibliography

        Returns
        -------
        Dict[str, str]
            CSV-formatted row
        """
        csv_row = {}

        # Required fields
        csv_row["doi"] = str(enriched.get("doi", ""))
        csv_row["title"] = str(enriched.get("title", ""))
        csv_row["link"] = str(enriched.get("link", enriched.get("url", "")))
        csv_row["_year"] = str(enriched.get("_year", ""))
        csv_row["author_given_name"] = str(enriched.get("author_given_name", ""))
        csv_row["author_surname"] = str(enriched.get("author_surname", ""))

        # Optional fields
        if "subtitle" in enriched:
            csv_row["subtitle"] = str(enriched["subtitle"])

        if "journal_title" in enriched:
            csv_row["journal_title"] = str(enriched["journal_title"])

        # Use default ISSN if not provided
        csv_row["journal_issn"] = str(enriched.get("journal_issn", "1234-5678"))

        if "volume" in enriched:
            csv_row["volume"] = str(enriched["volume"])

        if "issue" in enriched:
            csv_row["issue"] = str(enriched["issue"])

        if "first_page" in enriched:
            csv_row["first_page"] = str(enriched["first_page"])

        if "last_page" in enriched:
            csv_row["last_page"] = str(enriched["last_page"])

        if "language" in enriched:
            csv_row["language"] = str(enriched["language"])
        else:
            csv_row["language"] = "en"  # Default to English

        # Additional authors as JSON string
        if "additional_authors" in enriched:
            import json

            csv_row["additional_authors"] = json.dumps(enriched["additional_authors"])

        # Publisher info
        if "publisher" in enriched:
            csv_row["publisher"] = str(enriched["publisher"])

        if "publisher_place" in enriched:
            csv_row["publisher_place"] = str(enriched["publisher_place"])

        # Book-specific fields
        if "booktitle" in enriched:
            csv_row["booktitle"] = str(enriched["booktitle"])

        if "series_title" in enriched:
            csv_row["series_title"] = str(enriched["series_title"])

        if "edition" in enriched:
            csv_row["edition"] = str(enriched["edition"])

        return csv_row

    def register_batch(
        self,
        csv_file: Union[str, Path],
        use_sandbox: bool = True,
        check_conflicts: bool = True,
        delay_between_submissions: float = 2.0,
        max_retries: int = 3,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """
        Register DOIs from CSV file with bibliography enrichment.

        This method overrides the parent method to add enrichment step.

        Parameters
        ----------
        csv_file : str or Path
            Input CSV file (can be minimal with just bibkey and link)
        use_sandbox : bool
            Use sandbox environment for testing
        check_conflicts : bool
            Check for existing DOI conflicts before processing
        delay_between_submissions : float
            Seconds to wait between submissions (rate limiting)
        max_retries : int
            Maximum retry attempts per DOI
        dry_run : bool
            If True, generate XML files instead of submitting to Crossref

        Returns
        -------
        Dict[str, Any]
            Detailed results of batch processing
        """
        # Create enriched CSV if enrichment is enabled
        if self.enable_enrichment:
            enriched_csv = self._create_enriched_csv(csv_file)
            # Use enriched CSV for processing
            result = super().register_batch(
                enriched_csv, use_sandbox, check_conflicts, delay_between_submissions, max_retries, dry_run
            )
            # Clean up temporary file if created
            if enriched_csv != Path(csv_file):
                try:
                    enriched_csv.unlink()
                except Exception:
                    pass
            return result
        else:
            # No enrichment, use original method
            return super().register_batch(
                csv_file, use_sandbox, check_conflicts, delay_between_submissions, max_retries, dry_run
            )


def main() -> None:
    """Main entry point for enriched batch DOI registration."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Register DOIs from CSV with automatic bibliography enrichment",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Sandbox testing with minimal CSV (just bibkey + link)
  python batch_doi_registration_enriched.py minimal.csv

  # Production with full enrichment
  python batch_doi_registration_enriched.py data.csv --production

  # Disable enrichment (use full CSV directly)
  python batch_doi_registration_enriched.py full.csv --no-enrichment

  # Dry run to inspect generated XML
  python batch_doi_registration_enriched.py data.csv --dry-run

Environment variables required:
  CROSSREF_USERNAME - Crossref username
  CROSSREF_PASSWORD - Crossref password
  BIBLIOGRAPHY_ODS_PATH - Path to bibliography ODS file (for enrichment)
        """,
    )

    parser.add_argument("csv_file", help="Input CSV file")
    parser.add_argument("--production", action="store_true", help="Use production environment (default: sandbox)")
    parser.add_argument("--delay", type=float, default=3.0, help="Delay between submissions in seconds (default: 3.0)")
    parser.add_argument("--retries", type=int, default=3, help="Max retry attempts (default: 3)")
    parser.add_argument("--no-conflict-check", action="store_true", help="Skip DOI conflict checking")
    parser.add_argument("--dry-run", action="store_true", help="Generate XML files without submitting")
    parser.add_argument("--no-enrichment", action="store_true", help="Disable bibliography enrichment")
    parser.add_argument("--bibliography", type=str, help="Bibliography ODS path (overrides env var)")
    parser.add_argument("--encoding", type=str, help="CSV file encoding (default: auto-detect)")

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

    # Initialize enriched batch registration
    try:
        batch = EnrichedBatchDOIRegistration(
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
    use_sandbox = not args.production
    if not use_sandbox and not args.dry_run:
        print("\n⚠️  WARNING: You are about to register DOIs in PRODUCTION!")
        print("   This will create REAL, PERMANENT DOIs.")
        response = input("   Type 'YES' to continue: ")
        if response != "YES":
            print("Registration cancelled.")
            sys.exit(0)

    # Run batch registration
    try:
        results = batch.register_batch(
            csv_file=args.csv_file,
            use_sandbox=use_sandbox,
            check_conflicts=not args.no_conflict_check,
            delay_between_submissions=args.delay,
            max_retries=args.retries,
            dry_run=args.dry_run,
        )

        # Print summary
        print("\n" + "=" * 60)
        print("REGISTRATION SUMMARY")
        print("=" * 60)
        print(f"Success: {results.get('success', False)}")
        print(f"Total submitted: {results.get('submitted', 0)}")
        print(f"Successful: {results.get('successful', 0)}")
        print(f"Failed: {results.get('failed', 0)}")

        if not results.get('success'):
            error = results.get('error', 'Unknown error')
            print(f"\n❌ Error: {error}")
            sys.exit(1)

    except KeyboardInterrupt:
        print("\n\n⚠️  Registration interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error during registration: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
