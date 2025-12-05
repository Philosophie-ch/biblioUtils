# Big Portal Update - Reference Box Generation

## Overview

Regenerate reference boxes (HTML files) for all entity types on philosophie.ch portal:
- Individual pages (articles)
- Profiles (author profiles)
- Biblio profiles
- Journals
- Publications

## Prerequisites

- Python 3.13+ with virtual environment
- Rust toolchain (for transitive closure computation)
- Access to bibliography: `/home/alebg/philosophie-ch/Dropbox/philosophie-ch/biblio/biblio-v10-table.ods`
- Access to DLTC workhouse directory (configured in `src/ref_pipe/.env`)

---

## Phase 1: Compute Bibliography Dependencies

### Goal
Compute transitive closures for all bibliography entries to determine:
- `further_references_closed`: All references cited in title/notes (transitively)
- `depends_on_closed`: All dependencies including crossrefs (transitively)

### Steps

#### 1.1 Environment Setup
```bash
cd /home/alebg/philosophie-ch/bibliography/biblioUtils
source .venv/bin/activate
```

#### 1.2 Build Rust Crate (if needed)
```bash
cd rust_crate
maturin develop
cd ..
```

#### 1.3 Run Dependency Computation
```bash
python src/bib_deps/bib_deps_recursive.py \
  -i /home/alebg/philosophie-ch/Dropbox/philosophie-ch/biblio/biblio-v10-table.ods \
  -o data/bibliography-with-closures.tsv
```

**Output**: `data/bibliography-with-closures.tsv` with columns:
- `bibkey`
- `title`, `notes`, `crossref`, `further_note`
- `further_references` (direct)
- `depends_on` (direct)
- `further_references_closed` (transitive)
- `depends_on_closed` (transitive)
- `max_depth_reached`
- `status`, `error_message`

#### 1.4 Type Check
```bash
poetry run mypy .
```

---

## Phase 2: Extract Bibkeys for Each Entity Type

### Goal
For each entity type, extract matching bibkeys from bibliography as comma-separated lists.

### Approach
1. Load bibliography once in memory
2. For each entity CSV, match entity IDs to bibliography column
3. Extract bibkeys and aggregate as comma-separated strings
4. Output CSV with original columns + bibkey columns

### Entity Types & Mappings

**TODO**: User to provide for each entity type:
- CSV file location
- ID column name in entity CSV
- Matching column name in bibliography
- Number of output columns needed (1 or 3: main_bibkeys, further_references, depends_on)

#### 2.1 Journals
- **Entity CSV**: `[TO BE PROVIDED]`
- **Entity ID column**: `ID`
- **Bibliography column**: `journal_id`
- **Output columns**: `[1 or 3 - TO BE SPECIFIED]`

#### 2.2 Profiles
- **Entity CSV**: `[TO BE PROVIDED]`
- **Entity ID column**: `[TO BE PROVIDED]`
- **Bibliography column**: `[TO BE PROVIDED]`
- **Output columns**: `[1 or 3 - TO BE SPECIFIED]`

#### 2.3 Biblio Profiles
- **Entity CSV**: `[TO BE PROVIDED]`
- **Entity ID column**: `[TO BE PROVIDED]`
- **Bibliography column**: `[TO BE PROVIDED]`
- **Output columns**: `[1 or 3 - TO BE SPECIFIED]`

#### 2.4 Pages
- **Entity CSV**: `[TO BE PROVIDED]`
- **Entity ID column**: `[TO BE PROVIDED]`
- **Bibliography column**: `[TO BE PROVIDED]`
- **Output columns**: `[1 or 3 - TO BE SPECIFIED]`

#### 2.5 Publications
- **Entity CSV**: `[TO BE PROVIDED]`
- **Entity ID column**: `[TO BE PROVIDED]`
- **Bibliography column**: `[TO BE PROVIDED]`
- **Output columns**: `[1 or 3 - TO BE SPECIFIED]`

### Implementation Plan

#### Create extraction script: `src/utils/extract_entity_bibkeys.py`

**Features**:
- Load bibliography ODS once into memory (polars DataFrame)
- Accept entity CSV + mapping config
- Match entity IDs to bibliography column
- Extract bibkeys (direct references)
- Optionally lookup closures from `further_references_closed` and `depends_on_closed`
- Output CSV preserving original column order
- Type-checked with mypy

**Usage**:
```bash
python src/utils/extract_entity_bibkeys.py \
  -e <entity.csv> \
  -b <bibliography-with-closures.tsv> \
  --entity-id-col <column_name> \
  --biblio-match-col <column_name> \
  --output-mode <single|triple> \
  -o <output.csv>
```

