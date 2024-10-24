from src.sdk.utils import handle_error, handle_unexpected_exception
from src.sdk.ResultMonad import Err, Ok, rbind, runwrap
from src.ref_pipe.models import Profile
from src.ref_pipe.utils import CHLLGR as lgr


# Example of working docker exec command:
# docker exec dltc-env bash -c 'cd "/home/copyeditor/dltc-workhouse/2023/2023-03-issue/01-patterson" && dltc-make offhtml'
