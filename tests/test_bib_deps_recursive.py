from rust_crate import RustedBibEntry, compute_transitive_closures, TransitivelyClosedBibEntry

from src.sdk.ResultMonad import Ok


def test_rusted_bib_entry_generator_works() -> None:

    rusted_bibentries = [
        RustedBibEntry(
            bibkey="1",
            title="Title 1",
            notes="Notes 1",
            crossref="",
            further_note="Further note 1",
            further_references=[],
            depends_on=[],
        )
        for _ in range(10)
    ]

    bibentries_with_closures = compute_transitive_closures(rusted_bibentries)

    assert len(bibentries_with_closures) == 10


def test_transitive_closure_works_for_three_bibentries() -> None:

    rusted_bibentries = [
        RustedBibEntry(
            bibkey="1",
            title="Title 1",
            notes="Notes 1",
            crossref="",
            further_note="Further note 1",
            further_references=["2"],
            depends_on=["3"],
        ),
        RustedBibEntry(
            bibkey="2",
            title="Title 2",
            notes="Notes 2",
            crossref="",
            further_note="Further note 2",
            further_references=["3"],
            depends_on=[],
        ),
        RustedBibEntry(
            bibkey="3",
            title="Title 3",
            notes="Notes 3",
            crossref="",
            further_note="Further note 3",
            further_references=[],
            depends_on=["2"],
        ),
    ]

    bibentries_with_closures = compute_transitive_closures(rusted_bibentries)

    assert len(bibentries_with_closures) == 3

    bibkey_to_entry = {entry.bibkey: entry for entry in bibentries_with_closures}

    assert bibkey_to_entry["1"].further_references == "2"
    assert (
        bibkey_to_entry["1"].further_references_closed == "2,3"
        or bibkey_to_entry["1"].further_references_closed == "3,2"
    )
    assert bibkey_to_entry["1"].depends_on == "3"
    assert bibkey_to_entry["1"].depends_on_closed == "2,3" or bibkey_to_entry["1"].depends_on_closed == "3,2"

    assert bibkey_to_entry["2"].further_references == "3"
    assert bibkey_to_entry["2"].further_references_closed == "3"
    assert bibkey_to_entry["2"].depends_on == ""
    assert bibkey_to_entry["2"].depends_on_closed == ""

    assert bibkey_to_entry["3"].further_references == ""
    assert bibkey_to_entry["3"].further_references_closed == ""
    assert bibkey_to_entry["3"].depends_on == "2"
    assert bibkey_to_entry["3"].depends_on_closed == "2"

    # assert also that all other fields returned being the same
    assert bibkey_to_entry["1"].title == "Title 1"
    assert bibkey_to_entry["1"].notes == "Notes 1"
    assert bibkey_to_entry["1"].crossref == ""
    assert bibkey_to_entry["1"].further_note == "Further note 1"

    assert bibkey_to_entry["2"].title == "Title 2"
    assert bibkey_to_entry["2"].notes == "Notes 2"
    assert bibkey_to_entry["2"].crossref == ""
    assert bibkey_to_entry["2"].further_note == "Further note 2"

    assert bibkey_to_entry["3"].title == "Title 3"
    assert bibkey_to_entry["3"].notes == "Notes 3"
    assert bibkey_to_entry["3"].crossref == ""
    assert bibkey_to_entry["3"].further_note == "Further note 3"


def test_bib_deps_recursion_for_transitive_cycles_is_not_infinite() -> None:

    # Create a loop of 3 bibentries
    rusted_bibentries = [
        RustedBibEntry(
            bibkey="1",
            title="Title 1",
            notes="Notes 1",
            crossref="",
            further_note="Further note 1",
            further_references=["2"],
            depends_on=["2"],
        ),
        RustedBibEntry(
            bibkey="2",
            title="Title 2",
            notes="Notes 2",
            crossref="",
            further_note="Further note 2",
            further_references=["3"],
            depends_on=["3"],
        ),
        RustedBibEntry(
            bibkey="3",
            title="Title 3",
            notes="Notes 3",
            crossref="",
            further_note="Further note 3",
            further_references=["1"],
            depends_on=["1"],
        ),
    ]

    bibentries_with_closures = compute_transitive_closures(rusted_bibentries)

    assert len(bibentries_with_closures) == 3

    bibkey_to_entry = {entry.bibkey: entry for entry in bibentries_with_closures}

    assert bibkey_to_entry["1"].further_references == "2"
    assert (
        bibkey_to_entry["1"].further_references_closed == "2,3"
        or bibkey_to_entry["1"].further_references_closed == "3,2"
    )
    assert bibkey_to_entry["1"].depends_on == "2"
    assert bibkey_to_entry["1"].depends_on_closed == "2,3" or bibkey_to_entry["1"].depends_on_closed == "3,2"

    assert bibkey_to_entry["2"].further_references == "3"
    assert (
        bibkey_to_entry["2"].further_references_closed == "1,3"
        or bibkey_to_entry["2"].further_references_closed == "3,1"
    )
    assert bibkey_to_entry["2"].depends_on == "3"
    assert bibkey_to_entry["2"].depends_on_closed == "1,3" or bibkey_to_entry["2"].depends_on_closed == "3,1"
