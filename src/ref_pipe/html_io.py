import os
from typing import FrozenSet, Tuple
from src.sdk.utils import get_logger, lginf
from src.sdk.ResultMonad import try_except_wrapper
from src.ref_pipe.models import (
    BibDiv,
    BibEntity,
    BibEntityWithHTML,
    Bibliography,
    HTMLIssue,
    HTMLVolume,
    HTMLYear,
    RefHTML,
    TBibDivDict,
    THTMLCollapsible,
    TSupportedEntity,
    SUPPORTED_ENTITY_TYPES,
)
import polars as pl


lgr = get_logger("Generate HTMLs")


def get_bibdivs(bibdiv_dict: dict[str, str], bibkeys: FrozenSet[str]) -> Tuple[str, ...]:
    return tuple(bibdiv_dict.get(bibkey, "") for bibkey in bibkeys if bibdiv_dict.get(bibkey, "") != "")


def gen_basic_html_files(
    bibentity: BibEntity,
    bibdiv_dict: TBibDivDict,
    output_basedir: str,
) -> BibEntityWithHTML:

    frame = f"gen_basic_html_files"

    os.makedirs(output_basedir, exist_ok=True)

    main_bibkeys = bibentity.main_bibkeys
    further_references = bibentity.further_references

    # 1. Main references
    if main_bibkeys != frozenset():
        main_bibkeys_divs = get_bibdivs(bibdiv_dict, main_bibkeys)
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
        further_references_divs = get_bibdivs(bibdiv_dict, further_references)
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
                name += f" :: vol. {volumes[0]}"
            years.append(HTMLYear(name=name, contents=tuple(year_bibkeys)))
        else:
            # Multiple volumes
            year_contents = [*bibs_without_volume]
            volume_names_g = (f"{v}" for v in year_group["volume"].unique().drop_nulls().to_list())
            volume_names = ", ".join(volume_names_g)
            year_name = f"{year_str} :: vol. {volume_names}"

            for volume_val, vol_group in year_group.group_by("volume", maintain_order=True):
                volume_str = " ".join(map(str, volume_val))

                volume_bibkeys_without_issue = vol_group.filter(pl.col("number").is_null().or_(pl.col("number") == ""))[
                    "bibkey"
                ].to_list()
                volume_contents = [*volume_bibkeys_without_issue]

                issues = vol_group.select("number").unique().drop_nulls().to_series().to_list()
                for issue_val in issues:
                    issue_str = " ".join(map(str, issue_val))
                    issue_name = f"issue {issue_str}"

                    issue_bibkeys = vol_group.filter(pl.col("number") == issue_val)["bibkey"].to_list()
                    volume_contents.append(HTMLIssue(name=str(issue_name), contents=tuple(issue_bibkeys)))

                year_contents.append(HTMLVolume(name=volume_str, contents=tuple(volume_contents)))

            years.append(HTMLYear(name=year_name, contents=tuple(year_contents)))

    return tuple(years)


COLLAPSIBLE_YEAR_HTML_FORMAT = """
<details class="collapsible-level-1">
    <summary>{name}</summary>
    <hr>

    {contents}

</details>
"""

COLLAPSIBLE_VOLUME_HTML_FORMAT = """
<details class="collapsible-level-2">
    <summary>{name}</summary>
    <hr>

    {contents}
</details>
"""

COLLAPSIBLE_ISSUE_HTML_FORMAT = """
<details class="collapsible-level-3">
    <summary>{name}</summary>
    <hr>

    {contents}
</details>
"""


