from dataclasses import asdict, dataclass
from typing import Literal, Set, TypeAlias

from src.sdk.ResultMonad import Err, Ok


@dataclass
class BaseBibEntry:
    id: str
    bibkey: str
    title: str
    notes: str
    crossref: str
    further_note: str

    def dict_dump(self) -> dict[str, str]:
        return self.__dict__


Status: TypeAlias = Literal["success", "warning", "error"]


@dataclass
class ParsedBibEntry(BaseBibEntry):
    further_references_raw: list[str]
    depends_on_raw: list[str]
    status: Status
    error_message: str = ""


@dataclass
class ProcessedBibEntry(BaseBibEntry):
    further_references_good: str
    further_references_bad: str
    depends_on_good: str
    depends_on_bad: str
    status: Status
    error_message: str = ""


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


@dataclass
class PyTransitivelyClosedBibEntry:
    id: str
    bibkey: str
    title: str
    notes: str
    crossref: str
    further_note: str
    further_references: str
    depends_on: str
    further_references_closed: str
    depends_on_closed: str
    max_depth_reached: int
    status: str
    error_message: str
