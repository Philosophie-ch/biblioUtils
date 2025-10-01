# Bibliography Enrichment for DOI Registration

This enhancement allows you to register and update DOIs using **minimal CSV files** that get automatically enriched with metadata from your full bibliography ODS file.

## What's New?

Instead of providing all metadata in your CSV files, you can now just provide:
- `publication_key` (or `bibkey` or `_article_bib_key`) - the unique identifier from your bibliography
- `link` - the URL where the publication lives
- `doi` - (optional) the DOI to register/update

All other metadata (authors, title, journal, volume, issue, pages, etc.) will be automatically looked up from your bibliography ODS file.

**Column Name Flexibility:** The scripts automatically recognize these bibkey column names:
- `publication_key` (default, matches portal exports)
- `bibkey` (alternative)
- `_article_bib_key` (fallback)

## Setup

### 1. Configure Bibliography Path

Add to your `.env` file:

```bash
BIBLIOGRAPHY_ODS_PATH=/path/to/your/bibliography.ods
```

### 2. Bibliography Requirements

Your ODS file must:
- Contain a `bibkey` column with unique identifiers
- Have standard bibliography fields: `author`, `title`, `date`, `journal`, `volume`, `number`, `pages`, etc.
- Use the author format: `"Family, Given and Family, Given"` (e.g., `"Müller, Hans and Schmidt, Anna"`)

## New Scripts

### `batch_doi_registration_enriched.py`

Enhanced DOI registration with automatic metadata enrichment.

**Minimal CSV format:**
```csv
publication_key,link,doi
smith-2024-epistemology,https://philosophie.ch/smith-2024,10.48106/dial.2024.smith
jones-2023-ethics,https://philosophie.ch/jones-2023,10.48106/dial.2023.jones
```

*Note: Also accepts `bibkey` or `_article_bib_key` as the bibkey column name.*

**Usage:**
```bash
# Sandbox testing
python batch_doi_registration_enriched.py minimal.csv

# Production registration
python batch_doi_registration_enriched.py minimal.csv --production

# Dry run to inspect generated XML
python batch_doi_registration_enriched.py minimal.csv --dry-run

# Disable enrichment (use full CSV)
python batch_doi_registration_enriched.py full.csv --no-enrichment
```

**Options:**
- `--production` - Use production environment (default: sandbox)
- `--delay SECONDS` - Delay between submissions (default: 3.0)
- `--retries NUMBER` - Max retry attempts (default: 3)
- `--dry-run` - Generate XML without submitting
- `--no-enrichment` - Disable bibliography enrichment
- `--bibliography PATH` - Override bibliography path

### `update_dois_enriched.py`

Enhanced DOI updates with automatic metadata enrichment.

**Minimal CSV format:**
```csv
publication_key,link
smith-2024-epistemology,https://philosophie.ch/new-url/smith-2024
jones-2023-ethics,https://philosophie.ch/new-url/jones-2023
```

*Note: Also accepts `bibkey` or `_article_bib_key` as the bibkey column name.*

**Usage:**
```bash
# Dry run to inspect XML
python update_dois_enriched.py updates.csv --dry-run

# Sandbox testing
python update_dois_enriched.py updates.csv --sandbox

# Production updates
python update_dois_enriched.py updates.csv

# Disable enrichment
python update_dois_enriched.py updates.csv --no-enrichment
```

**Options:**
- `--sandbox` - Use sandbox environment (default: production)
- `--dry-run` - Generate XML without submitting
- `--no-enrichment` - Disable bibliography enrichment
- `--bibliography PATH` - Override bibliography path

## How It Works

### 1. Bibliography Lookup

The `BibliographyEnricher` class loads your ODS file using polars and provides fast bibkey lookups:

```python
from src.crossref_doi_api.bibliography_enrichment import BibliographyEnricher

enricher = BibliographyEnricher()
metadata = enricher.enrich_metadata("smith-2024-epistemology")
```

### 2. Author Parsing

Authors are parsed using the `philch-bib-sdk` library, which handles:
- Multiple authors separated by " and "
- Format: "Family, Given and Family, Given"
- Mononyms (single names)
- Missing first names

Example: `"Müller, Hans and Schmidt and Johnson, Mary"` is parsed into:
```python
[
    {"given_name": "Hans", "surname": "Müller"},
    {"given_name": "", "surname": "Schmidt"},
    {"given_name": "Mary", "surname": "Johnson"}
]
```

### 3. Field Mapping

The enricher extracts and maps bibliography fields to Crossref format:

| Bibliography Field | Crossref Field |
|-------------------|----------------|
| `bibkey` | Identifier for lookup |
| `author` | Parsed to `author_given_name`, `author_surname`, `additional_authors` |
| `editor` | Used if no author present |
| `title` | `title` |
| `date` | `_year` |
| `journal` | `journal_title` |
| `volume` | `volume` |
| `number` | `issue` |
| `pages` | Parsed to `first_page`, `last_page` |
| `doi` | `existing_doi` |
| `url` | `url` |
| `publisher` | `publisher` |
| `address` | `publisher_place` |
| `booktitle` | `booktitle` |
| `series` | `series_title` |
| `_langid` | `language` |

