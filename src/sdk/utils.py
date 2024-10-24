from datetime import datetime
import logging
from os import getenv
from fuzzywuzzy import fuzz

from src.sdk.ResultMonad import Err


def get_logger(name: str) -> logging.Logger:
    """
    Returns a logger object. Pass the name of the logger as an argument.

    You can also pass the environment variables 'LOGGING_LEVEL' or 'LOG_LEVEL' to set the logging level. If none is passed, the default is 'INFO'.
    """

    if name is None or not isinstance(name, str):
        raise ValueError("Utils::GetLogger::Argument 'name' has to be a non None string.")

    logging_level = getenv("LOGGING_LEVEL", "")

    if not logging_level:
        logging_level = getenv("LOG_LEVEL", "INFO")

    logger = logging.getLogger(name)
    logger.setLevel(logging_level)

    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setLevel(logging_level)
        datefmt = "%Y-%m-%d %H:%M:%S"
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s", datefmt)
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger


def remove_extra_whitespace(string: str) -> str:
    """
    Remove extra whitespace from a string. This version removes all newlines, tabs, carriage returns, trailing and leading whitespace, and multiple spaces in a row.

    If the input is None or not a string, a ValueError is raised.
    """
    if string is None or not isinstance(string, str):
        raise ValueError("Utils::RemoveExtraWhiteSpace::Argument string has to be a (non None) string.")

    cleaned_string = " ".join(string.split()).strip()

    return cleaned_string


def get_timestamp() -> str:
    """
    Returns a string timestamp in the format YYYYMMDD_HHMMSS.
    """
    dt = datetime.now().strftime("%Y%m%d_%H%M%S")

    return dt


def fuzzy_match_score(
    str1: str,
    str2: str,
) -> int:
    """
    Returns a fuzzy match score between two strings.

    If any of the inputs is None or not a string, a ValueError is raised.
    """

    if str1 is None or str2 is None or not isinstance(str1, str) or not isinstance(str2, str):
        raise ValueError(f"Utils::FuzzyMatchScore::Arguments have to be non None strings. Got:\n'{str1}'\n'{str2}'")

    score = fuzz.token_sort_ratio(str1, str2)

    if not isinstance(score, int):
        raise ValueError(
            f"Utils::FuzzyMatchScore::The score returned by the fuzzywuzzy library is not an integer. Got: {score}"
        )

    return score


def lginf(frame: str, msg: str, logger: logging.Logger) -> None:
    """
    Log an info message.
    """
    logger.info(f"{frame}\n\t{msg}")


def handle_error(frame: str, msg: str, logger: logging.Logger, code: int) -> Err:
    """
    Handle errors. This function returns an Err object with the message and code.
    """
    message = f"{frame}\n\t{msg}"
    logger.error(message)
    return Err(message=message, code=code)


def handle_unexpected_exception(msg: str, logger: logging.Logger, code: int = -1) -> Err:
    """
    Handle unexpected exceptions. This function logs the message and returns an Err object with the message and code.
    """
    message = f"Unexpected exception!\n{msg}"
    logger.error(message)
    return Err(message=message, code=code)
