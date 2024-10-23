from typing import Callable, Generic, TypeVar
from pydantic import BaseModel, ConfigDict

T = TypeVar("T")
U = TypeVar("U")
E = TypeVar("E")


class Result(BaseModel, Generic[T]):
    """
    Model for the result of a function in this project.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)


class Ok(Result[T]):
    """
    Model for the success case of a function in this project.

    Attributes
    ----------
    out : T
        The data returned by the function.
    """

    out: T


class Err(Result[None]):
    """
    Model for the error case of a function in this project.

    Attributes
    ----------
    message : str
        A message describing the error.
    code : int
        A code that can be used to handle different error cases.
    """

    message: str
    code: int


def rmap(f: Callable[[T], U], result: Ok[T] | Err) -> Ok[U] | Err:
    """
    Map a function over a Result.

    Parameters
    ----------
    f : Callable[[T], U]
        The function to map over the Result.
    result : Result[T]
        The Result to map the function over.

    Returns
    -------
    Result[U]
        The Result with the function mapped over it.
    """

    match result:
        case Ok(out=data):
            return Ok(out=f(data))
        case Err(message=msg, code=code):
            return Err(message=msg, code=code)
        case _:
            raise ValueError("Unknown Result type.")


def rbind(f: Callable[[T], Ok[U] | Err], result: Ok[T] | Err) -> Ok[U] | Err:
    """
    "result bind". Binds a function to a Result.

    Parameters
    ----------
    f : Callable[[T], Result[E]]
        The function to bind to the Result.
    result : Result[T]
        The Result to bind the function to.

    Returns
    -------
    Result[E]
        The Result with the function bound to it.
    """

    match result:
        case Ok(out=data):
            return f(data)
        case Err(message=msg, code=code):
            return Err(message=msg, code=code)
        case _:
            raise ValueError("Unknown Result type.")


def runwrap(result: Ok[T] | Err) -> T:
    """
    Unwrap a Result.

    Parameters
    ----------
    result : Result[T]
        The Result to unwrap.

    Returns
    -------
    T
        The data inside the Result.

    Raises
    ------
    ValueError
        If the Result is an Err.
    """

    match result:
        case Ok(out=data):
            return data
        case Err(message=msg, code=code):
            raise ValueError(f"Error: {msg}")


def runwrap_or(result: Ok[T] | Err, default: T) -> T:
    """
    Unwrap a Result, returning a default value if the Result is an Err.

    Parameters
    ----------
    result : Result[T]
        The Result to unwrap.
    default : T
        The default value to return if the Result is an Err.

    Returns
    -------
    T
        The data inside the Result, or the default value if the Result is an Err.
    """

    match result:
        case Ok(out=data):
            return data
        case Err(message=msg, code=code):
            return default
