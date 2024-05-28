from typing import Generic, TypeVar
from pydantic import BaseModel, ConfigDict

T = TypeVar("T")


class Ok(BaseModel, Generic[T]):
    """
    Model for the success case of a function in this project.

    Attributes
    ----------
    out : T
        The data returned by the function.
    """

    out: T
    model_config = ConfigDict(arbitrary_types_allowed=True)


class Err(BaseModel):
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


class ErrData(BaseModel, Generic[T]):
    """
    Model for the error case of a function in this project that returns data. Note: it's important that this doesn't inherit from Err, as isinstance checks would rule out ErrData when checking for Err.

    Attributes
    ----------
    message : str
        A message describing the error.
    code : int
        A code that can be used to handle different error cases.
    data : T
        The data returned by the function.
    """

    message: str
    code: int
    data: T
    model_config = ConfigDict(arbitrary_types_allowed=True)
