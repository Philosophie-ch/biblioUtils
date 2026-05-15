from typing import Any

import requests
from aletk.utils import get_logger

from src.spps_cover.base_types import SppsMetadata, resolve_license

logger = get_logger(__name__)

type JsonDict = dict[str, Any]


def _headers(api_key: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}


def fetch_bibitem(base_url: str, bibkey: str, api_key: str) -> JsonDict:
    url = f"{base_url}/api/v1/bibitems/by-key/{bibkey}"
    resp = requests.get(url, headers=_headers(api_key), timeout=30)
    if resp.status_code == 404:
        raise ValueError(f"No bibitem found for bibkey '{bibkey}'")
    resp.raise_for_status()
    result: JsonDict = resp.json()
    return result


def fetch_authors(base_url: str, bibitem_id: int, api_key: str) -> list[JsonDict]:
    url = f"{base_url}/api/v1/bibitems/{bibitem_id}/authors"
    resp = requests.get(url, headers=_headers(api_key), timeout=30)
    resp.raise_for_status()
    junctions: Any = resp.json()
    if not isinstance(junctions, list):
        junctions = junctions.get("items", junctions.get("data", []))

    junctions.sort(key=lambda j: j.get("position", 0))

    authors: list[JsonDict] = []
    for j in junctions:
        author_key = j.get("author_key")
        if not author_key:
            continue
        author_resp = requests.get(f"{base_url}/api/v1/authors/by-key/{author_key}", headers=_headers(api_key), timeout=30)
        author_resp.raise_for_status()
        authors.append(author_resp.json())
    return authors


def fetch_citation_html(base_url: str, bibkey: str, api_key: str) -> str:
    url = f"{base_url}/api/v1/render"
    resp = requests.post(url, headers=_headers(api_key), json={"bibkeys": [bibkey]}, timeout=30)
    resp.raise_for_status()
    data: Any = resp.json()
    if isinstance(data, dict) and "main_html" in data:
        return str(data["main_html"])
    raise ValueError(f"'{bibkey}': unexpected render response: {data}")


def _require(bibkey: str, field: str, value: Any) -> str:
    if not value:
        raise ValueError(f"'{bibkey}': missing required field '{field}'")
    return str(value)


def lookup_spps_metadata(base_url: str, bibkey: str, api_key: str) -> SppsMetadata:
    bibitem = fetch_bibitem(base_url, bibkey, api_key)
    bibitem_id = int(bibitem["id"])

    title = _require(bibkey, "title_unicode", bibitem.get("title_unicode") or bibitem.get("title"))
    raw_year = bibitem.get("date_year")
    if not raw_year:
        raise ValueError(f"'{bibkey}': missing required field 'date_year'")
    date_year = int(raw_year)
    number = _require(bibkey, "number", bibitem.get("number"))

    authors_data = fetch_authors(base_url, bibitem_id, api_key)
    if not authors_data:
        raise ValueError(f"'{bibkey}': no authors found")
    author_names: list[str] = []
    for a in authors_data:
        given = str(a.get("given_name_unicode") or a.get("given_name") or "")
        family = str(a.get("family_name_unicode") or a.get("family_name") or "")
        full = f"{given} {family}".strip()
        if not full:
            raise ValueError(f"'{bibkey}': author entry has no name")
        author_names.append(full)

    how_to_cite_html = fetch_citation_html(base_url, bibkey, api_key)
    if not how_to_cite_html:
        raise ValueError(f"'{bibkey}': render endpoint returned empty citation")

    license_name, license_url = resolve_license(date_year)
    copyright_holder = ", ".join(author_names)

    return SppsMetadata(
        title=title,
        authors=tuple(author_names),
        date_year=date_year,
        number=number,
        how_to_cite_html=how_to_cite_html,
        license_name=license_name,
        license_url=license_url,
        copyright_holder=copyright_holder,
    )
