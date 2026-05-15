# Crossref DOI API Tools

A complete toolkit for registering DOIs with Crossref using CSV files. This system processes bibliography data from CSV files and registers DOIs directly with Crossref's production or sandbox environments.

## Features

- ✅ **CSV to DOI Registration**: Process CSV files and register DOIs automatically
- ✅ **Journal Issue Support**: Register DOIs for journal issues and articles
- ✅ **Metadata JSON Mode**: Pre-validated JSON metadata with Pydantic
- ✅ **Bibliography Enrichment**: Auto-populate metadata from bibliography ODS files
- ✅ **Alexandria Nexus Enrichment**: Fetch metadata from the Alexandria REST API (`--alexandria`)
- ✅ **Bulk Submission**: Package all DOIs into a single XML and submit in one POST (`--bulk`)
- ✅ **Batch Processing**: Handle hundreds/thousands of DOIs efficiently
- ✅ **Production & Sandbox**: Test safely before registering real DOIs
- ✅ **Conflict Detection**: Check for existing DOIs before processing
- ✅ **Retry Logic**: Automatic retry with exponential backoff
- ✅ **Progress Tracking**: Progress updates every 100 entries
- ✅ **XML Output Persistence**: Production XMLs always saved to `CROSSREF_XML_OUTPUT_DIR`
- ✅ **Strong Typing**: Full mypy compliance for reliability

## Quick Start

### 1. Setup

```bash
# Install dependencies
pip install requests python-dotenv

# Create credentials file
cp .env.template .env
# Edit .env with your Crossref credentials
```

### 2. Prepare Your Data

Create a CSV file with your publications (see `CSV_FORMAT.md` for details):

```csv
doi,title,resource_url,publication_year,author_given_name,author_surname
10.48106/example.2025.001,My Article,https://example.com/article1,2025,John,Doe
```

### 3. Register DOIs

```bash
# Test in sandbox (recommended first)
python batch_doi_registration.py your_data.csv

# Register in production (creates real DOIs!)
python batch_doi_registration.py your_data.csv --production
```

## Main Scripts

### `update_dois_enriched.py` - Enhanced DOI Update Tool (Recommended)

**NEW:** Register and update DOIs with metadata JSON or bibliography enrichment.

**Metadata JSON mode (default):**
```bash
# For journal issues
python update_dois_enriched.py journal_issues.csv --dry-run --sandbox

# For articles
python update_dois_enriched.py articles.csv --dry-run --sandbox
```

**Bibliography enrichment mode:**
```bash
python update_dois_enriched.py updates.csv --use-bibliography --dry-run
```

**Options:**
- `--sandbox` - Use sandbox environment (default: production)
- `--dry-run` - Generate XML without submitting
- `--use-bibliography` - Enable bibliography enrichment mode
- `--bibliography PATH` - Override bibliography path
- `--encoding` - CSV file encoding (default: auto-detect)

See [ENRICHMENT_README.md](ENRICHMENT_README.md) for detailed usage.

### `batch_doi_registration_enriched.py` - Enriched DOI Registration (Recommended)

Register DOIs with automatic metadata enrichment from either a bibliography ODS file or the Alexandria Nexus API.

**Basic Usage:**
```bash
# Using bibliography ODS file (default enrichment)
python batch_doi_registration_enriched.py data.csv --bulk

# Using Alexandria Nexus API for enrichment
python batch_doi_registration_enriched.py data.csv --bulk --alexandria
```

**Options:**
- `--production` - Use production environment (default: sandbox)
- `--bulk` - Submit all DOIs in a single XML (recommended)
- `--alexandria` - Use Alexandria Nexus API instead of ODS file
- `--alexandria-url URL` - Override `ALEXANDRIA_API_URL` env var
- `--alexandria-key KEY` - Override `ALEXANDRIA_API_KEY` env var
- `--bibliography PATH` - Override `BIBLIOGRAPHY_ODS_PATH` env var
- `--dry-run` - Generate XML without submitting
- `--delay SECONDS` - Delay between submissions (default: 3.0, non-bulk mode)
- `--retries NUMBER` - Max retry attempts (default: 3)
- `--no-conflict-check` - Skip checking for existing DOIs
- `--no-enrichment` - Disable enrichment, use full CSV directly
- `--encoding` - CSV file encoding (default: auto-detect)

**Examples:**
```bash
# Dry run with Alexandria to inspect generated XML
python batch_doi_registration_enriched.py data.csv --bulk --alexandria --dry-run

# Production bulk submission with Alexandria
python batch_doi_registration_enriched.py data.csv --bulk --alexandria --production

# Sandbox testing with ODS enrichment
python batch_doi_registration_enriched.py data.csv --bulk
```

### `batch_doi_registration.py` - Base DOI Registration Tool

Register DOIs from CSV files directly with Crossref (no enrichment).

**Basic Usage:**
```bash
python batch_doi_registration.py publications.csv
```

**Options:**
- `--sandbox` - Use sandbox environment (default)
- `--production` - Use production environment
- `--delay SECONDS` - Delay between submissions (default: 3.0)
- `--retries NUMBER` - Max retry attempts (default: 3)
- `--verify` - Verify DOIs after registration
- `--no-conflict-check` - Skip checking for existing DOIs

