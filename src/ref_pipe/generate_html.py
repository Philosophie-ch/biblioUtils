import os
from typing import Tuple
from src.sdk.utils import get_logger, lginf
from src.sdk.ResultMonad import try_except_wrapper
from src.ref_pipe.models import BibDiv, BibEntity, BibEntityWithHTML, RefHTML


lgr = get_logger("Generate HTMLs")


@try_except_wrapper(lgr)
def gen_html_files(bibentity: BibEntity, bibdivs: Tuple[BibDiv, ...], output_basedir: str) -> BibEntityWithHTML:

    frame = f"gen_html_files"
    lginf(frame, f"Generating HTML files for '{bibentity.entity_key}'...", lgr)

    os.makedirs(output_basedir, exist_ok=True)

    main_bibkeys = bibentity.main_bibkeys
    further_references = bibentity.further_references
    depends_on = bibentity.depends_on

    # 1. Main references
    main_bibkeys_divs = tuple(bibdiv.content for bibdiv in bibdivs if bibdiv.div_id in main_bibkeys)
    main_bibkeys_filename = f"{output_basedir}/{bibentity.url_endpoint}-references.html"

    with open(main_bibkeys_filename, "w") as f:
        f.write("\n".join(main_bibkeys_divs))

    if not os.path.exists(main_bibkeys_filename):
        msg = f"The main references HTML file '{main_bibkeys_filename}' was not generated for '{bibentity.entity_key}'. Exiting."
        raise FileNotFoundError(msg)

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