def generate_struct_html(
    struct: THTMLCollapsible,
    bibdiv_dict: TBibDivDict,
) -> str:

    main_html = f""

    for year in struct:

        year_html_contents = f""
        for year_content in year.contents:

            if isinstance(year_content, str):
                bibdiv = bibdiv_dict.get(year_content, None)
                if bibdiv is None:
                    lgr.warning(f"Bibkey {year_content} not found in bibdiv_dict.")
                    continue
                year_html_contents += bibdiv
                year_html_contents += "\n"

            elif isinstance(year_content, HTMLVolume):

                vol_html_contents = f""
                for vol_content in year_content.contents:

                    if isinstance(vol_content, str):
                        bibdiv = bibdiv_dict.get(vol_content, None)
                        if bibdiv is None:
                            lgr.warning(f"Bibkey {vol_content} not found in bibdiv_dict.")
                            continue
                        vol_html_contents += bibdiv
                        vol_html_contents += "\n"

                    elif isinstance(vol_content, HTMLIssue):
                        issue_html_contents = f""

                        for issue_content in vol_content.contents:
                            bibdiv = bibdiv_dict.get(issue_content, None)
                            if bibdiv is None:
                                lgr.warning(f"Bibkey {issue_content} not found in bibdiv_dict.")
                                continue
                            issue_html_contents += bibdiv
                            issue_html_contents += "\n"

                        issue_html = COLLAPSIBLE_ISSUE_HTML_FORMAT.format(
                            name=vol_content.name, contents=issue_html_contents
                        )
                        vol_html_contents += issue_html
                        vol_html_contents += "\n"
                    else:
                        raise ValueError(f"Unknown content type for volume content: {type(vol_content)}")

                volume_html = COLLAPSIBLE_VOLUME_HTML_FORMAT.format(name=year_content.name, contents=vol_html_contents)
                year_html_contents += volume_html
                year_html_contents += "\n"

            else:
                raise ValueError(f"Unknown content type for year content: {type(year_content)}")

        year_html = COLLAPSIBLE_YEAR_HTML_FORMAT.format(name=year.name, contents=year_html_contents)
        main_html += year_html
        main_html += "\n"

    return main_html


def gen_journal_html_file(
    bibentity: BibEntity,
    bibdiv_dict: TBibDivDict,
    output_basedir: str,
    bib_df: pl.DataFrame,
) -> BibEntityWithHTML:
    """
    Generate the HTML file for a journal entity.
    This function creates a collapsible HTML structure for the journal's articles.
    """
    frame = f"gen_journal_html_file"
    lginf(frame, f"Generating HTML file for journal '{bibentity.entity_key}'...", lgr)

    os.makedirs(output_basedir, exist_ok=True)
    if not os.path.exists(output_basedir):
        msg = f"The output directory '{output_basedir}' does not exist and could not be created. Exiting."
        raise FileNotFoundError(msg)

    journal_df = bib_df.filter(bib_df['journal_key'] == bibentity.entity_key)
    journal_structure = build_collapsible(journal_df)
    journal_html = generate_struct_html(journal_structure, bibdiv_dict)

    journal_html_filename = f"{output_basedir}/{bibentity.url_endpoint}.html"

    with open(journal_html_filename, "w") as f:
        f.write(journal_html)
        f.write("\n")

    if not os.path.exists(journal_html_filename):
        msg = (
            f"The journal HTML file '{journal_html_filename}' was not generated for '{bibentity.entity_key}'. Exiting."
        )
        raise FileNotFoundError(msg)

    lginf(
        frame,
        f"HTML file '{journal_html_filename}' successfully generated for '{bibentity.entity_key}'",
        lgr,
    )

    return BibEntityWithHTML(
        id=bibentity.id,
        entity_key=bibentity.entity_key,
        url_endpoint=bibentity.url_endpoint,
        main_bibkeys=bibentity.main_bibkeys,
        further_references=bibentity.further_references,
        depends_on=bibentity.depends_on,
        html=RefHTML(
            references_filename=journal_html_filename,
            further_references_filename="",
        ),
    )


@try_except_wrapper(lgr)
def gen_html_files(
    bibentity: BibEntity,
    bibdiv_dict: TBibDivDict,
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

            return gen_journal_html_file(bibentity, bibdiv_dict, output_basedir, bib_df, bibliography)

        case "publisher":
            if not bib_df:
                raise ValueError("The bib_df parameter must be provided for journal entities.")

            raise NotImplementedError("Publisher HTML generation is not implemented yet.")

        case "article":
            return gen_basic_html_files(
                bibentity,
                bibdiv_dict,
                output_basedir,
            )

        case "profile":
            return gen_basic_html_files(
                bibentity,
                bibdiv_dict,
                output_basedir,
            )

        case _:
            raise ValueError(
                f"Unsupported entity type: {entity_type}. Supported types are: {', '.join(SUPPORTED_ENTITY_TYPES)}"
            )
