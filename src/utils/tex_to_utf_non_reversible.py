#!/usr/bin/env python3

"""
Replaces LaTeX special characters with their Unicode equivalents.

If after applying to a CSV it breaks, do the following, and open the CSV by stating that " is the delimiter for strings:

sed 's/^"//;s/"$//' [FILE] | sed 's/.*/"&"/' > [OUTPUT_FILE]
"""

import polars as pl

from pathlib import Path
from typing import Generator, Tuple
from pylatexenc.latex2text import LatexNodes2Text

from src.sdk.utils import get_logger, remove_extra_whitespace, lginf


lgr = get_logger("TeX to UTF -- Non-Reversible Conversion")


LATEX_TO_UNICODE_MAP = {
    r"{\'e}": "é",
    r"{\'E}": "É",
    r"{\'a}": "á",
    r"{\'A}": "Á",
    r"{\'o}": "ó",
    r"{\'u}": "ú",
    r"{\'{u}}": "ú",
    r"{\'n}": "ń",
    r"{\'s}": "ś",
    r"{\'{\i}}": "í",
    r"{\'y}": "ý",
    r"{\'c}": "ć",
    r"{\'C}": "Ć",
    r"{\'z}": "ź",
    r"{\'S}": "Ś",
    r"{\'I}": "Í",
    r"{\'r}": "ŕ",
    r"{\`e}": "è",
    r"{\`E}": "È",
    r"{\`a}": "à",
    r"{\`A}": "À",
    r"{\`u}": "ù",
    r"{\`{\i}}": "ì",
    r"{\`o}": "ò",
    r"{\^A}": "Â",
    r"{\^o}": "ô",
    r"{\{o}}": "ô",
    r"{\^e}": "ê",
    r"{\^E}": "Ê",
    r"{\^i}": "î",
    r"{\^{\i}}": "î",
    r"{\^a}": "â",
    r"{\^u}": "û",
    r"{\^e}": "ê",
    r"{\^w}": "ŵ",
    r"{\^S}": "Ŝ",
    r"{\^Z}": "Ž",
    r"{\^g}": "ĝ",
    r"{\"e}": "ë",
    r"{\"{\i}}": "ï",
    r"{\c{c}}": "ç",
    r"{\c{C}}": "Ç",
    r"{\c{e}}": "ȩ",
    r"{\c{S}}": "Ş",
    r"{\c{s}}": "ş",
    r"{\k{e}}": "ę",
    r"{\k{a}}": "ą",
    r"{\l}": "ł",
    r"{\L}": "Ł",
    r"{\o}": "ø",
    r"{\O}": "Ø",
    r"{\dj}": "đ",
    r"{\={e}}": "ē",
    r"{\={E}}": "Ē",
    r"{\={A}}": "Ā",
    r"{\={a}}": "ā",
    r"{\=a}": "ā",
    r"{\={i}}": "ī",
    r"{\=i}": "ī",
    r"{\={I}}": "Ī",
    r"{\={o}}": "ō",
    r"{\={O}}": "Ō",
    r"{\={u}}": "ū",
    r"{\={U}}": "Ū",
    r"{\d{a}}": "ạ",
    r"{\d{d}}": "ḍ",
    r"{\d{h}}": "ḥ",
    r"{\d{H}}": "Ḥ",
    r"{\d{n}}": "ṇ",
    r"{\d{m}}": "ṃ",
    r"{\d{s}}": "ṣ",
    r"{\d{S}}": "Ṣ",
    r"{\d{t}}": "ṭ",
    r"{\d{T}}": "Ṭ",
    r"{\d{r}}": "ṛ",
    r"{\d{z}}": "ẓ",
    r"{\.{a}}": "ȧ",
    r"{\.{e}}": "ė",
    r"{\.{G}}": "Ġ",
    r"{\.{z}}": "ż",
    r"{\.Z}": "Ż",
    r"{\.{Z}}": "Ż",
    r"{\aa}": "å",
    r"{\AA}": "Å",
    r"{\u{e}}": "ĕ",
    r"{\v{a}}": "ǎ",
    r"{\v{e}}": "ě",
    r"{\v{s}}": "š",
    r"{\v{S}}": "Š",
    r"{\v{i}}": "ǐ",
    r"{\v{c}}": "č",
    r"{\v{C}}": "Č",
    r"{\v{r}}": "ř",
    r"{\v{Z}}": "Ž",
    r"{\v{z}}": "ž",
    r"{\v{g}}": "ǧ",
    r"{\v{n}}": "ň",
    r"{\~n}": "ñ",
    r"{\.I}": "İ",
    r"{\AA}": "Å",
    r"{\^i}": "î",
    r"{\^s}": "ŝ",
    r"{\.{I}}": "İ",
    r"{\'I}": "Í",
    r"{\'O}": "Ó",
    r"{\={O}}": "Ō",
    r"{\c{S}}": "Ş",
    r"{\c{s}}": "ş",
    r"{\"a}": "ä",
    r"{\"A}": "Ä",
    r"{\"e}": "ë",
    r"{\"E}": "Ë",
    r"{\"i}": "ï",
    r"{\"I}": "Ï",
    r"{\"o}": "ö",
    r"{\"O}": "Ö",
    r"{\"u}": "ü",
    r"{\"U}": "Ü",
    r"{\"y}": "ÿ",
    r"{\"Y}": "Ÿ",
    r"{\'r}": "ŕ",
    r"{\c{n}}": "ņ",
    r"{\i}": "ı",
    r"{\ae}": "æ",
    r"{\AE}": "Æ",
    r"{\oe}": "œ",
    r"{\OE}": "Œ",
    r"{\~n}": "ñ",
    r"{\~a}": "ã",
    r"{\~u}": "ũ",
    r"{\~o}": "õ",
    r"\&": "&",
    r"~": "   ",
    r"\dots": "…",
    r"\S": "§",
    r"$\Delta$": "Δ",
    r"$\Theta$": "Τ",
    r"$\Gamma$": "Γ",
    r"$\lambda$": "Λ",
    r"$\omega$": "ω",
    r"$\mu$": "μ",
    r"$\Box$": "□",
    r"$\Diamond$": "◊",
    r"$T^\omega$": "T^ω",
    r"$\neq$": "≠",
    r"$\neg$": "¬",
    r"$\sim$": "≈",
    r"$\epsilon$": "ε",
    r"$\infty$": "∞",
    r"$_{\infty}$": "_∞",
    r"$^{\infty}$": "^∞",
    r"$S$": "𝑆",
    r"$P$": "𝑃",
    r"$T$": "𝑇",
    r"$a$": "𝑎",
    r"$p$": "𝒑",
    # Order matters!
    r"{": "",
    r"}": "",
    r"^": "",
    r"_": "",
    r"\$": "",
}

