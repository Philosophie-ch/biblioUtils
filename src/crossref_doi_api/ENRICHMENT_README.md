# DOI Registration with Metadata Enrichment

This toolkit allows you to register and update DOIs using **two flexible modes**:

1. **Metadata JSON Mode** (Default, Recommended) - Provide pre-generated metadata JSON
2. **Bibliography Enrichment Mode** - Look up metadata from your bibliography ODS file

## Mode 1: Metadata JSON (Default)

**Best for:** Journal articles and journal issues with structured metadata.

Instead of providing all metadata fields in CSV, you can now just provide:
- `doi` - The DOI to register/update
- `metadata_json` - Pre-generated JSON string with article or journal issue metadata
- `link` - (optional) The URL where the publication lives
- `title` - (optional) For journal issues, combined with metadata title

### Supported Metadata Types

**Article Metadata:**
```json
{
  "type": "article",
  "year": 2025,
  "issue": "1",
  "pages": "123-145",
  "start_page": "123",
  "end_page": "145",
  "volume": "78",
  "journal": "Dialectica",
  "license": "CC-BY-4.0",
  "language": "en",
  "journal_issn": "1746-8361",
  "publication_status": "published",
  "keywords": ["philosophy", "epistemology"]
}
```

**Journal Issue Metadata:**
```json
{
  "type": "journal_issue",
  "issn": "1746-8361",
  "volume": "78",
  "issue": "1",
  "year": 2025,
  "license": "CC-BY-4.0",
  "language": "en",
  "keywords": ["philosophy"],
  "publication_status": "published",
  "title": "Special Issue on Epistemology"
}
```

## Mode 2: Alexandria Nexus Enrichment (`--alexandria`)

**Best for:** When Alexandria Nexus is running and has the bibliography data. This is the preferred enrichment mode — it fetches all metadata (authors, title, year, journal, ISSN, language, pages, etc.) from the Alexandria REST API.

The CSV only needs:
- `bibkey` - the unique identifier in Alexandria
- `doi` - the DOI to register
- `link` - the URL where the publication can be accessed

Everything else is fetched from the API:
- **Bibitem metadata**: title, year, language, volume, number, pages, publisher, etc. via `/api/v1/bibitems/by-key/{bibkey}`
- **Authors**: given name + family name via `/api/v1/bibitems/{id}/authors` + `/api/v1/authors/by-key/{key}`
- **Journal metadata**: journal title + ISSN via `/api/v1/journals/by-key/{journal_key}` (cached per journal)

**Setup:**
```bash
# Add to .env
ALEXANDRIA_API_URL=http://localhost:8080
ALEXANDRIA_API_KEY=your_api_key
```

**Usage:**
```bash
# Dry run
python batch_doi_registration_enriched.py data.csv --bulk --alexandria --dry-run

# Production
python batch_doi_registration_enriched.py data.csv --bulk --alexandria --production
```

## Mode 3: Bibliography ODS Enrichment

**Best for:** When Alexandria Nexus is not available, or for legacy workflows with existing bibliography ODS files.

Instead of metadata JSON, provide:
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
- `--bulk` - Submit all DOIs in a single XML (recommended)
- `--alexandria` - Use Alexandria Nexus API for enrichment
- `--alexandria-url URL` - Override `ALEXANDRIA_API_URL` env var
- `--alexandria-key KEY` - Override `ALEXANDRIA_API_KEY` env var
- `--delay SECONDS` - Delay between submissions (default: 3.0, non-bulk mode)
- `--retries NUMBER` - Max retry attempts (default: 3)
- `--dry-run` - Generate XML without submitting
- `--no-enrichment` - Disable bibliography enrichment
- `--bibliography PATH` - Override bibliography ODS path

### `update_dois_enriched.py`

Enhanced DOI updates with automatic metadata enrichment.

**Metadata JSON CSV format (default):**
```csv
doi,metadata_json,link
10.48106/dial.v78.i1,"{\"type\":\"journal_issue\",...}",https://philosophie.ch/dialectica-78-1
```

**Bibliography enrichment CSV format:**
```csv
publication_key,link
smith-2024-epistemology,https://philosophie.ch/new-url/smith-2024
jones-2023-ethics,https://philosophie.ch/new-url/jones-2023
```

*Note: Column names are case-insensitive. Also accepts `bibkey` or `_article_bib_key`.*

**Usage:**
```bash
# Metadata JSON mode (default)
python update_dois_enriched.py updates.csv --dry-run

# Bibliography enrichment mode
python update_dois_enriched.py updates.csv --use-bibliography --dry-run

# Sandbox testing
python update_dois_enriched.py updates.csv --sandbox

# Production updates
python update_dois_enriched.py updates.csv
```

**Options:**
- `--sandbox` - Use sandbox environment (default: production)
- `--dry-run` - Generate XML without submitting
- `--use-bibliography` - Enable bibliography enrichment mode
- `--bibliography PATH` - Override bibliography path
- `--encoding` - CSV file encoding (default: auto-detect)

