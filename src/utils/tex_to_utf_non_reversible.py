#!/usr/bin/env python3

"""
Replaces LaTeX special characters with their Unicode equivalents.

If after applying to a CSV it breaks, do the following, and open the CSV by stating that " is the delimiter for strings:

sed 's/^"//;s/"$//' [FILE] | sed 's/.*/"&"/' > [OUTPUT_FILE]
"""

import re


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
}


def tex2utc(text: str) -> str:
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


def cli() -> None:
    """
    Command line interface for the tex2utc function.
    """
    import argparse

    parser = argparse.ArgumentParser(description="Replace LaTeX special characters with their Unicode equivalents.")
    parser.add_argument(
        "-f", "--file", type=str, help="File containing LaTeX special characters to convert to Unicode."
    )
    parser.add_argument("-e", "--encoding", type=str, help="Encoding of the file. 'utf-8' by default.", default="utf-8")

    file = parser.parse_args().file
    encoding = parser.parse_args().encoding

    with open(file, "r", encoding=encoding) as f:
        text = f.read()
        lines = text.splitlines()
        processed_lines = [tex2utc(line) for line in lines]
        result = "\n".join(processed_lines)

        print(result)


if __name__ == "__main__":
    cli()
