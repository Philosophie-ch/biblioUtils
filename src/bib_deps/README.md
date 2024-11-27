# Bibliographic Dependencies

Compute different kinds of bibliographic dependencies for the entries of `biblio.bib`.

## Setup & Dependencies

Requirements:

- Python 3.13+
- Rust 1.79+


First, at the root of the whole repository (not in this directoy) ,create a virtual environment and install the dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install .[dev]
# or, to install the development dependencies with exact versions
# use this second alternative if you want to contribute to the project or find any issues
pip install -r requirements-dev.txt

# then, to build the rust part of the project
cd rust_crate
maturin build --release
# or, to build the development version
maturin develop
```


## Usage

To execute the scripts, run the a command like the one below at the root of the project, with the virtual environment active:

```bash
python src/bib_deps/bib_deps_recursive.py ...
```

See the specific scripts in question for more details on their usage.