from typing import Generic, TypeVar
from pydantic import BaseModel

T = TypeVar("T")


class Ok(BaseModel, Generic[T]):
    out: T


class Err(BaseModel):
    message: str


class ErrData(BaseModel, Generic[T]):
    message: str
    data: T
