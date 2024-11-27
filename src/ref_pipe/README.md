# HTML References Pipeline

Streamline the automatic production of a HTML file that contains all the references for a bibliographic entity, such as an author, or an article, `biblio.bib`.

## Setup & Dependencies

Requirements:

- Python 3.13+
- Docker


First, create a virtual environment and install the dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install .
# or, to install the development dependencies with exact versions
# use this second alternative if you want to contribute to the project or find any issues
pip install -r requirements-dev.txt
```

Then, populate the `.env` file following the template. You'll also need access to a copy Dialectica's "dltc-workhouse" directory, and access to a docker image with the necessary dependencies to compile Dialectica articles.


## Usage

To execute the pipeline, run the following command at the root of the project, with the virtual environment active:

```bash
PYTHONPATH='.' python src/ref_pipe/main_local.py -i data/rptest.csv -e 'utf-16' -v src/ref_pipe/.env
```