**Important:** Do NOT mix articles and journal issues in the same CSV! They must be in separate files.

## How It Works

### Mode 1: Metadata JSON Processing

1. **Parse metadata JSON** - Validates JSON structure using Pydantic models
2. **Type detection** - Identifies article vs journal_issue types
3. **Field extraction** - Maps metadata fields to Crossref XML format
4. **XML generation** - Creates appropriate Crossref XML structure
5. **Validation** - Different validation rules for articles vs issues

**Key Features:**
- ✅ Articles require title and authors
- ✅ Journal issues don't require title or authors
- ✅ Separate `<journal>` blocks for each issue (Crossref schema requirement)
- ✅ Articles can be batched together by journal/volume/issue
- ✅ Case-insensitive CSV column names

### Mode 2: Alexandria Nexus Lookup

The `AlexandriaEnricher` class fetches metadata from the Alexandria Nexus REST API:

```python
from src.crossref_doi_api.bibliography_enrichment import AlexandriaEnricher

enricher = AlexandriaEnricher()  # uses ALEXANDRIA_API_URL and ALEXANDRIA_API_KEY from .env
metadata = enricher.enrich_metadata("smith-2024-epistemology")
```

It fetches bibitem data, authors (with proper sequencing), and journal metadata (title + ISSN) via the journal's `journal_key`. Journal responses are cached to avoid repeated API calls for articles in the same journal.

### Mode 3: Bibliography ODS Lookup

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

# Using Alexandria Nexus
batch = EnrichedBatchDOIRegistration(
    username="your_username",
    password="your_password",
    use_alexandria=True,
)

# Or using bibliography ODS file
batch = EnrichedBatchDOIRegistration(
    username="your_username",
    password="your_password",
    bibliography_path="/path/to/bibliography.ods",
)

# Bulk submission (recommended)
results = batch.register_bulk(csv_file="minimal.csv", use_sandbox=True, dry_run=True)

# Or per-DOI submission
results = batch.register_batch(csv_file="minimal.csv", use_sandbox=True, dry_run=True)
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

### Workflow 1: Register Journal Issue DOIs (Metadata JSON)

1. **Generate metadata JSON CSV** using `journal_issues_to_metadata_json.py`:
```bash
python src/utils/journal_issues_to_metadata_json.py journal_issues.csv
```

This creates a CSV with columns: `doi`, `metadata_json`, `link`, `title`

2. **Test in sandbox**:
```bash
python update_dois_enriched.py journal_issues_metadata.csv --dry-run --sandbox
```

3. **Review generated XML**, then register:
```bash
python update_dois_enriched.py journal_issues_metadata.csv --sandbox
```

4. **Production registration**:
```bash
python update_dois_enriched.py journal_issues_metadata.csv
```

### Workflow 2: Register Article DOIs (Metadata JSON)

1. **Generate metadata JSON CSV** using `bibliography_to_metadata_json.py`:
```bash
python src/utils/bibliography_to_metadata_json.py articles.csv
```

2. **Test and register** (same as journal issues workflow above)

