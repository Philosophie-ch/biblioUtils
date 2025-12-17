from typing import Tuple

from src.sdk.ResultMonad import try_except_wrapper
from src.sdk.utils import get_logger
from src.ref_pipe.models import BibEntity, TSupportedEntity, SUPPORTED_ENTITY_TYPES
import polars as pl

lgr = get_logger("Preprocess Bibentities")


def load_bibliography_dataframe(
    bibliography_file: str,
) -> pl.DataFrame:

    df_raw = pl.read_ods(bibliography_file)

    # Remove duplicates on 'bibkey'
    df = df_raw.unique(subset=["bibkey"], keep="first")

    return df


def _preprocess_journal(bib_df: pl.DataFrame, raw_journal: BibEntity) -> BibEntity:

    journal_df = bib_df.filter(bib_df['journal-id'] == str(raw_journal.id))

    main_bibkeys = frozenset(f"{bibkey}" for bibkey in journal_df["bibkey"].to_list())

    return BibEntity(
        id=raw_journal.id,
        entity_key=raw_journal.entity_key,
        url_endpoint=raw_journal.url_endpoint,
        main_bibkeys=main_bibkeys,
        further_references=raw_journal.further_references,
        depends_on=raw_journal.depends_on,
    )


def _preprocess_publisher(bib_df: pl.DataFrame, raw_publisher: BibEntity) -> BibEntity:
    """
    Preprocess a publisher entity. Unlike journals, publishers don't need
    to extract bibkeys from the ODS - they already have them from the CSV.
    This function is a pass-through that keeps the entity as-is.
    """
    return raw_publisher


@try_except_wrapper(lgr)
def preprocess_bibentities(
    bibliography_file: str, raw_bibentities: Tuple[BibEntity, ...], entity_type: TSupportedEntity
) -> Tuple[Tuple[BibEntity, ...], pl.DataFrame]:
    """
    Preprocess the raw bibentities to ensure they are in the correct format.
    Always loads the bibliography DataFrame for sorting purposes.
    """
    # Load the bibliography ODS file into a Polars DataFrame (needed for all entity types for sorting)
    df: pl.DataFrame = load_bibliography_dataframe(bibliography_file)

    # Preprocess the raw bibentities
    match entity_type:
        case "journal":
            processed_bibentities = tuple(_preprocess_journal(df, raw_bibentity) for raw_bibentity in raw_bibentities)

        case "publisher":
            processed_bibentities = tuple(_preprocess_publisher(df, raw_bibentity) for raw_bibentity in raw_bibentities)

        case "profile":
            processed_bibentities = raw_bibentities

        case "article":
            processed_bibentities = raw_bibentities

        case "page":
            processed_bibentities = raw_bibentities

        case _:
            raise ValueError(
                f"Unsupported entity type: '{entity_type}'. Supported types are: {', '.join(SUPPORTED_ENTITY_TYPES)}"
            )

    return processed_bibentities, df


def prepare_bib_df(
    bib_df: pl.DataFrame,
) -> pl.DataFrame:
    """
    Prepare the bibliography DataFrame for sorting operations.
    Adds author parsing columns for sorting by last name and first name.
    """
    # Remove duplicates on 'bibkey'
    df = (
        bib_df.unique(subset=["bibkey"], keep="first")
        .select(
            [
                "bibkey",
                "title",
                "author",
                "journal",
                "journal-id",
                "date",
                "volume",
                "number",
                "pages",
            ]
        )
        .with_columns(
            [
                # Process the 'pages' column to extract start and end pages
                pl.col('pages')
                .str.strip_chars()
                .str.split('--')
                .alias('pages_split')
            ]
        )
        .with_columns(
            [
                pl.col('pages_split').list.get(0, null_on_oob=True).alias('start'),
                pl.col('pages_split').list.get(1, null_on_oob=True).alias('end'),
            ]
        )
        .drop('pages_split')
        .with_columns(
            [
                pl.col('start').str.replace_all(r'[^0-9]', '').cast(pl.Int32, strict=False).alias('start_int'),
            ]
        )
        # Add author parsing columns for sorting
        .with_columns(
            [
                # Extract first author (before " and ")
                pl.col('author')
                .str.split(' and ')
                .list.get(0, null_on_oob=True)
                .alias('_first_author'),
            ]
        )
        .with_columns(
            [
                # Extract last name (before comma) and first name (after comma)
                pl.col('_first_author')
                .str.split(',')
                .list.get(0, null_on_oob=True)
                .str.strip_chars()
                .str.to_lowercase()
                .fill_null('zzzzz')  # Sort entries without author to end
                .alias('_sort_last_name'),
                pl.col('_first_author')
                .str.split(',')
                .list.get(1, null_on_oob=True)
                .str.strip_chars()
                .str.to_lowercase()
                .fill_null('zzzzz')  # Sort entries without first name to end
                .alias('_sort_first_name'),
                # Lowercase title for sorting
                pl.col('title').str.to_lowercase().fill_null('zzzzz').alias('_sort_title'),
            ]
        )
        .drop('_first_author')
    )

    # Sort for journals/publishers (default sort: date DESC, volume DESC, number DESC, start_int ASC)
    sorted_df = (
        df.sort('start_int', nulls_last=True)
        .sort("number", descending=True)
        .sort('volume', descending=True)
        .sort('date', descending=True)
    )

    return sorted_df