CLEANUP_MAP = {
    r"Textsubscript": "textsubscript",
    r"TEXTSUBSCRIPT": "textsubscript",
    r"Textsuperscript": "textsuperscript",
    r"TEXTSUPERSCRIPT": "textsuperscript",
    r"Textsc": "textsc",
    r"TEXTSC": "textsc",
    r"Emph": "emph",
    r"EMPH": "emph",
    r"Citet": "citet",
    r"CITET": "citet",
    r"Citep": "citep",
    r"CITEP": "citep",
    r'\""u': "ü",  # in case csv delimiter is " itself
    r'\""o': "ö",  # in case csv delimiter is " itself
    r'\""a': "ä",  # in case csv delimiter is " itself
    r'\""e': "ë",  # in case csv delimiter is " itself
    r'\""i': "ï",  # in case csv delimiter is " itself
    r'\""U': "Ü",  # in case csv delimiter is " itself
    r'\""O': "Ö",  # in case csv delimiter is " itself
    r'\""A': "Ä",  # in case csv delimiter is " itself
    r'\""E': "Ë",  # in case csv delimiter is " itself
    r'\""I': "Ï",  # in case csv delimiter is " itself
    r"\emph": "",
    r"\,": "",
}

EXTERNAL_CLEANUP_MAP = {
    r"`": "'",  # Replace backticks with single quotes
}


