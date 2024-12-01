import csv
import os
from pathlib import Path
from typing import Dict, FrozenSet, Tuple
from src.ref_pipe.bibkey_utils import BibkeyError, parse_bibkey, validate_bibkeys
from src.sdk.ResultMonad import Err, Ok, runwrap, runwrap_or, try_except_wrapper
from src.sdk.utils import get_logger, lginf, remove_extra_whitespace, pretty_format_frozenset
from src.ref_pipe.models import (
    SUPPORTED_ENTITY_TYPES,
    BibEntity,
    Bibliography,
    THTMLReport,
    TSupportedEntity,
    TBibEntityAttribute,
)


lgr = get_logger("Filesystem I/O")


@try_except_wrapper(lgr)
def extract_bibkeys(bibkeys_s: str) -> FrozenSet[str]:

    if bibkeys_s is None or bibkeys_s == "":
        return frozenset()

    return frozenset({remove_extra_whitespace(k) for k in bibkeys_s.split(",")})


type RawBibEntity = Tuple[
    str,  # id
    str,  # entity_key
    str,  # url_endpoint
    FrozenSet[str],  # main_bibkeys
    FrozenSet[str],  # further_references
    FrozenSet[str],  # depends_on
]

"""
The following dictionary maps the attributes of the external CSV file to the attributes of the BibEntity class.
"""
EXTERNAL_COLUMN: Dict[TSupportedEntity, Dict[TBibEntityAttribute, str]] = {
    "profile": {
        "id": "id",
        "entity_key": "biblio_name",
        "url_endpoint": "login",
        "main_bibkeys": "biblio_keys",
        "further_references": "biblio_keys_further_references",
        "depends_on": "biblio_dependencies_keys",
    },
    "article": {
        "id": "id",
        "entity_key": "_article_bib_key",
        "url_endpoint": "urlname",
        "main_bibkeys": "ref_bib_keys",
        "further_references": "_further_refs",
        "depends_on": "_depends_on",
    },
}


def load_raw_bibentities_csv(input_file: str, encoding: str, entity_type: TSupportedEntity) -> list[RawBibEntity]:

    frame = f"load_bibentities_csv"
    lginf(frame, f"Reading CSV file '{input_file}' with encoding '{encoding}' for entity type '{entity_type}'...", lgr)

    if not os.path.exists(input_file):
        msg = f"The input file '{input_file}' does not exist."
        raise FileNotFoundError(msg)

    with open(input_file, "r", encoding=encoding) as f:
        reader = csv.DictReader(f)

        required_columns = tuple(col for col in EXTERNAL_COLUMN[entity_type].values())

        if reader.fieldnames is None or not all(col in reader.fieldnames for col in required_columns):
            msg = f"The CSV file needs to have a header row with at least the following columns:\n\t{', '.join(required_columns)}."
            raise ValueError(msg)

        rows = tuple(reader)  # Read all rows into memory

    output: list[RawBibEntity] = []

    id_column = EXTERNAL_COLUMN[entity_type]["id"]
    entity_key_column = EXTERNAL_COLUMN[entity_type]["entity_key"]
    url_endpoint_column = EXTERNAL_COLUMN[entity_type]["url_endpoint"]
    main_bibkeys_column = EXTERNAL_COLUMN[entity_type]["main_bibkeys"]
    further_references_column = EXTERNAL_COLUMN[entity_type]["further_references"]
    depends_on_column = EXTERNAL_COLUMN[entity_type]["depends_on"]

    for row in rows:
        # Sanitize inputs
        main_bibkeys = runwrap(extract_bibkeys(row[main_bibkeys_column]))
        further_references_raw = runwrap_or(extract_bibkeys(row[further_references_column]), frozenset())
        depends_on_raw = runwrap_or(extract_bibkeys(row[depends_on_column]), frozenset())

        output.append(
            (
                f"{row[
                    id_column
                ]}",
                f"{row[
                    entity_key_column
                ]}",
                f"{row[
                    url_endpoint_column
                ]}",
                main_bibkeys,
                further_references_raw,
                depends_on_raw,
            )
        )

    return output


def process_raw_bibentity(raw_bibentity: RawBibEntity, bibliography: Bibliography) -> BibEntity:
    bib_id, entity_key, url_endpoint, main_bibkeys, further_references_raw, depends_on_raw = raw_bibentity

    # lgr.info(f"main_bibkeys: {pretty_format_frozenset(main_bibkeys)}")
    # lgr.info(f"further_references_raw: {pretty_format_frozenset(further_references_raw)}")
    # lgr.info(f"depends_on_raw: {pretty_format_frozenset(depends_on_raw)}")

    # Force uniqueness of sets of bibkeys to prevent unnecessary processing
    further_references = further_references_raw - main_bibkeys
    _depends_on = depends_on_raw - main_bibkeys
    depends_on = _depends_on - further_references

    # lgr.info(f"further_references: {pretty_format_frozenset(further_references)}")
    # lgr.info(f"depends_on: {pretty_format_frozenset(depends_on)}")


    # Sanitize bibkeys
    bibentity_bibkeys = main_bibkeys | further_references | depends_on

    # Assert that all bibkeys have the standard structure
    validate_bibkeys(bibentity_bibkeys, bibliography.bibkey_index_dict)

    # Assert that all bibkeys are present in the bibliography
    if not bibentity_bibkeys.issubset(bibliography.bibkeys):
        missing_bibkeys = bibentity_bibkeys - bibliography.bibkeys
        raise ValueError(
            f"Missing bibkeys for '{entity_key}' in the bibliography: {', '.join(sorted(missing_bibkeys))}"
        )

    return BibEntity(
        id=bib_id,
        entity_key=entity_key,
        url_endpoint=url_endpoint,
        main_bibkeys=main_bibkeys,
        further_references=further_references,
        depends_on=depends_on,
    )


