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
    further_references_closed: Set[str]
    depends_on_closed: Set[str]

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

def compute_transitive_closures(
    entries: Dict[str, RustedBibEntry],
    max_depth: int,
) -> Tuple[Dict[str, Set[str]], Dict[str, Set[str]]]: ...
