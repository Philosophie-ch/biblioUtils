# HTML References Pipeline

Streamline the automatic production of a HTML file that contains all the references for an author, using `dialectica.bib`.

## Setup & Dependencies

Requirements:

- Python 3.11
- Docker


First, create a virtual environment and install the dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install .
```

Then, populate the `.env` file following the template.


## Usage

To execute the pipeline, run the following command at the root of the project:

```bash
PYTHONPATH='.' python src/ref_pipe/main.py -e src/ref_pipe/.env -c src/ref_pipe/docker-compose.yml
```