### Workflow 3: Register DOIs (Bibliography Enrichment)

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
python batch_doi_registration_enriched.py new_dois.csv --use-bibliography --dry-run
```

4. **Review generated XML**, then register:
```bash
python batch_doi_registration_enriched.py new_dois.csv --use-bibliography
```

### Workflow 4: Update Existing DOIs (Bibliography Enrichment)

1. **Create minimal CSV** with bibkeys and new URLs:
```csv
bibkey,link
smith-2024,https://new-domain.com/smith-2024
jones-2023,https://new-domain.com/jones-2023
```

2. **Test update**:
```bash
python update_dois_enriched.py updates.csv --use-bibliography --dry-run
```

3. **Apply updates**:
```bash
python update_dois_enriched.py updates.csv --use-bibliography
```

## Troubleshooting

### "Missing 'doi' column" or "Missing 'metadata_json' column"

**Solution:** Make sure your CSV has the required columns:
- Metadata JSON mode: `doi`, `metadata_json` (case-insensitive)
- Optional columns: `link`, `title`, `update_type`, `update_reason`

### "JSON decode error" or "Metadata validation failed"

**Cause:** Invalid or malformed metadata JSON.

**Solution:**
- Use the provided generator scripts (`journal_issues_to_metadata_json.py` or `bibliography_to_metadata_json.py`)
- Validate JSON structure matches the expected schema (see examples above)
- Check for proper escaping of quotes in JSON strings

### "Missing title" or "Missing author information" for journal issues

**Cause:** The `content_type` field is not set to `"journal_issue"`.

**Solution:** Ensure your metadata JSON has `"type": "journal_issue"` for issue entries.

### "Mixed batch detected" error

**Cause:** CSV contains both articles and journal issues.

**Solution:** Separate articles and journal issues into different CSV files. They cannot be processed together.

### "Invalid content was found starting with element 'journal_issue'"

**Cause:** Old version of code that grouped multiple issues under one `<journal>` element.

**Solution:** Update to latest code. Each journal issue now gets its own `<journal>` block.

### Bibliography Enrichment Mode Issues

#### "Bibliography file not found"

Make sure `BIBLIOGRAPHY_ODS_PATH` is set in `.env` and points to a valid ODS file:
```bash
echo $BIBLIOGRAPHY_ODS_PATH  # Should print the path
ls -la $BIBLIOGRAPHY_ODS_PATH  # Should show the file
```

#### "Bibkey not found in bibliography"

Check that:
- The bibkey exists in your bibliography ODS
- The bibkey column is named exactly `bibkey`
- The bibkey values match exactly (case-sensitive)

#### "Author parsing failed"

If `philch-bib-sdk` is not available, the system falls back to basic parsing. To use the full parser:
```bash
pip install philoch-bib-sdk
```

#### "Missing required fields"

The enrichment may fail if the bibliography entry is missing critical fields like `author` or `title`. Check the bibliography entry and ensure it has:
- Either `author` or `editor`
- `title`
- `date` (year)

#### Enrichment disabled

If you see "⚠️ Bibliography enrichment disabled", check:
1. `BIBLIOGRAPHY_ODS_PATH` is set correctly
2. The bibliography file exists and is readable
3. The file is a valid ODS format
4. The file contains a `bibkey` column

## Benefits

### Metadata JSON Mode
✅ **Type safety** - Pydantic validation ensures correct structure
✅ **Journal issue support** - First-class support for issue-level DOIs
✅ **Separation of concerns** - Clean separation between data generation and submission
✅ **Reusable metadata** - Generated metadata can be version-controlled
✅ **Flexible validation** - Different rules for articles vs issues

### Bibliography Enrichment Mode
✅ **Less manual work** - No need to copy metadata from bibliography to CSV
✅ **Consistency** - Single source of truth for metadata
✅ **Bulk operations** - Process hundreds of entries with minimal CSV
✅ **Error prevention** - Automatic parsing reduces typos
✅ **Maintainability** - Update bibliography once, use everywhere

## Integration with Existing Scripts

The enriched scripts inherit from the original scripts, so:
- All original features still work
- All original options are supported
- Can switch between metadata JSON and bibliography modes
- Compatible with existing workflows

## Architecture

### Metadata JSON Mode Architecture
```
CSV with metadata_json → MetadataJSONParser → Validated Metadata → XML Generation → Crossref API
    ↓                           ↓                    ↓                    ↓
DOI + JSON              Pydantic validation    content_type         Separate <journal>
metadata                article vs issue       detection            blocks for issues
```

### Alexandria Enrichment Mode Architecture (`--alexandria`)
```
Minimal CSV → AlexandriaEnricher → Full Metadata → CSVToXMLConverter → Crossref API
    ↓              ↓                      ↓                ↓
 bibkey      REST API calls         author lookup     XML generation
 + doi       /bibitems/by-key/      /authors/by-key/  (bulk or per-DOI)
 + link      /journals/by-key/      field mapping
```

### Bibliography ODS Enrichment Mode Architecture
```
Minimal CSV → BibliographyEnricher → Full Metadata → CSVToXMLConverter → Crossref API
    ↓              ↓                      ↓                ↓
 bibkey      polars lookup           author parsing    XML generation
 + link      in ODS file             field mapping     DOI submission
```

## Related Tools

### Metadata JSON Generator Scripts
- `src/utils/journal_issues_to_metadata_json.py` - Generate metadata JSON for journal issues
- `src/utils/bibliography_to_metadata_json.py` - Generate metadata JSON for articles from bibliography

### Core Modules
- `metadata_json_parser.py` - Pydantic-based metadata JSON parser and validator
- `bibliography_enrichment.py` - Enrichment via Alexandria Nexus API (`AlexandriaEnricher`) or bibliography ODS file (`BibliographyEnricher`)
- `csv_to_xml.py` - CSV to Crossref XML generation (single + bulk modes)
- `batch_doi_registration.py` - Base batch DOI registration with bulk submission support
- `batch_doi_registration_enriched.py` - Enriched registration with `--alexandria` and `--bulk` flags
- `check_submission_status.py` - Query Crossref submission results by batch ID
- `update_dois.py` - Core DOI update logic with journal issue support
- `update_dois_enriched.py` - Enhanced update script with both modes

## See Also

- [README.md](README.md) - Main documentation for Crossref DOI tools
- [DOI_UPDATE_FORMAT.md](DOI_UPDATE_FORMAT.md) - DOI update CSV format
- [CSV_FORMAT.md](CSV_FORMAT.md) - Full CSV format specification
