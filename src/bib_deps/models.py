from dataclasses import asdict, dataclass
from typing import Literal, TypeAlias

from src.sdk.ResultMonad import Err, Ok

@dataclass
class BaseBibEntry:
    id: str
    bibkey: str
    title: str
    notes: str
    crossref: str
    further_note: str


@dataclass
class CSVBibEntry(BaseBibEntry):
    pass


@dataclass
class ParsedBibEntry(BaseBibEntry):
    further_references_raw: list[str]
    depends_on_raw: list[str]
    status: Literal["success", "error"]
    error_message: str = ""


@dataclass
class ProcessedBibEntry(BaseBibEntry):
    further_references_good: str
    further_references_bad: str
    depends_on_good: str
    depends_on_bad: str
    status: Literal["success", "error"]
    error_message: str = ""

    def dict_dump(self) -> dict[str, str]:
        return asdict(self)


CitetField: TypeAlias = Literal[
    # For further_references
    "title",
    "notes",
    # for depends_on
    "crossref",
    "further_note",
]

@dataclass
class CitetResults:
    notes: Ok[list[str]] | Err
    title: Ok[list[str]] | Err
    further_note: Ok[list[str]] | Err