**Examples:**
```bash
# Safe testing in sandbox
python batch_doi_registration.py data.csv --delay 2.0

# Production with verification
python batch_doi_registration.py data.csv --production --verify
```

### `csv_to_xml.py` - Standalone XML Generation

Generate Crossref XML files from CSV (for testing/inspection).

```bash
python csv_to_xml.py publications.csv -o output_directory
```

### `xml_parser_test.py` - XML Validation

Validate XML files against Crossref requirements.

```bash
python xml_parser_test.py generated_file.xml
```

### `api_test.py` - API Testing & Exploration

Test Crossref API connectivity and explore your account.

```bash
python api_test.py
```

## Configuration

### Environment Variables (.env)

```bash
# Production credentials
CROSSREF_USERNAME=your_username
CROSSREF_PASSWORD=your_password  
CROSSREF_MEMBER_ID=your_member_id

# Sandbox credentials (optional, fallback to production)
CROSSREF_SANDBOX_USERNAME=sandbox_username
CROSSREF_SANDBOX_PASSWORD=sandbox_password

# Bibliography ODS enrichment
BIBLIOGRAPHY_ODS_PATH=/path/to/bibliography.ods
AUTHORS_CSV_PATH=/path/to/authors.csv
BIBKEY_COLUMN_NAME=bibkey

# Alexandria Nexus enrichment (used with --alexandria flag)
ALEXANDRIA_API_URL=http://localhost:8080
ALEXANDRIA_API_KEY=your_api_key

# Output directory for generated XML files
CROSSREF_XML_OUTPUT_DIR=/path/to/output
```

### CSV Format

See `CSV_FORMAT.md` for complete specification. Minimum required fields:

- `doi` - DOI to register (e.g., "10.48106/example.2025.001")
- `title` - Publication title
- `resource_url` - URL where publication is accessible
- `publication_year` - Year (YYYY format)
- `author_given_name` - First name of primary author
- `author_surname` - Last name of primary author

## Workflow

1. **Prepare CSV** with publication metadata
2. **Test in sandbox** to ensure everything works
3. **Get sandbox credentials** from Crossref support if needed
4. **Run production registration** when ready
5. **Verify DOIs** resolve correctly

## Memory-Efficient Design

The system uses Python generators to process large CSV files without loading everything into memory:

- ✅ **No temporary XML files created**
- ✅ **Streaming CSV processing**  
- ✅ **Memory usage scales with single row, not dataset size**
- ✅ **Progress reporting every 100 entries**

Perfect for processing thousands of DOIs efficiently.

## Safety Features

- **Sandbox by default** - prevents accidental production registrations
- **Production confirmation** - requires typing "YES" for production
- **Conflict checking** - prevents duplicate DOI registration  
- **Rate limiting** - respects Crossref API limits
- **Comprehensive error handling** - graceful failure recovery


## Architecture

### Individual submission mode (default)
```
CSV File → Generator → XML per DOI (in memory) → Crossref API → DOI Registration
    ↓                                                    ↓
Validation                                        Response Handling
    ↓                                                    ↓  
Error Reporting                                  Progress Tracking
```

### Bulk submission mode (`--bulk`, recommended)
```
CSV File → All rows → Single XML <doi_batch> → One POST → Crossref API
    ↓                        ↓                                  ↓
Validation            Saved to disk                     Batch tracking
```

### Enrichment data sources
```
--alexandria:      CSV (bibkey+doi+link) → Alexandria Nexus API → Full metadata
default:           CSV (bibkey+doi+link) → Bibliography ODS file → Full metadata
--no-enrichment:   CSV must contain all required fields directly
```

## Troubleshooting

**"Missing credentials"**
- Ensure `.env` file exists with valid Crossref credentials

**"401 Unauthorized in sandbox"**
- Request sandbox access from Crossref support
- Use `--production` flag to test with production credentials (careful!)

**"DOI conflicts found"**
- Review existing DOIs in your account
- Use `--no-conflict-check` to override (not recommended)

**"Rate limiting errors"**  
- Increase `--delay` parameter
- Reduce concurrent processing

## Documentation

- 📖 [ENRICHMENT_README.md](ENRICHMENT_README.md) - Metadata JSON and bibliography enrichment guide
- 📖 [CSV_FORMAT.md](CSV_FORMAT.md) - Full CSV format specification
- 📖 [DOI_UPDATE_FORMAT.md](DOI_UPDATE_FORMAT.md) - DOI update CSV format

## Metadata JSON Generators

Generate metadata JSON CSV files from your data:

- `src/utils/journal_issues_to_metadata_json.py` - Convert journal issues to metadata JSON
- `src/utils/bibliography_to_metadata_json.py` - Convert bibliography to metadata JSON

## Support

- 📧 Crossref Support: `support@crossref.org`
- 🔧 API Details: See `api_test.py`

---

**⚠️ Important**: Always test in sandbox before production registration. Production DOI registration is permanent and cannot be undone!