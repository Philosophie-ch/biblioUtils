import csv
import os
from src.sdk.ResultMonad import Err, Ok, runwrap, runwrap_or, try_except_wrapper
from src.sdk.utils import get_logger, remove_extra_whitespace
from src.ref_pipe.models import Profile, TMDReport, THTMLReport


GMDLGR = get_logger("gen_md")
DTSLGR = get_logger("dltc_env_setup")
CHLLGR = get_logger("compile_html")
MAINLGR = get_logger("main")

lgr = get_logger("utils")


@try_except_wrapper(lgr)
def parse_bibkeys(bibkeys_s: str) -> list[str]:

    return [remove_extra_whitespace(k) for k in bibkeys_s.split(",")]


@try_except_wrapper(lgr)
def load_profiles_csv(input_file: str, encoding: str) -> list[Profile]:

    frame = f"load_profiles_csv"
    lgr.info(f"{frame}\n\tReading CSV file '{input_file}' with encoding '{encoding}'...")

    if not os.path.exists(input_file):
        msg = f"The input file '{input_file}' does not exist."
        raise FileNotFoundError(msg)

    with open(input_file, "r", encoding=encoding) as f:
        reader = csv.DictReader(f)

        required_columns = ["id", "lastname", "_biblio_name", "biblio_keys", "biblio_dependencies_keys"]

        if reader.fieldnames is None or not all(col in reader.fieldnames for col in required_columns):
            msg = f"The CSV file needs to have a header row with at least the following columns:\n\t{', '.join(required_columns)}."
            raise ValueError(msg)

        rows = list(reader)  # Read all rows into memory

    output = [
        Profile(
            id=row["id"],
            lastname=row["lastname"],
            biblio_name=row["_biblio_name"],
            biblio_keys=runwrap(parse_bibkeys(row["biblio_keys"])),
            biblio_keys_further_references=runwrap_or(parse_bibkeys(row["biblio_keys_further_references"]), []),
            biblio_dependencies_keys=runwrap_or(parse_bibkeys(row["biblio_dependencies_keys"]), []),
        )
        for row in rows
    ]

    return output


@try_except_wrapper(lgr)
def generate_report(main_output: TMDReport | THTMLReport, output_folder: str, encoding: str) -> None:

    frame = f"generate_report"
    lgr.info(f"{frame}\n\tGenerating report for the markdown file generation...")
    os.makedirs(output_folder, exist_ok=True)

    report_filename = f"{output_folder}/gen_md_report.csv"

    with open(report_filename, "w", encoding=encoding) as f:
        writer = csv.writer(f, quotechar='"')
        writer.writerow(
            [
                "id",
                "lastname",
                "biblio_keys",
                "biblio_keys_further_references",
                "biblio_dependencies_keys",
                "status",
                "error_message",
                "model_dump",
            ]
        )

        for profile, write_result in main_output:
            match write_result:
                case Ok(out=out_p):
                    if out_p.biblio_name != profile.biblio_name:
                        status = "error"
                        err_msg = f"The profile name '{profile.biblio_name}' does not match the output profile name '{out_p.biblio_name}'"

                    else:
                        status = "success"
                        err_msg = ""

                case Err(message=message, code=code):
                    status = "error"
                    err_msg = message

            dump = profile.dump()

            writer.writerow(
                [
                    profile.id,
                    profile.lastname,
                    profile.biblio_keys,
                    ",".join(profile.biblio_keys_further_references),
                    ",".join(profile.biblio_dependencies_keys),
                    status,
                    err_msg,
                    dump,
                ]
            )

    lgr.info(f"Success! Report written to {report_filename}.")

    return None