@try_except_wrapper(lgr)
def load_bibentities(input_file: str, encoding: str, entity_type: TSupportedEntity, bibliography: Bibliography) -> tuple[BibEntity, ...]:

    frame = f"load_bibentities"

    if entity_type not in SUPPORTED_ENTITY_TYPES:
        raise ValueError(f"Unsupported entity type '{entity_type}'.")

    lginf(frame, f"Reading input file '{input_file}'...", lgr)

    input_path = Path(input_file)
    if not input_path.exists():
        msg = f"The input file '{input_file}' does not exist."
        raise FileNotFoundError(msg)

    extension = input_path.suffix

    match (extension, encoding):
        case (".csv", _):
            if encoding is None:
                raise ValueError("The encoding must be specified for CSV files.")

            raw_bibentities = load_raw_bibentities_csv(input_file, encoding, entity_type)

        case (_, _):
            raise ValueError(f"Unsupported file extension '{extension}'.")

    return tuple(process_raw_bibentity(raw_bibentity, bibliography) for raw_bibentity in raw_bibentities)


def _extract_bibkey(line: str) -> str:
    bracket_split = line.split("{")
    comma_split = bracket_split[1].split(",")
    bibkey = comma_split[0]
    return remove_extra_whitespace(bibkey)


@try_except_wrapper(lgr)
def load_bibliography(bibliography_file: str) -> Bibliography:

    frame = f"load_bibliography_bibkeys"
    lginf(frame, f"Reading bibliography file '{bibliography_file}'...", lgr)

    if not os.path.exists(bibliography_file):
        msg = f"The bibliography file '{bibliography_file}' does not exist."
        raise FileNotFoundError(msg)

    with open(bibliography_file, "r") as f:
        bibkey_linenum_d = {_extract_bibkey(line): i for i, line in enumerate(f.readlines())}

    with open(bibliography_file, "r") as f:
        bibkeys = frozenset({_extract_bibkey(line) for line in f.readlines()})


    with open(bibliography_file, "r") as f:
        bibliography_len = len(f.readlines())

    bibkeys_len = len(bibkeys)

    # Sanitize bibliography
    if bibkeys_len != len(bibkey_linenum_d):
        raise ValueError(
            f"The number of bibkeys and the number of line numbers should be the same. This means that bibkeys are not unique. Found {len(bibkeys)} bibkeys but {len(bibkey_linenum_d)} line numbers in the bibliography. Fix the consistency of your bibliography and try again."
        )

    if bibkeys_len != bibliography_len:
        raise ValueError(
            f"The number of bibkeys ({bibkeys_len}) should be the same as the number of lines in the bibliography ({bibliography_len}). This means that some lines didn't contain bibkeys at all, or your bibliography file is not a valid bib file. Fix the consistency of your bibliography and try again."
        )

    # Assert that all bibkeys have the standard structure
    validate_bibkeys(bibkeys, bibkey_linenum_d)

    with open(bibliography_file, "r") as f:
        content_tuple = tuple(f.readlines())

    return Bibliography(
        bibkeys=bibkeys,
        bibkey_index_dict=bibkey_linenum_d,
        content=content_tuple,
    )


@try_except_wrapper(lgr)
def generate_report_for_html_files(main_output: THTMLReport, output_folder: str, encoding: str) -> None:

    frame = f"generate_report_for_html_files"
    lginf(frame, f"Generating report for the markdown file generation...", lgr)

    os.makedirs(output_folder, exist_ok=True)
    report_filename = f"{output_folder}/ref_pipe_report.csv"

    with open(report_filename, "w", encoding=encoding) as f:
        writer = csv.writer(f, quotechar='"')
        writer.writerow(
            [
                "id",
                "entity_key",
                "main_bibkeys",
                "further_references",
                "depends_on",
                "references_html_file",
                "further_references_html_file",
                "status",
                "error_message",
                "model_dump",
            ]
        )

        for entity, write_result in main_output:
            references_html_file = ""
            further_references_html_file = ""
            status = ""
            err_msg = ""

            match write_result:
                case Ok(out=out_e):
                    if out_e.entity_key != entity.entity_key:
                        status = "error"
                        err_msg = f"The key '{entity.entity_key}' does not match the output's key '{out_e.entity_key}'"

                    else:
                        status = "success"
                        references_html_file = out_e.html.references_filename
                        further_references_html_file = out_e.html.further_references_filename

                case Err(message=message, code=code):
                    status = "error"
                    err_msg = message

            dump = entity.dump()

            writer.writerow(
                [
                    entity.id,
                    entity.entity_key,
                    pretty_format_frozenset(entity.main_bibkeys),
                    pretty_format_frozenset(entity.further_references),
                    pretty_format_frozenset(entity.depends_on),
                    references_html_file,
                    further_references_html_file,
                    status,
                    err_msg,
                    dump,
                ]
            )

    lginf(frame, f"Success! Report written to {report_filename}.", lgr)

    return None
