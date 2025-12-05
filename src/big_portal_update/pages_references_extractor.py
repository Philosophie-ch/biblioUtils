"""
Extract bibkeys for pages from entities (journals or publishers) via _presentation_of mapping.

For pages with _request == "AD HOC", aggregate bibkeys from all entities
listed in _presentation_of column.
"""

import argparse
import csv
from enum import Enum
from pathlib import Path
from typing import Dict, FrozenSet, Tuple

from src.sdk.ResultMonad import light_error_handler, main_try_except_wrapper
from src.sdk.utils import get_logger, lginf, remove_extra_whitespace

lgr = get_logger("Pages References Extractor")
DEBUG = True

type TBibkey = str
type TEntityID = str
type TPageID = str

type TEntityReferences = Tuple[
    FrozenSet[TBibkey],  # references_keys
    FrozenSet[TBibkey],  # further_references_keys
    FrozenSet[TBibkey],  # references_dependencies_keys
]

type TEntitiesMap = Dict[TEntityID, TEntityReferences]

type TPageWithReferences = Tuple[
    TPageID,
    FrozenSet[TBibkey],  # ref_bib_keys (aggregated from entities)
    FrozenSet[TBibkey],  # further_refs (aggregated from entities)
    FrozenSet[TBibkey],  # depends_on (aggregated from entities)
]


class EntityType(Enum):
    JOURNAL = "journal"
    PUBLISHER = "publisher"


@light_error_handler(DEBUG)
def _parse_entity_ids(presentation_of: str) -> FrozenSet[TEntityID]:
    """Parse comma-separated entity IDs from _presentation_of column."""
    if not presentation_of or presentation_of.strip() == "" or presentation_of == "None":
        return frozenset()
    return frozenset(remove_extra_whitespace(eid) for eid in presentation_of.split(","))


@light_error_handler(DEBUG)
def _parse_bibkeys(bibkeys_str: str) -> FrozenSet[TBibkey]:
    """Parse comma-separated bibkeys."""
    if not bibkeys_str or bibkeys_str.strip() == "" or bibkeys_str == "None":
        return frozenset()
    return frozenset(remove_extra_whitespace(bk) for bk in bibkeys_str.split(","))


@light_error_handler(DEBUG)
def load_entities_map(entities_file: str, encoding: str, entity_type: EntityType) -> TEntitiesMap:
    """Load entities with their bibkey references into a map keyed by entity ID."""
    frame = "load_entities_map"

    lginf(frame, f"Loading {entity_type.value}s from '{entities_file}'...", lgr)

    entities_map: TEntitiesMap = {}
    with open(entities_file, "r", encoding=encoding) as f:
        reader = csv.DictReader(f)

        required_columns = ["id", "_references_keys", "_further_references_keys", "_references_dependencies_keys"]
        if reader.fieldnames is None or not all(col in reader.fieldnames for col in required_columns):
            raise ValueError(f"CSV must have columns: {', '.join(required_columns)}")

        for row in reader:
            entity_id = remove_extra_whitespace(f"{row['id']}")
            entities_map[entity_id] = (
                _parse_bibkeys(row["_references_keys"]),
                _parse_bibkeys(row["_further_references_keys"]),
                _parse_bibkeys(row["_references_dependencies_keys"]),
            )

    lginf(frame, f"Loaded {len(entities_map)} {entity_type.value}s", lgr)
    return entities_map


def process_page(
    page_row: Dict[str, str],
    entities_map: TEntitiesMap,
) -> TPageWithReferences | None:
    """
    Extract aggregated bibkeys for a page from its entities.
    Returns None if page should be skipped (_request != "AD HOC").
    """
    page_id = remove_extra_whitespace(f"{page_row['id']}")
    request = f"{page_row.get('_request', '')}".strip()

    # Only process pages with _request == "AD HOC"
    if request != "AD HOC":
        return None

    # Parse entity IDs from _presentation_of
    presentation_of = f"{page_row.get('_presentation_of', '')}"
    entity_ids = _parse_entity_ids(presentation_of)

    # Aggregate bibkeys from all entities
    all_refs: list[FrozenSet[TBibkey]] = []
    all_further: list[FrozenSet[TBibkey]] = []
    all_depends: list[FrozenSet[TBibkey]] = []

    for eid in entity_ids:
        if eid in entities_map:
            refs, further, depends = entities_map[eid]
            all_refs.append(refs)
            all_further.append(further)
            all_depends.append(depends)

    # Union all sets
    ref_bib_keys = frozenset(bk for refs in all_refs for bk in refs)
    further_refs = frozenset(bk for refs in all_further for bk in refs)
    depends_on = frozenset(bk for refs in all_depends for bk in refs)

    return (page_id, ref_bib_keys, further_refs, depends_on)