def tex2utf_naive(text: str) -> str:
    """
    Replace LaTeX special characters with their Unicode equivalents.
    """
    for latex, unicode in LATEX_TO_UNICODE_MAP.items():
        text = text.replace(latex, unicode)

    for cleanup, replacement in CLEANUP_MAP.items():
        text = text.replace(cleanup, replacement)

    # Clean all multiple spaces
    line = " ".join(text.split())

    return line


def tex2utf_external_postprocess(text: str) -> str:
    """
    Post-process the text after using pylatexenc to remove any unwanted characters.
    """
    for latex, unicode in EXTERNAL_CLEANUP_MAP.items():
        post_processed = text.replace(latex, unicode)

    return post_processed


def tex2utf_external(latex_input: str) -> str:
    """
    Replace LaTeX special characters with their Unicode equivalents using the pylatexenc library.
    """
    latex_input = LatexNodes2Text().latex_to_text(latex_input)

    stripped = remove_extra_whitespace(latex_input)

    post_processed = tex2utf_external_postprocess(stripped)

    return post_processed


type TReadInput = Tuple[
    Generator[str, None, None],  # lines
    int,  # number of lines
]


def read_input_file(file: str, encoding: str | None, column: str | None) -> TReadInput:
    """
    Read the input file and return a generator of lines.
    """

    path = Path(file)

    if not path.exists():
        raise FileNotFoundError("The input file does not exist.")

    extension = path.suffix

    match (extension, encoding, column):
        case (".txt", encoding, None) if (isinstance(encoding, str) and encoding != ""):
            with open(file, "r", encoding=encoding) as f:
                text = f.read()
                lines = text.splitlines()

        case (".ods", _, column) if (isinstance(column, str) and column != ""):
            df = pl.read_ods(file, has_header=True)
            lines = df[column].to_list()

        case _:
            raise ValueError(
                "The input file must be a .txt or .ods file. For a .txt file, the encoding must be specified. For a .ods file, the column name must be specified."
            )

    result = (line for line in lines), len(lines)
    return result


def main(file: str, encoding: str | None, column: str | None) -> str:
    try:
        frame = "main"

        lginf(frame, f"Reading file '{file}'", lgr)

        lines, num_lines = read_input_file(file, encoding, column)

        lginf(frame, f"Processing {num_lines} lines", lgr)
        processed_lines = (tex2utf_external(line) for line in lines)

        lginf(frame, "Joining the output", lgr)

        result = "\n".join(processed_lines)

        return result

    except Exception as e:
        lgr.error(f"Unexpected error: {e}")
        return f"Unexpected error: {e}"


def cli() -> None:
    """
    Command line interface for the tex2utc function.
    """
    import argparse

    parser = argparse.ArgumentParser(description="Replace LaTeX special characters with their Unicode equivalents.")
    parser.add_argument(
        "-f",
        "--file",
        type=str,
        help="File containing LaTeX special characters to convert to Unicode. Supported formats: .txt (each line is a LaTeX string); .ods (will need a column name passed as a parameter).",
        required=True,
    )
    parser.add_argument("-e", "--encoding", type=str, help="Encoding of the file.", required=False)

    parser.add_argument(
        "-c", "--column", type=str, help="Column name in the .ods file to convert to Unicode.", required=False
    )

    file = parser.parse_args().file
    encoding = parser.parse_args().encoding
    column = parser.parse_args().column

    frame = "cli"
    result = main(file, encoding, column)
    lginf(frame, "Writing the output to stdout", lgr)
    print(result)


if __name__ == "__main__":
    cli()
