"""
Bibliography Metadata Enrichment

This module provides functionality to enrich minimal CSV data with metadata
from a full bibliography ODS file. It handles bibkey lookup, field extraction,
and author parsing using the philch-bib-sdk library.

The enrichment process:
1. Loads the bibliography ODS file (configured via BIBLIOGRAPHY_ODS_PATH)
2. For each bibkey in the input CSV, looks up the corresponding row
3. Extracts and transforms Crossref-relevant fields
4. Parses author strings into structured format
5. Returns enriched metadata ready for Crossref XML generation
"""

import os
from pathlib import Path
from typing import Dict, Any, List, Optional, Union, Tuple, Literal
import polars as pl
from dotenv import load_dotenv

# Import author parser from philch-bib-sdk (required dependency)
from philoch_bib_sdk.converters.plaintext.author.parser import parse_author
from philoch_bib_sdk.converters.plaintext.bibitem.date_parser import parse_date
from philoch_bib_sdk.logic.models import TBibString, Author, BibItemDateAttr
from aletk.ResultMonad import Ok, Err

# Load environment variables first
load_dotenv()

# Configuration constants
BIBKEY_COLUMN_NAME = os.getenv("BIBKEY_COLUMN_NAME", "bibkey")

JSONValue = Union[str, int, float, bool, None, Dict[str, Any], List[Any]]
JSONObject = Dict[str, JSONValue]


