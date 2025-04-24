import os
from typing import Tuple
from src.sdk.utils import get_logger, lginf
from src.sdk.ResultMonad import try_except_wrapper
from src.ref_pipe.models import BibDiv, BibEntity, BibEntityWithHTML, Bibliography, HTMLIssue, HTMLVolume, HTMLYear, RefHTML, THTMLCollapsible, TSupportedEntity, SUPPORTED_ENTITY_TYPES
import polars as pl


lgr = get_logger("Generate HTMLs")


def gen_basic_html_files(
    bibentity: BibEntity,
    bibdivs: Tuple[BibDiv, ...],
    output_basedir: str,
) -> BibEntityWithHTML:

    frame = f"gen_basic_html_files"

    os.makedirs(output_basedir, exist_ok=True)

    main_bibkeys = bibentity.main_bibkeys
    further_references = bibentity.further_references

    # 1. Main references
    if main_bibkeys != frozenset():
        main_bibkeys_divs = tuple(bibdiv.content for bibdiv in bibdivs if bibdiv.div_id in main_bibkeys)
        main_bibkeys_filename = f"{output_basedir}/{bibentity.url_endpoint}-references.html"

        with open(main_bibkeys_filename, "w") as f:
            f.write("\n".join(main_bibkeys_divs))

        if not os.path.exists(main_bibkeys_filename):
            msg = f"The main references HTML file '{main_bibkeys_filename}' was not generated for '{bibentity.entity_key}'. Exiting."
            raise FileNotFoundError(msg)

    else:
        # Skip if there are no main references
        lginf(frame, f"Note: no main references found for '{bibentity.entity_key}'.", lgr)
        return BibEntityWithHTML(
            id=bibentity.id,
            entity_key=bibentity.entity_key,
            url_endpoint=bibentity.url_endpoint,
            main_bibkeys=bibentity.main_bibkeys,
            further_references=bibentity.further_references,
            depends_on=bibentity.depends_on,
            html=RefHTML(
                references_filename="",
                further_references_filename="",
            ),
        )

    # 2. Further references and dependencies
    if further_references != frozenset():
        further_references_divs = tuple(bibdiv.content for bibdiv in bibdivs if bibdiv.div_id in further_references)
        further_references_filename = f"{output_basedir}/{bibentity.url_endpoint}-further-references.html"

        with open(further_references_filename, "w") as f:
            f.write("\n".join(further_references_divs))

        if not os.path.exists(further_references_filename):
            msg = f"The further references HTML file '{further_references_filename}' was not generated for '{bibentity.entity_key}'. Exiting."
            raise FileNotFoundError

    else:
        further_references_filename = ""

    ref_html = RefHTML(
        references_filename=main_bibkeys_filename,
        further_references_filename=further_references_filename,
    )

    lginf(frame, f"HTML files successfully generated for '{bibentity.entity_key}'", lgr)

    return BibEntityWithHTML(
        id=bibentity.id,
        entity_key=bibentity.entity_key,
        url_endpoint=bibentity.url_endpoint,
        main_bibkeys=bibentity.main_bibkeys,
        further_references=bibentity.further_references,
        depends_on=bibentity.depends_on,
        html=ref_html,
    )


def build_collapsible(df: pl.DataFrame) -> THTMLCollapsible:
    """
    Build a collapsible HTML structure from a bibliography DataFrame.
    Note that this is independent of the entity type, so it can be reused for different entities.
    """
    years = []
    for year_val, year_group in df.group_by("date", maintain_order=True):
        year_str = " ".join(map(str, year_val))

        volumes = year_group.select("volume").unique().drop_nulls().to_series().to_list()
        has_multiple_volumes = len(volumes) > 1

        bibs_without_volume = year_group.filter(pl.col("volume").is_null())["bibkey"].to_list()

        if not has_multiple_volumes:
            # Single or no volume: flatten to HTMLYear
            year_bibkeys = year_group["bibkey"].to_list()
            name = year_str
            if len(volumes) == 1:
                name += f" :: {volumes[0]}"
            years.append(HTMLYear(name=name, contents=tuple(year_bibkeys)))
        else:
            # Multiple volumes
            year_contents = [*bibs_without_volume]

            for volume_val, vol_group in year_group.group_by("volume", maintain_order=True):
                volume_str = " ".join(map(str, volume_val))

                volume_bibkeys_without_issue = vol_group.filter(pl.col("number").is_null())["bibkey"].to_list()
                volume_contents = [*volume_bibkeys_without_issue]

                issues = vol_group.select("number").unique().drop_nulls().to_series().to_list()
                for issue_val in issues:
                    issue_str = " ".join(map(str, issue_val))
                    issue_bibkeys = vol_group.filter(pl.col("number") == issue_val)["bibkey"].to_list()
                    volume_contents.append(
                        HTMLIssue(name=str(issue_str), contents=tuple(issue_bibkeys))
                    )

                year_contents.append(HTMLVolume(name=volume_str, contents=tuple(volume_contents)))

            years.append(HTMLYear(name=year_str, contents=tuple(year_contents)))

    return tuple(years)



def gen_journal_html_file(
    bibentity: BibEntity,
    bibdivs: Tuple[BibDiv, ...],
    output_basedir: str,
    bib_df: pl.DataFrame,
    bibliography: Bibliography,
) -> BibEntityWithHTML:

    journal_df = bib_df.filter(bib_df['journal_key'] == bibentity.entity_key)


    return None



@try_except_wrapper(lgr)
def gen_html_files(
    bibentity: BibEntity,
    bibdivs: Tuple[BibDiv, ...],
    output_basedir: str,
    entity_type: TSupportedEntity,
    bib_df: pl.DataFrame | None,
    bibliography: Bibliography,
) -> BibEntityWithHTML:

    frame = f"gen_html_files"
    lginf(frame, f"Generating HTML files for '{bibentity.entity_key}'...", lgr)

    match entity_type:

        case "journal":
            if not bib_df:
                raise ValueError("The bib_df parameter must be provided for journal entities.")

            return gen_journal_html_file(
                bibentity,
                bibdivs,
                output_basedir,
                bib_df,
                bibliography
            )

        case "publisher":
            if not bib_df:
                raise ValueError("The bib_df parameter must be provided for journal entities.")

            raise NotImplementedError("Publisher HTML generation is not implemented yet.")

        case "article":
            return gen_basic_html_files(
                bibentity,
                bibdivs,
                output_basedir,
            )

        case "profile":
            return gen_basic_html_files(
                bibentity,
                bibdivs,
                output_basedir,
            )

        case _:
            raise ValueError(
                f"Unsupported entity type: {entity_type}. Supported types are: {', '.join(SUPPORTED_ENTITY_TYPES)}"
            )
