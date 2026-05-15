from dataclasses import dataclass


SPPS_ISSN = "1662-937X"

_LICENSE_HISTORY: list[tuple[int, str, str]] = [
    (2005, "CC BY 3.0", "https://creativecommons.org/licenses/by/3.0/"),
    (2026, "CC BY 4.0", "https://creativecommons.org/licenses/by/4.0/"),
]


def resolve_license(year: int) -> tuple[str, str]:
    name = _LICENSE_HISTORY[0][1]
    url = _LICENSE_HISTORY[0][2]
    for from_year, n, u in _LICENSE_HISTORY:
        if from_year <= year:
            name, url = n, u
    return name, url


@dataclass(frozen=True, slots=True)
class SppsMetadata:
    title: str
    authors: tuple[str, ...]
    date_year: int
    number: str
    how_to_cite_html: str
    license_name: str
    license_url: str
    copyright_holder: str