class BibliographyEnricher:
    """Handle bibliography metadata lookup and enrichment."""

    def __init__(self, bibliography_path: Optional[str] = None, authors_csv_path: Optional[str] = None):
        """
        Initialize the bibliography enricher.

        Parameters
        ----------
        bibliography_path : str, optional
            Path to the bibliography ODS file. If not provided, will try to
            load from BIBLIOGRAPHY_ODS_PATH environment variable.
        authors_csv_path : str, optional
            Path to the authors CSV file. If not provided, will try to
            load from AUTHORS_CSV_PATH environment variable.
        """
        if bibliography_path is None:
            load_dotenv()
            bibliography_path = os.getenv("BIBLIOGRAPHY_ODS_PATH")

        if not bibliography_path:
            raise ValueError(
                "Bibliography path not provided. Set BIBLIOGRAPHY_ODS_PATH environment "
                "variable or pass bibliography_path parameter."
            )

        self.bibliography_path = Path(bibliography_path)
        if not self.bibliography_path.exists():
            raise FileNotFoundError(f"Bibliography file not found: {self.bibliography_path}")

        print(f"📚 Loading bibliography from: {self.bibliography_path}")
        self.df = pl.read_ods(str(self.bibliography_path), has_header=True, drop_empty_rows=True, infer_schema_length=0)
        print(f"   Loaded {len(self.df)} entries")

        # Check for bibkey column
        if "bibkey" not in self.df.columns:
            raise ValueError("Bibliography ODS must contain 'bibkey' column")

        # Load authors CSV if provided
        if authors_csv_path is None:
            authors_csv_path = os.getenv("AUTHORS_CSV_PATH")

        self.authors_df: Optional[pl.DataFrame] = None
        if authors_csv_path:
            authors_path = Path(authors_csv_path)
            if authors_path.exists():
                try:
                    print(f"👥 Loading authors from: {authors_path}")
                    # Only load the columns we need, ignore schema inference issues
                    self.authors_df = pl.read_csv(
                        str(authors_path), ignore_errors=True, infer_schema_length=0  # Treat all columns as strings
                    )
                    print(f"   Loaded {len(self.authors_df)} authors")

                    # Check for required columns
                    required_cols = ["login", "firstname", "lastname"]
                    missing = [col for col in required_cols if col not in self.authors_df.columns]
                    if missing:
                        print(f"⚠️  Authors CSV missing columns: {missing}")
                        self.authors_df = None
                except Exception as e:
                    print(f"⚠️  Error loading authors CSV: {e}")
                    self.authors_df = None
            else:
                print(f"⚠️  Authors CSV not found: {authors_path}")

    def lookup_bibkey(self, bibkey: str) -> Optional[Dict[str, Any]]:
        """
        Look up a bibkey in the bibliography and return the row as a dictionary.

        Parameters
        ----------
        bibkey : str
            The unique bibkey to look up

        Returns
        -------
        Optional[Dict[str, Any]]
            Dictionary of field values, or None if bibkey not found
        """
        matches = self.df.filter(pl.col("bibkey") == bibkey)

        if len(matches) == 0:
            return None

        if len(matches) > 1:
            print(f"⚠️  Warning: Multiple entries found for bibkey '{bibkey}'. Using first match.")

        # Convert first row to dictionary
        row_dict = matches.row(0, named=True)
        return row_dict

    def lookup_author(self, login: str) -> Optional[Dict[str, str]]:
        """
        Look up an author by login and return clean firstname/lastname.

        Parameters
        ----------
        login : str
            The author login/key to look up

        Returns
        -------
        Optional[Dict[str, str]]
            Dictionary with 'given_name' and 'surname' keys, or None if not found
        """
        if self.authors_df is None:
            return None

        matches = self.authors_df.filter(pl.col("login") == login)

        if len(matches) == 0:
            return None

        row = matches.row(0, named=True)
        return {"given_name": str(row.get("firstname", "")), "surname": str(row.get("lastname", ""))}

    def lookup_authors_from_keys(self, author_keys: str) -> List[Dict[str, str]]:
        """
        Look up multiple authors from comma-separated author keys.

        Parameters
        ----------
        author_keys : str
            Comma-separated list of author login keys

        Returns
        -------
        List[Dict[str, str]]
            List of author dictionaries with 'given_name' and 'surname' keys
        """
        if not author_keys or not author_keys.strip():
            return []

        authors = []
        keys = [k.strip() for k in author_keys.split(",") if k.strip()]

        for key in keys:
            author = self.lookup_author(key)
            if author:
                authors.append(author)

        return authors

    def parse_authors(self, author_string: str) -> List[Dict[str, str]]:
        """
        Parse author string using philch-bib-sdk parser.

        Parameters
        ----------
        author_string : str
            Author string in format "family, given and family, given"

        Returns
        -------
        List[Dict[str, str]]
            List of author dictionaries with 'given_name' and 'surname' keys
        """
        if not author_string or author_string.strip() == "":
            return []

        try:
            # TBibString is Literal["latex", "unicode", "simplified"], not an enum with .raw
            result: Union[Ok[Tuple[Author, ...]], Err] = parse_author(author_string, "simplified")

            if isinstance(result, Ok):
                authors: Tuple[Author, ...] = result.out
                parsed_authors = []

                for author in authors:
                    # Extract from BibStringAttr objects (use simplified form)
                    given_name = str(author.given_name.simplified) if author.given_name.simplified else ""
                    family_name = str(author.family_name.simplified) if author.family_name.simplified else ""
                    mononym = str(author.mononym.simplified) if author.mononym.simplified else ""

                    if mononym:
                        # For mononyms, use as surname
                        parsed_authors.append({"given_name": "", "surname": mononym})
                    else:
                        parsed_authors.append({"given_name": given_name, "surname": family_name})

                return parsed_authors
            elif isinstance(result, Err):
                print(f"⚠️  Author parsing error: {result.message if hasattr(result, 'message') else 'Unknown error'}")
                return self._parse_authors_fallback(author_string)
            else:
                return self._parse_authors_fallback(author_string)

        except Exception as e:
            print(f"⚠️  Exception parsing authors '{author_string}': {e}")
            return self._parse_authors_fallback(author_string)

    def _parse_authors_fallback(self, author_string: str) -> List[Dict[str, str]]:
        """
        Fallback author parsing if philch-bib-sdk is not available.

        Parameters
        ----------
        author_string : str
            Author string in format "family, given and family, given"

        Returns
        -------
        List[Dict[str, str]]
            List of author dictionaries
        """
        authors = []
        parts = author_string.split(" and ")

        for part in parts:
            part = part.strip()
            if "," in part:
                surname, given = part.split(",", 1)
                authors.append({"given_name": given.strip(), "surname": surname.strip()})
            else:
                # No comma, assume mononym or surname only
                authors.append({"given_name": "", "surname": part.strip()})

        return authors

    def parse_pages(self, pages_string: Optional[str]) -> Tuple[str, str]:
        """
        Parse page range into first and last page.

        Parameters
        ----------
        pages_string : str, optional
            Page range like "123-145" or "123--145"

        Returns
        -------
        Tuple[str, str]
            (first_page, last_page) - empty strings if not parseable
        """
        if not pages_string:
            return ("", "")

        pages_string = str(pages_string).strip()

        # Handle double dash (common in LaTeX)
        if "--" in pages_string:
            parts = pages_string.split("--", 1)
        elif "-" in pages_string:
            parts = pages_string.split("-", 1)
        else:
            # Single page
            return (pages_string, pages_string)

        if len(parts) == 2:
            return (parts[0].strip(), parts[1].strip())

        return ("", "")

    def enrich_metadata(self, bibkey: str, base_metadata: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """
        Enrich metadata for a bibkey by looking up the bibliography.

        Parameters
        ----------
        bibkey : str
            The bibkey to look up
        base_metadata : Dict[str, Any], optional
            Base metadata from CSV (will be merged with enriched data)

        Returns
        -------
        Optional[Dict[str, Any]]
            Enriched metadata dictionary ready for Crossref XML generation,
            or None if bibkey not found
        """
        bib_row = self.lookup_bibkey(bibkey)

        if bib_row is None:
            print(f"❌ Bibkey '{bibkey}' not found in bibliography")
            return None

        # Start with base metadata if provided
        enriched = base_metadata.copy() if base_metadata else {}
        enriched["bibkey"] = bibkey

        # Extract and transform fields from bibliography

        # Title - only use from bibliography if not already in base metadata (CSV takes precedence)
        if "title" not in enriched and bib_row.get("title"):
            enriched["title"] = str(bib_row["title"])

        # Year - extract from date field using SDK parser
        date_field = bib_row.get("date")
        if date_field is not None and date_field != "":
            try:
                # Use SDK's parse_date to properly parse the date string
                date_result: Union[Ok[Union[BibItemDateAttr, Literal["no date"]]], Err] = parse_date(str(date_field))

                if isinstance(date_result, Ok):
                    date_value = date_result.out
                    # Check if we got a BibItemDateAttr (not "no date")
                    if isinstance(date_value, BibItemDateAttr):
                        enriched["_year"] = date_value.year
                    elif date_value != "no date":
                        # Fallback: try direct conversion
                        enriched["_year"] = int(str(date_field))
                elif isinstance(date_result, Err):
                    print(
                        f"⚠️  Could not parse date '{date_field}': {date_result.message if hasattr(date_result, 'message') else 'Unknown error'}"
                    )
            except Exception as e:
                print(f"⚠️  Exception parsing date '{date_field}': {e}")

        # Authors - prefer assigned_authors from base_metadata (CSV), then fall back to bibliography
        assigned_authors = enriched.get("assigned_authors", "")
        parsed_authors: List[Dict[str, str]] = []
        if assigned_authors and self.authors_df is not None:
            parsed_authors = self.lookup_authors_from_keys(str(assigned_authors))

        if not parsed_authors:
            author_string = bib_row.get("author", "")
            if author_string:
                parsed_authors = self.parse_authors(str(author_string))
            elif bib_row.get("editor"):
                parsed_authors = self.parse_authors(str(bib_row["editor"]))
                enriched["contributor_role"] = "editor"

        if not parsed_authors:
            raise ValueError(
                f"Bibkey '{bibkey}': no author data found from assigned_authors, bibliography author, or editor fields"
            )

        enriched["author_given_name"] = parsed_authors[0]["given_name"]
        enriched["author_surname"] = parsed_authors[0]["surname"]
        if len(parsed_authors) > 1:
            enriched["additional_authors"] = [
                {"given_name": a["given_name"], "surname": a["surname"]} for a in parsed_authors[1:]
            ]

        # Journal metadata
        if bib_row.get("journal"):
            enriched["journal_title"] = str(bib_row["journal"])

        if bib_row.get("volume"):
            enriched["volume"] = str(bib_row["volume"])

        if bib_row.get("number"):
            enriched["issue"] = str(bib_row["number"])

        # Pages
        if bib_row.get("pages"):
            first_page, last_page = self.parse_pages(bib_row["pages"])
            if first_page:
                enriched["first_page"] = first_page
            if last_page:
                enriched["last_page"] = last_page

        # Electronic ID
        if bib_row.get("eid"):
            enriched["eid"] = str(bib_row["eid"])

        # URL and DOI
        if bib_row.get("url"):
            enriched["url"] = str(bib_row["url"])

        if bib_row.get("doi"):
            enriched["existing_doi"] = str(bib_row["doi"])

        # Publisher
        if bib_row.get("publisher"):
            enriched["publisher"] = str(bib_row["publisher"])

        if bib_row.get("address"):
            enriched["publisher_place"] = str(bib_row["address"])

        # Book-specific fields
        if bib_row.get("booktitle"):
            enriched["booktitle"] = str(bib_row["booktitle"])

        if bib_row.get("series"):
            enriched["series_title"] = str(bib_row["series"])

        if bib_row.get("edition"):
            enriched["edition"] = str(bib_row["edition"])

        # Academic works
        if bib_row.get("school"):
            enriched["institution_name"] = str(bib_row["school"])

        if bib_row.get("institution"):
            enriched["institution_name"] = str(bib_row["institution"])

        if bib_row.get("type"):
            enriched["degree"] = str(bib_row["type"])

        langid = bib_row.get("_langid")
        if langid and str(langid) not in ("None", ""):
            iso_code = _BABEL_TO_ISO.get(str(langid), str(langid))
            enriched["language"] = iso_code
        elif "language" not in enriched:
            enriched["language"] = "en"

        # Entry type
        if bib_row.get("entry_type"):
            enriched["entry_type"] = str(bib_row["entry_type"])

        # Special issue metadata
        if bib_row.get("_issuetitle"):
            enriched["special_issue_title"] = str(bib_row["_issuetitle"])

        if bib_row.get("_guesteditor"):
            enriched["guest_editor"] = str(bib_row["_guesteditor"])

        return enriched


_BABEL_TO_ISO = {
    "english": "en",
    "american": "en",
    "british": "en",
    "UKenglish": "en",
    "USenglish": "en",
    "french": "fr",
    "francais": "fr",
    "ngerman": "de",
    "german": "de",
    "austrian": "de",
    "naustrian": "de",
    "nswissgerman": "de",
    "swissgerman": "de",
    "italian": "it",
    "spanish": "es",
    "portuguese": "pt",
    "brazilian": "pt",
    "dutch": "nl",
    "latin": "la",
    "greek": "el",
    "polutonikogreek": "el",
    "russian": "ru",
    "catalan": "ca",
}


class AlexandriaEnricher:
    """Enrich metadata via the Alexandria Nexus REST API instead of ODS file."""

    def __init__(self, api_url: Optional[str] = None, api_key: Optional[str] = None):
        load_dotenv()
        self.api_url = (api_url or os.getenv("ALEXANDRIA_API_URL") or "").rstrip("/")
        self.api_key = api_key or os.getenv("ALEXANDRIA_API_KEY", "")

        if not self.api_url:
            raise ValueError("Alexandria API URL not provided. Set ALEXANDRIA_API_URL or pass api_url.")
        if not self.api_key:
            raise ValueError("Alexandria API key not provided. Set ALEXANDRIA_API_KEY or pass api_key.")

        self._journal_cache: Dict[str, Dict[str, Any]] = {}
        print(f"📚 Using Alexandria Nexus at: {self.api_url}")

    def _headers(self) -> Dict[str, str]:
        return {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

    def _get(self, path: str) -> Any:
        import requests

        resp = requests.get(f"{self.api_url}{path}", headers=self._headers(), timeout=30)
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return resp.json()

    def lookup_bibkey(self, bibkey: str) -> Optional[Dict[str, Any]]:
        result: Optional[Dict[str, Any]] = self._get(f"/api/v1/bibitems/by-key/{bibkey}")
        return result

    def _fetch_authors(self, bibitem_id: int) -> List[Dict[str, str]]:
        junctions = self._get(f"/api/v1/bibitems/{bibitem_id}/authors")
        if not junctions:
            return []
        if not isinstance(junctions, list):
            junctions = junctions.get("items", junctions.get("data", []))

        authors: List[Dict[str, str]] = []
        for j in junctions:
            author_key = j.get("author_key")
            if not author_key:
                continue
            a = self._get(f"/api/v1/authors/by-key/{author_key}")
            if not a:
                continue
            given = str(a.get("given_name_unicode") or a.get("given_name") or "")
            family = str(a.get("family_name_unicode") or a.get("family_name") or "")
            if given or family:
                authors.append({"given_name": given, "surname": family})
        return authors

    def _fetch_journal(self, journal_key: str) -> Optional[Dict[str, Any]]:
        if journal_key in self._journal_cache:
            return self._journal_cache[journal_key]
        journal: Optional[Dict[str, Any]] = self._get(f"/api/v1/journals/by-key/{journal_key}")
        if journal:
            self._journal_cache[journal_key] = journal
        return journal

    def enrich_metadata(self, bibkey: str, base_metadata: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        bibitem = self.lookup_bibkey(bibkey)
        if bibitem is None:
            print(f"❌ Bibkey '{bibkey}' not found in Alexandria")
            return None

        enriched = base_metadata.copy() if base_metadata else {}
        enriched["bibkey"] = bibkey

        # Title
        title = bibitem.get("title_unicode") or bibitem.get("title")
        if title:
            enriched["title"] = str(title)

        # Year
        raw_year = bibitem.get("date_year")
        if raw_year:
            enriched["_year"] = int(raw_year)

        # Authors from Alexandria API
        bibitem_id = bibitem.get("id")
        if bibitem_id:
            parsed_authors = self._fetch_authors(int(bibitem_id))
        else:
            parsed_authors = []

        if not parsed_authors:
            raise ValueError(f"Bibkey '{bibkey}': no authors found in Alexandria")

        enriched["author_given_name"] = parsed_authors[0]["given_name"]
        enriched["author_surname"] = parsed_authors[0]["surname"]
        if len(parsed_authors) > 1:
            enriched["additional_authors"] = [
                {"given_name": a["given_name"], "surname": a["surname"]} for a in parsed_authors[1:]
            ]

        # Journal metadata from journal_key
        journal_key = bibitem.get("journal_key")
        if journal_key:
            journal = self._fetch_journal(str(journal_key))
            if journal:
                journal_name = journal.get("name_unicode") or journal.get("name_latex")
                if journal_name:
                    enriched["journal_title"] = str(journal_name)
                issn = journal.get("issn_electronic") or journal.get("issn_print")
                if issn:
                    enriched["journal_issn"] = str(issn)

        if bibitem.get("volume"):
            enriched["volume"] = str(bibitem["volume"])
        if bibitem.get("number"):
            enriched["issue"] = str(bibitem["number"])

        # Pages
        pages = bibitem.get("pages")
        if pages:
            pages_str = str(pages)
            sep = "--" if "--" in pages_str else "-"
            parts = pages_str.split(sep, 1)
            if len(parts) == 2:
                enriched["first_page"] = parts[0].strip()
                enriched["last_page"] = parts[1].strip()
            else:
                enriched["first_page"] = pages_str.strip()
                enriched["last_page"] = pages_str.strip()

        if bibitem.get("url"):
            enriched["url"] = str(bibitem["url"])
        if bibitem.get("doi"):
            enriched["existing_doi"] = str(bibitem["doi"])
        if bibitem.get("publisher"):
            enriched["publisher"] = str(bibitem["publisher"])
        if bibitem.get("address"):
            enriched["publisher_place"] = str(bibitem["address"])
        if bibitem.get("booktitle"):
            enriched["booktitle"] = str(bibitem["booktitle"])
        if bibitem.get("series"):
            enriched["series_title"] = str(bibitem["series"])
        if bibitem.get("edition"):
            enriched["edition"] = str(bibitem["edition"])

        # Language
        langid = bibitem.get("langid")
        if langid and str(langid) not in ("None", ""):
            enriched["language"] = _BABEL_TO_ISO.get(str(langid), str(langid))
        elif "language" not in enriched:
            enriched["language"] = "en"

        if bibitem.get("entry_type"):
            enriched["entry_type"] = str(bibitem["entry_type"])

        return enriched


def enrich_csv_with_bibliography(
    csv_path: str, bibliography_path: Optional[str] = None, bibkey_column: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Read a CSV file and enrich each row with bibliography metadata.

    Parameters
    ----------
    csv_path : str
        Path to the CSV file containing bibkeys
    bibliography_path : str, optional
        Path to bibliography ODS file (or uses BIBLIOGRAPHY_ODS_PATH env var)
    bibkey_column : str, optional
        Name of the column containing bibkeys (default: from BIBKEY_COLUMN_NAME env var or "_article_bib_key")

    Returns
    -------
    List[Dict[str, Any]]
        List of enriched metadata dictionaries
    """
    if bibkey_column is None:
        bibkey_column = BIBKEY_COLUMN_NAME

    enricher = BibliographyEnricher(bibliography_path)

    # Read CSV
    csv_df = pl.read_csv(csv_path)

    # Check if bibkey column exists
    if bibkey_column not in csv_df.columns:
        raise ValueError(
            f"CSV must contain bibkey column '{bibkey_column}'. " f"Available columns: {list(csv_df.columns)}"
        )

    enriched_rows = []
    total = len(csv_df)

    print(f"📖 Enriching {total} entries from CSV...")

    for idx, row in enumerate(csv_df.iter_rows(named=True)):
        bibkey = row.get(bibkey_column)

        if not bibkey:
            print(f"⚠️  Row {idx + 1}: No bibkey found, skipping")
            continue

        enriched = enricher.enrich_metadata(bibkey, base_metadata=row)

        if enriched:
            enriched_rows.append(enriched)
            if (idx + 1) % 10 == 0:
                print(f"   Processed {idx + 1}/{total} entries")
        else:
            print(f"⚠️  Row {idx + 1}: Could not enrich bibkey '{bibkey}'")

    print(f"✅ Successfully enriched {len(enriched_rows)}/{total} entries")

    return enriched_rows