Where:
- `--output-mode single`: Output only `main_bibkeys` column
- `--output-mode triple`: Output `main_bibkeys`, `further_references`, `depends_on` columns

---

## Phase 3: Generate HTML Reference Boxes

### Goal
Use `ref_pipe` to generate HTML files for each entity.

### Prerequisites
- Entity CSVs with bibkey columns from Phase 2
- Docker container with dltc-env running
- Environment configured in `src/ref_pipe/.env`

### Steps

#### 3.1 For Articles
```bash
PYTHONPATH='.' python src/ref_pipe/main_local.py \
  -i data/entities/articles-with-bibkeys.csv \
  -e utf-8 \
  -t article \
  -v src/ref_pipe/.env
```

**Output**:
- `{url_endpoint}-references.html`
- `{url_endpoint}-further-references.html`

#### 3.2 For Profiles
```bash
PYTHONPATH='.' python src/ref_pipe/main_local.py \
  -i data/entities/profiles-with-bibkeys.csv \
  -e utf-8 \
  -t profile \
  -v src/ref_pipe/.env
```

**Output**: Same as articles (2 HTML files per profile)

#### 3.3 For Journals
```bash
PYTHONPATH='.' python src/ref_pipe/main_local.py \
  -i data/entities/journals-with-bibkeys.csv \
  -e utf-8 \
  -t journal \
  -v src/ref_pipe/.env
```

**Output**: Single collapsible HTML file per journal: `{url_endpoint}.html`

#### 3.4 For Other Entity Types
- **Biblio Profiles**: Use `profile` type
- **Pages**: Use `article` type
- **Publications**: [TO BE DETERMINED - may need new entity type]

---

## Phase 4: Quality Assurance

### Validation Checks
1. All entity IDs processed successfully
2. No missing bibkeys (check error logs)
3. HTML files generated for all entities
4. Spot-check sample HTML outputs for correctness

### Type Checking
```bash
poetry run mypy .
```

### Tests (if applicable)
```bash
pytest tests/
```

---

## Output Locations

### Intermediate Files
- `data/bibliography-with-closures.tsv`: Bibliography with computed closures
- `data/entities/*.csv`: Entity CSVs with bibkey columns

### Final HTML Files
Location: `{DLTC_WORKHOUSE_DIRECTORY}/{REF_PIPE_DIR_RELATIVE_PATH}/`

Example: `data/ref_pipe/dwh-[date]/refpipe/`

---

## Script Reference

### Dependency Computation
- **Main**: `src/bib_deps/bib_deps_recursive.py`
- **Lookup**: `src/bib_deps/closed_deps_lookup.py`
- **Author bootstrap**: `src/utils/author_references_bootstrap.py`

### HTML Generation
- **Pipeline**: `src/ref_pipe/main_local.py`
- **Div generation**: `src/ref_pipe/prep_divs.py`
- **HTML assembly**: `src/ref_pipe/html_io.py`

### To Be Created
- `src/utils/extract_entity_bibkeys.py`: Extract bibkeys for entities

---

## Known Considerations

### Dependency Types
- **further_references**: Citations from `title` + `notes` fields
- **depends_on**: Citations from `title` + `notes` + `further_note` + `crossref`

### Entity-Specific Requirements
- **Journals**: Need bibliography with `volume`, `number`, `date` columns for collapsible structure
- **Articles/Profiles**: Need `url_endpoint` column for filename generation

### Performance
- Bibliography loaded once in memory per entity type
- Rust crate handles transitive closure computation efficiently
- ref_pipe processes entities sequentially (parallel processing not implemented)

---

## Timeline Estimate

- **Phase 1**: ~30 minutes (dependency computation)
- **Phase 2**: ~2 hours (script creation + entity processing)
- **Phase 3**: Variable (depends on entity count, ~1-2 entities/minute)
- **Phase 4**: ~30 minutes (validation)

**Total**: ~3-4 hours + entity processing time

---

## Status

- [ ] Phase 1: Compute bibliography dependencies
- [ ] Phase 2: Extract bibkeys for all entity types
  - [ ] Journals
  - [ ] Profiles
  - [ ] Biblio Profiles
  - [ ] Pages
  - [ ] Publications
- [ ] Phase 3: Generate HTML reference boxes
  - [ ] Articles
  - [ ] Profiles
  - [ ] Journals
  - [ ] Other entity types
- [ ] Phase 4: Quality assurance

---

## Notes

_Add any observations, issues, or decisions made during execution here._
