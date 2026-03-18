# biblioUtils -- General Context

## What this project is

**biblioUtils** is a Python 3.13 toolkit for managing, processing, and publishing the academic bibliography of [Philosophie.ch](https://philosophie.ch), a Swiss philosophy portal. It covers the full lifecycle of bibliographic data: ingesting records, resolving cross-references and dependencies, registering DOIs via the Crossref API, and producing HTML output for the portal.

Performance-critical work (transitive-closure computation on dependency graphs) is implemented in Rust and exposed to Python through `pyo3` / `maturin` (see `rust_crate/`).


## Repository layout

```
biblioUtils/
  src/            # All source code (Python package)
  rust_crate/     # Rust library exposed to Python via pyo3/maturin
  tests/          # Pytest test suite
  data/           # Data files (input spreadsheets, CSVs, etc.)
  docs/           # Documentation
  pyproject.toml  # Build config (hatchling), dependencies, tool settings
```


## src/ -- module overview

| Module | Purpose |
|---|---|
| `ref_pipe/` | **References pipeline** -- the central workflow. Reads a CSV of bibliographic entities (profiles, articles, journals, publishers, pages), loads a `.bib` bibliography file, resolves cross-references and dependencies, generates per-entity HTML snippets via a Dockerized Pandoc/CSL toolchain, and writes a processing report. Entry point: `main_local.py`. |
| `bib_deps/` | **Bibliography dependencies**. Parses `\citet` / `crossref` / `further_note` fields from `.bib` entries to build dependency graphs, then computes their transitive closure (delegating to the Rust crate for speed). |
| `utils/` | Standalone utilities: TeX-to-UTF8 and UTF8-to-TeX conversion, philosophy-aware titlecasing, bibkey parsing/cleanup, duplicate-key detection, string replacement maps, markdown reference handling, XML analysis, and more. |
| `crossref_doi_api/` | Crossref/DOI integration: batch DOI registration and updates, CSV-to-XML deposit-file generation, submission-status checking, and bibliography enrichment from DOI metadata. |
| `dltc_backcatalog/` | Management of the *Dialectica* journal back-catalog: DOI lookup, metadata extraction, YAML-based data repository, and Crossref gateway. |
| `big_portal_update/` | Bulk-update scripts that extract reference lists for authors, publishers, journals, and pages from ODS/spreadsheet sources. |
| `ad_hoc/` | One-off scripts (e.g., generating cover images, merging PDFs). |
| `doi_chase/` | DOI resolution helpers. |


## Key domain concepts

- **Bibkey**: A unique string identifier for a bibliography entry (e.g., `smith2020ontology`). Bibkeys are the primary unit of reference throughout the system.
- **BibEntity**: A portal entity (profile, article, journal, publisher, or page) that has associated bibliography references (`main_bibkeys`, `further_references`, `depends_on`).
- **Bibliography**: The master `.bib` file, loaded and indexed by bibkey.
- **Dependencies**: Entries can reference other entries via `crossref` or `\citet{}` commands. The system resolves these transitively to compute complete dependency sets.
- **References pipeline** (`ref_pipe`): The end-to-end process that takes a CSV of entities, matches them against the bibliography, computes dependencies, generates HTML, and produces a report.


## Technology stack

- **Python 3.13** with type hints and `mypy --strict`
- **Rust** (via `maturin` / `pyo3`) for transitive closure computation
- **Polars** for tabular data manipulation
- **Pydantic** for data validation (Result monad, models)
- **Docker** (Pandoc + CSL) for HTML compilation from Markdown
- **BeautifulSoup** for HTML parsing
- **habanero** for Crossref API interaction
- **pylatexenc / TexSoup** for LaTeX parsing and conversion
- **pytest**, **mypy**, **black** for testing, type checking, and formatting


## Development quick start

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install .[dev]

# Build the Rust extension
cd rust_crate && maturin build --release && cd ..

# Quality checks
mypy .
pytest
black .
```
