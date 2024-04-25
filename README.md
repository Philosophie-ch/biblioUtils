# Bibliography Utils for Philosophie.ch

## Development

It is recommended that you create a virtual environment to install the dependencies.

```bash
python3 -m venv .venv_dev
source .venv_dev/bin/activate
pip install .[dev]
```

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
