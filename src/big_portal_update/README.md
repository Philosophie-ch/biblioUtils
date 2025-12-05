# Big Portal Update - Reference Box Generation

Scripts for regenerating reference boxes (HTML files) for all entity types on philosophie.ch portal.

## Overview

This process extracts bibliography references for different entity types and computes transitive closures to generate complete reference lists including:
- Direct references (main bibkeys)
- Further references (citations found in bibliography entries)
- Dependencies (including crossrefs and further_note field)

## Prerequisites

- Python 3.13+ with virtual environment
- Rust toolchain (for transitive closure computation)
- Bibliography: `/home/alebg/philosophie-ch/Dropbox/philosophie-ch/biblio/biblio-v10-table.ods`
- Precomputed closures: `data/bibliography-with-closures.tsv`

## Phase 1: Compute Bibliography Dependencies

Run once to generate transitive closures:

```bash
python src/bib_deps/bib_deps_recursive.py \
  -i /home/alebg/philosophie-ch/Dropbox/philosophie-ch/biblio/biblio-v10-table.ods \
  -o data/bibliography-with-closures.tsv
```

**Output**: `data/bibliography-with-closures.tsv` with columns:
- `bibkey`, `title`, `notes`, `crossref`, `further_note`
- `_further-references` (transitive closure of citations from title+notes)
- `_depends-on` (transitive closure of title+notes+further_note+crossref)

**Time**: ~11 minutes for 209,583 entries

## Phase 2: Extract Bibkeys for Entity Types

### Publishers

```bash
python src/big_portal_update/publisher_references_extractor.py \
  -p data/publishers.csv \
  -b /home/alebg/philosophie-ch/Dropbox/philosophie-ch/biblio/biblio-v10-table.ods \
  -c data/bibliography-with-closures.tsv \
  -o data/publishers-with-bibkeys.csv \
  -e utf-8

python src/big_portal_update/truncate_long_cells.py \
  -i data/publishers-with-bibkeys.csv \
  -o data/publishers-with-bibkeys-sheets.csv \
  -e utf-8
```

**Input columns**: `id`, `name`
**Bibliography match**: `publisher-id`
**Output columns**: `_references_keys`, `_further_references_keys`, `_references_dependencies_keys`
**Results**: 2,005 publishers, 43,358 bibliography entries matched

### Journals

```bash
python src/big_portal_update/journal_references_extractor.py \
  -j data/journals.csv \
  -b /home/alebg/philosophie-ch/Dropbox/philosophie-ch/biblio/biblio-v10-table.ods \
  -c data/bibliography-with-closures.tsv \
  -o data/journals-with-bibkeys.csv \
  -e utf-8

python src/big_portal_update/truncate_long_cells.py \
  -i data/journals-with-bibkeys.csv \
  -o data/journals-with-bibkeys-sheets.csv \
  -e utf-8
```

**Input columns**: `id`, `name`
**Bibliography match**: `journal-id`
**Output columns**: `_references_keys`, `_further_references_keys`, `_references_dependencies_keys`
**Results**: 2,063 journals, 75,292 bibliography entries matched

### Profiles (Authors)

```bash
python src/big_portal_update/author_references_extractor.py \
  -a data/profiles.csv \
  -b /home/alebg/philosophie-ch/Dropbox/philosophie-ch/biblio/biblio-v10-table.ods \
  -c data/bibliography-with-closures.tsv \
  -o data/profiles-with-bibkeys.csv \
  -e utf-8

python src/big_portal_update/truncate_long_cells.py \
  -i data/profiles-with-bibkeys.csv \
  -o data/profiles-with-bibkeys-sheets.csv \
  -e utf-8
```

**Input columns**: `id`, `_biblio_name`
**Bibliography match**: `author_ids` (comma-separated, matching any ID in the set)
**Output columns**: `biblio_keys`, `biblio_keys_further_references`, `biblio_dependencies_keys`
**Results**: 7,395 profiles

## Understanding the Output Columns

### For Publishers & Journals:
- **`_references_keys`**: Direct bibkeys where publisher-id/journal-id matches
- **`_further_references_keys`**: Transitive closure of citations in title+notes of main bibkeys
- **`_references_dependencies_keys`**: Transitive closure including crossrefs and further_note

### For Profiles (Authors):
- **`biblio_keys`**: Direct bibkeys where author ID appears in author_ids
- **`biblio_keys_further_references`**: Transitive closure of citations in title+notes
- **`biblio_dependencies_keys`**: Transitive closure including crossrefs and further_note

### Difference between Further References and Dependencies:
- **Further references**: Citations found in `title` + `notes` fields (transitively closed)
- **Dependencies**: Citations from `title` + `notes` + `further_note` + `crossref` (transitively closed)

Dependencies include everything in further references PLUS:
1. Crossref entries (parent/container works like book chapters → book)
2. Citations in the `further_note` field

Example: A book chapter would have the book in dependencies via crossref, but not in further references unless explicitly cited.

## Google Sheets Compatibility

The `truncate_long_cells.py` script creates `-sheets.csv` versions where cells >49,000 characters are replaced with `[TOO LONG]` for Google Sheets compatibility.

**Cells truncated**:
- Publishers: 1 cell (Oxford University Press)
- Journals: 1 cell (ID 1748)
- Profiles: 0 cells

## Scripts

- **`publisher_references_extractor.py`**: Extract publisher bibkeys and closures
- **`journal_references_extractor.py`**: Extract journal bibkeys and closures
- **`author_references_extractor.py`**: Extract author/profile bibkeys and closures
- **`truncate_long_cells.py`**: Create Google Sheets compatible versions

## Common Issues

### Polars Reading Columns as Null
If polars reads columns as all null, add `infer_schema_length=0` to force string types:
```python
df = pl.read_ods(file, has_header=True, drop_empty_rows=True, infer_schema_length=0)
```

### Column Name Mismatches
- Bibliography closures TSV uses hyphens: `_further-references`, `_depends-on`
- Entity CSVs use underscores: `_references_keys`, `biblio_keys`
- Make sure to map correctly when writing output

## Next Steps

Phase 3 will use `ref_pipe` to generate HTML files from these CSVs. See `docs/todo/big-portal-update.md` for details.