@light_error_handler(DEBUG)
def _write_output_csv(
    result: dict[TPageID, TPageWithReferences],
    output_file: str,
    encoding: str,
    original_pages: list[Dict[str, str]],
) -> None:
    """Write output CSV preserving original column order, mapping to existing column names."""
    # Convert result to dict keyed by page_id
    result_dict = {
        page_id: {
            "ref_bib_keys": ", ".join(sorted(ref_bib_keys)),
            "_further_refs": ", ".join(sorted(further_refs)),
            "_depends_on": ", ".join(sorted(depends_on)),
        }
        for page_id, ref_bib_keys, further_refs, depends_on in result.values()
    }

    # Preserve original row order and update existing columns
    output_rows = []
    for orig_row in original_pages:
        page_id = remove_extra_whitespace(f"{orig_row['id']}")
        new_row = dict(orig_row)  # Copy original columns

        if page_id in result_dict:
            # Update the existing columns
            new_row["ref_bib_keys"] = result_dict[page_id]["ref_bib_keys"]
            new_row["_further_refs"] = result_dict[page_id]["_further_refs"]
            new_row["_depends_on"] = result_dict[page_id]["_depends_on"]
        else:
            # Page not processed (not AD HOC) - clear the columns
            new_row["ref_bib_keys"] = ""
            new_row["_further_refs"] = ""
            new_row["_depends_on"] = ""

        output_rows.append(new_row)

    # Write with original columns (no new columns added)
    fieldnames = list(original_pages[0].keys())

    with open(output_file, "w", newline="", encoding=encoding) as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(output_rows)


def write_output(
    result: dict[TPageID, TPageWithReferences],
    output_file: str,
    encoding: str,
    original_pages_file: str,
) -> None:
    """Write output preserving original CSV structure."""
    # Load original pages to preserve column order
    with open(original_pages_file, "r", encoding=encoding) as f:
        original_pages = list(csv.DictReader(f))

    path = Path(output_file)
    if path.exists():
        lgr.warning(f"Output file '{output_file}' already exists. Overwriting...")

    _write_output_csv(result, output_file, encoding, original_pages)


@main_try_except_wrapper(lgr)
def main(
    pages_file: str,
    entities_file: str,
    output_file: str,
    encoding: str,
    entity_type: EntityType,
) -> None:
    """Main function to extract page bibkeys from entities."""
    frame = "main"

    # Load entities map
    entities_map = load_entities_map(entities_file, encoding, entity_type)

    # Load and process pages
    lginf(frame, f"Loading and processing pages from '{pages_file}'...", lgr)

    result: dict[TPageID, TPageWithReferences] = {}
    processed_count = 0
    skipped_count = 0
    missing_entities: set[TEntityID] = set()

    with open(pages_file, "r", encoding=encoding) as f:
        reader = csv.DictReader(f)

        required_columns = ["id", "_request", "_presentation_of"]
        if reader.fieldnames is None or not all(col in reader.fieldnames for col in required_columns):
            raise ValueError(f"CSV must have columns: {', '.join(required_columns)}")

        for row in reader:
            # Track missing entities for debugging
            presentation_of = f"{row.get('_presentation_of', '')}"
            entity_ids = _parse_entity_ids(presentation_of)
            for eid in entity_ids:
                if eid and eid not in entities_map:
                    missing_entities.add(eid)

            page_result = process_page(row, entities_map)
            if page_result is not None:
                page_id = page_result[0]
                result[page_id] = page_result
                processed_count += 1
            else:
                skipped_count += 1

    lginf(frame, f"Processed {processed_count} AD HOC pages, skipped {skipped_count} non-AD HOC pages", lgr)

    if missing_entities:
        lgr.warning(
            f"Found {len(missing_entities)} {entity_type.value} IDs in pages not present in entities file: {sorted(missing_entities)[:10]}{'...' if len(missing_entities) > 10 else ''}"
        )

    # Write output
    lginf(frame, f"Writing output to '{output_file}'...", lgr)
    write_output(result, output_file, encoding, pages_file)

    lginf(frame, "Done!", lgr)


def cli() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Extract bibkeys for pages from entities (journals or publishers)")
    parser.add_argument("-p", "--pages-file", required=True, help="Pages CSV file")
    parser.add_argument(
        "-s",
        "--source-file",
        required=True,
        help="Source entities CSV file with bibkeys (journals or publishers)",
    )
    parser.add_argument("-o", "--output-file", required=True, help="Output CSV file")
    parser.add_argument("-e", "--encoding", default="utf-8", help="CSV encoding (default: utf-8)")
    parser.add_argument(
        "-t",
        "--entity-type",
        required=True,
        choices=["journal", "publisher"],
        help="Type of entity to extract from (journal or publisher)",
    )

    args = parser.parse_args()

    entity_type = EntityType(args.entity_type)

    main(
        pages_file=args.pages_file,
        entities_file=args.source_file,
        output_file=args.output_file,
        encoding=args.encoding,
        entity_type=entity_type,
    )


if __name__ == "__main__":
    cli()