### 4. Enrichment Process

1. Load minimal CSV with bibkeys
2. For each bibkey:
   - Look up entry in bibliography ODS
   - Extract all relevant fields
   - Parse author string into structured format
   - Parse page range (e.g., "123-145" → first: 123, last: 145)
   - Merge with base metadata from CSV
3. Create temporary enriched CSV
4. Process with standard Crossref tools
5. Clean up temporary file

## Advanced Usage

### Custom Bibliography Path

```bash
python batch_doi_registration_enriched.py data.csv --bibliography /custom/path/biblio.ods
```

### Programmatic Use

```python
from src.crossref_doi_api.batch_doi_registration_enriched import EnrichedBatchDOIRegistration

batch = EnrichedBatchDOIRegistration(
    username="your_username",
    password="your_password",
    bibliography_path="/path/to/bibliography.ods",
    enable_enrichment=True
)

results = batch.register_batch(
    csv_file="minimal.csv",
    use_sandbox=True,
    dry_run=True
)
```

### Enrichment Only

To just enrich a CSV without registering DOIs:

```python
from src.crossref_doi_api.bibliography_enrichment import enrich_csv_with_bibliography

enriched_data = enrich_csv_with_bibliography(
    csv_path="minimal.csv",
    bibliography_path="/path/to/bibliography.ods"
)

# enriched_data is a list of dictionaries with full metadata
for entry in enriched_data:
    print(f"{entry['bibkey']}: {entry['title']} by {entry['author_surname']}")
```

## Workflow Examples

### Registering New DOIs

1. **Create minimal CSV** with bibkeys and URLs:
```csv
bibkey,link,doi
smith-2024,https://philosophie.ch/smith-2024,10.48106/dial.2024.01
```

2. **Set bibliography path** in `.env`:
```bash
BIBLIOGRAPHY_ODS_PATH=/path/to/bibliography.ods
```

3. **Test in sandbox**:
```bash
python batch_doi_registration_enriched.py new_dois.csv --dry-run
```

4. **Review generated XML**, then register:
```bash
python batch_doi_registration_enriched.py new_dois.csv
```

### Updating Existing DOIs

1. **Create minimal CSV** with bibkeys and new URLs:
```csv
bibkey,link
smith-2024,https://new-domain.com/smith-2024
jones-2023,https://new-domain.com/jones-2023
```

2. **Test update**:
```bash
python update_dois_enriched.py updates.csv --dry-run
```

3. **Apply updates**:
```bash
python update_dois_enriched.py updates.csv
```

## Troubleshooting

### "Bibliography file not found"

Make sure `BIBLIOGRAPHY_ODS_PATH` is set in `.env` and points to a valid ODS file:
```bash
echo $BIBLIOGRAPHY_ODS_PATH  # Should print the path
ls -la $BIBLIOGRAPHY_ODS_PATH  # Should show the file
```

### "Bibkey not found in bibliography"

Check that:
- The bibkey exists in your bibliography ODS
- The bibkey column is named exactly `bibkey`
- The bibkey values match exactly (case-sensitive)

### "Author parsing failed"

If `philch-bib-sdk` is not available, the system falls back to basic parsing. To use the full parser:
```bash
pip install philoch-bib-sdk
```

### "Missing required fields"

The enrichment may fail if the bibliography entry is missing critical fields like `author` or `title`. Check the bibliography entry and ensure it has:
- Either `author` or `editor`
- `title`
- `date` (year)

### Enrichment disabled

If you see "⚠️ Bibliography enrichment disabled", check:
1. `BIBLIOGRAPHY_ODS_PATH` is set correctly
2. The bibliography file exists and is readable
3. The file is a valid ODS format
4. The file contains a `bibkey` column

## Benefits

✅ **Less manual work** - No need to copy metadata from bibliography to CSV
✅ **Consistency** - Single source of truth for metadata
✅ **Bulk operations** - Process hundreds of entries with minimal CSV
✅ **Flexibility** - Can still use full CSVs with `--no-enrichment`
✅ **Error prevention** - Automatic parsing reduces typos
✅ **Maintainability** - Update bibliography once, use everywhere

## Integration with Existing Scripts

The enriched scripts inherit from the original scripts, so:
- All original features still work
- All original options are supported
- Can disable enrichment with `--no-enrichment` flag
- Compatible with existing workflows

## Architecture

```
Minimal CSV → BibliographyEnricher → Full Metadata → CSVToXMLConverter → Crossref API
    ↓              ↓                      ↓                ↓
 bibkey      polars lookup           author parsing    XML generation
 + link      in ODS file             field mapping     DOI submission
```

## See Also

- [README.md](README.md) - Main documentation for Crossref DOI tools
- [DOI_UPDATE_FORMAT.md](DOI_UPDATE_FORMAT.md) - DOI update CSV format
- `bibliography_enrichment.py` - Core enrichment module
- `batch_doi_registration_enriched.py` - Enriched batch registration
- `update_dois_enriched.py` - Enriched DOI updates
