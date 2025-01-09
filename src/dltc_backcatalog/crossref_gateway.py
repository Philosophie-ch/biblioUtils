from typing import Tuple
from habanero import Crossref
from aletk.ResultMonad import Ok, Err


type TEmailAddress = str

type TCrossrefCredentials = Tuple[TEmailAddress,]

def get_crossref_client(crossref_credentials: TCrossrefCredentials) -> Ok[Crossref] | Err:
    """
    Initializes a Crossref client using the "polite" pool. For this, you need to provide an email address.
    """
    try:
        (email_address,) = crossref_credentials

        cr = Crossref(
            mailto=email_address,
        )

        return Ok(out=cr)

    except Exception as e:
        return Err(
            message=f"Crossref client could not be initialized:\n{e}",
            code=-1,
        )
