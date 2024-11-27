import csv
import os
from pathlib import Path
from typing import FrozenSet, Tuple
from src.sdk.ResultMonad import Err, Ok, runwrap, runwrap_or, try_except_wrapper
from src.sdk.utils import get_logger, lginf, remove_extra_whitespace, pretty_format_frozenset
from src.ref_pipe.models import BibEntity, TMDReport, THTMLReport


lgr = get_logger("Filesystem I/O")


@try_except_wrapper(lgr)
def parse_bibkeys(bibkeys_s: str) -> FrozenSet[str]:

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


def load_raw_bibentities_csv(input_file: str, encoding: str) -> list[RawBibEntity]:

    frame = f"load_bibentities_csv"
    lginf(frame, f"Reading CSV file '{input_file}' with encoding '{encoding}'...", lgr)

    if not os.path.exists(input_file):
        msg = f"The input file '{input_file}' does not exist."
        raise FileNotFoundError(msg)

    with open(input_file, "r", encoding=encoding) as f:
        reader = csv.DictReader(f)

        required_columns = ["id", "entity_key", "url_endpoint", "main_bibkeys", "further_references", "depends_on"]

        if reader.fieldnames is None or not all(col in reader.fieldnames for col in required_columns):
            msg = f"The CSV file needs to have a header row with at least the following columns:\n\t{', '.join(required_columns)}."
            raise ValueError(msg)

        rows = tuple(reader)  # Read all rows into memory

    output: list[RawBibEntity] = []
    for row in rows:
        # Sanitize inputs
        main_bibkeys = runwrap(parse_bibkeys(row["main_bibkeys"]))
        further_references_raw = runwrap_or(parse_bibkeys(row["further_references"]), frozenset())
        depends_on_raw = runwrap_or(parse_bibkeys(row["depends_on"]), frozenset())

        output.append(
            (
                f"{row['id']}",
                f"{row['entity_key']}",
                f"{row['url_endpoint']}",
                main_bibkeys,
                further_references_raw,
                depends_on_raw,
            )
        )

    return output


def process_raw_bibentity(raw_bibentity: RawBibEntity) -> BibEntity:
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

    return BibEntity(
        id=bib_id,
        entity_key=entity_key,
        url_endpoint=url_endpoint,
        main_bibkeys=main_bibkeys,
        further_references=further_references,
        depends_on=depends_on,
    )


@try_except_wrapper(lgr)
def load_bibentities(input_file: str, encoding: str) -> tuple[BibEntity, ...]:

    frame = f"load_bibentities"
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

            raw_bibentities = load_raw_bibentities_csv(input_file, encoding)

        case (_, _):
            raise ValueError(f"Unsupported file extension '{extension}'.")

    return tuple(process_raw_bibentity(raw_bibentity) for raw_bibentity in raw_bibentities)


@try_except_wrapper(lgr)
def generate_report(main_output: TMDReport | THTMLReport, output_folder: str, encoding: str) -> None:

    frame = f"generate_report"
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
                "status",
                "error_message",
                "model_dump",
            ]
        )

        for entity, write_result in main_output:
            match write_result:
                case Ok(out=out_e):
                    if out_e.entity_key != entity.entity_key:
                        status = "error"
                        err_msg = f"The key '{entity.entity_key}' does not match the output's key '{out_e.entity_key}'"

                    else:
                        status = "success"
                        err_msg = ""

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
                    status,
                    err_msg,
                    dump,
                ]
            )

    lginf(frame, f"Success! Report written to {report_filename}.", lgr)

    return None
