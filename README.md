# Bibliography Utils for Philosophie.ch

## Development

It is recommended that you create a virtual environment to install the dependencies.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install .[dev]
```

Then, this project contains some custom made Rust crates that are used as python libraries, using the python package `maturin` with the `pyo3` backend.
To build the Rust library, you need to have Rust installed on your machine, then run the following:

```bash
cd rust_crate
maturin build --release
```

This will install the Rust library in the virtual environment, which allows it to be used as any other Python library.
It is a typed library (see `rust_crate/rust_crate.pyi`), so it doesn't conflict with the `mypy` static type checker.


### Typing, Tests, Formatting

To assure the quality of your code, please run the following commands before pushing your changes.
At the root of the project:

1. Static type checking:

```bash
mypy .
```
Fix any errors before proceeding.

2. Tests:

```bash
pytest
```
Fix any errors before proceeding.

3. Formatting:

```bash
black .
```
Note: will format the code in place, with no confirmation.
