from typing import List, Dict, Set, Tuple

def sum_as_string(a: int, b: int) -> str:
    """
    Returns the sum of two integers as a string.
    """

class RustedBibEntry:
    id: str
    bibkey: str
    title: str
    notes: str
    crossref: str
    further_note: str
    further_references: List[str]
    depends_on: List[str]

    def __new__(
        cls,
        id: str,
        bibkey: str,
        title: str,
        notes: str,
        crossref: str,
        further_note: str,
        further_references: List[str],
        depends_on: List[str],
    ) -> RustedBibEntry: ...
    def __str__(self) -> str: ...

class TransitivelyClosedBibEntry:
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

    def __new__(
        cls,
        id: str,
        bibkey: str,
        title: str,
        notes: str,
        crossref: str,
        further_note: str,
        further_references: str,
        depends_on: str,
        further_references_closed: str,
        depends_on_closed: str,
        max_depth_reached: int,
        status: str,
        error_message: str,
    ) -> TransitivelyClosedBibEntry: ...
    def __str__(self) -> str: ...
    def to_dict(self) -> Dict[str, str]: ...

def find_all_repeated_bibentries(entries: list[RustedBibEntry]) -> list[RustedBibEntry]: ...
def compute_transitive_closures(
    entries: list[RustedBibEntry],
) -> list[TransitivelyClosedBibEntry]: ...
