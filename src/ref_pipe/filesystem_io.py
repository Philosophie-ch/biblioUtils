import csv
import os
from src.sdk.ResultMonad import Err, Ok, runwrap, runwrap_or, try_except_wrapper
from src.sdk.utils import get_logger, lginf, remove_extra_whitespace
from src.ref_pipe.models import BibEntity, TMDReport, THTMLReport


lgr = get_logger("Filesystem I/O")


@try_except_wrapper(lgr)
def parse_bibkeys(bibkeys_s: str) -> list[str]:

    return [remove_extra_whitespace(k) for k in bibkeys_s.split(",")]


@try_except_wrapper(lgr)
def load_bibentities_csv(input_file: str, encoding: str) -> tuple[BibEntity, ...]:

    frame = f"load_bibentities_csv"
    lginf(frame, f"Reading CSV file '{input_file}' with encoding '{encoding}'...", lgr)

    if not os.path.exists(input_file):
        msg = f"The input file '{input_file}' does not exist."
        raise FileNotFoundError(msg)

    with open(input_file, "r", encoding=encoding) as f:
        reader = csv.DictReader(f)

        required_columns = ["id", "entity_key", "biblio_keys", "biblio_dependencies_keys"]

        if reader.fieldnames is None or not all(col in reader.fieldnames for col in required_columns):
            msg = f"The CSV file needs to have a header row with at least the following columns:\n\t{', '.join(required_columns)}."
            raise ValueError(msg)

        rows = tuple(reader)  # Read all rows into memory

    output = tuple(
        BibEntity(
            id=row["id"],
            entity_key=row["entity_key"],
            biblio_keys=runwrap(parse_bibkeys(row["biblio_keys"])),
            biblio_keys_further_references=runwrap_or(parse_bibkeys(row["biblio_keys_further_references"]), []),
            biblio_dependencies_keys=runwrap_or(parse_bibkeys(row["biblio_dependencies_keys"]), []),
        )
        for row in rows
    )

    return output


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
                "biblio_keys",
                "biblio_keys_further_references",
                "biblio_dependencies_keys",
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
                    entity.biblio_keys,
                    ",".join(entity.biblio_keys_further_references),
                    ",".join(entity.biblio_dependencies_keys),
                    status,
                    err_msg,
                    dump,
                ]
            )

    lginf(frame, f"Success! Report written to {report_filename}.", lgr)

    return None
