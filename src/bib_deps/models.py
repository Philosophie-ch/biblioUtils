from dataclasses import dataclass
from typing import Literal

from src.sdk.ResultMonad import Err, Ok


@dataclass(slots=True, frozen=True)
class BaseBibEntry:
    bibkey: str
    title: str
    notes: str
    crossref: str
    further_note: str

    def dict_dump(self) -> dict[str, str]:
        return self.__dict__


type Status = Literal["success", "warning", "error"]


@dataclass(slots=True, frozen=True)
class ParsedBibEntry(BaseBibEntry):
    further_references_raw: list[str]
    depends_on_raw: list[str]
    status: Status
    error_message: str = ""


@dataclass(slots=True, frozen=True)
class ProcessedBibEntry(BaseBibEntry):
    further_references_good: str
    further_references_bad: str
    depends_on_good: str
    depends_on_bad: str
    status: Status
    error_message: str = ""


type CitetField = Literal[
    # For further_references
    "title",
    "notes",
    # for depends_on
    "crossref",
    "further_note",
]


@dataclass(slots=True, frozen=True)
class CitetResults:
    notes: Ok[list[str]] | Err
    title: Ok[list[str]] | Err
    further_note: Ok[list[str]] | Err


@dataclass(slots=True, frozen=True)
class PyTransitivelyClosedBibEntry:
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
