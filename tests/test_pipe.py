from src.sdk.pipe import pipe, pipe_out
from src.sdk.ResultMonad import Err, try_except_wrapper, funwrap
from src.sdk.utils import get_logger

lgr = get_logger(__name__)

@try_except_wrapper(lgr)
def f(x: int) -> int:
    return x + 1

@try_except_wrapper(lgr)
def g(x: object) -> None:
    raise ValueError("g error")

@try_except_wrapper(lgr)
def h(x: object) -> None:
    raise ValueError("h error")


def test_pipe_error_propagation() -> None:

    res = pipe(1) >> f >> g >> f >> pipe_out  # type: ignore

    assert isinstance(res, Err)
    assert "g error" in res.message

    res2 = pipe(1) >> f >> h >> f >> g >> pipe_out   # type: ignore

    assert isinstance(res2, Err)
    assert "h error" in res2.message


def test_pipe_unwrapping_Ok_monad() -> None:

    res = (pipe(1) >> f >> (lambda x: x + 2) >> f >> (lambda x: x + 3) >> pipe_out)  # type: ignore

    assert isinstance(res, int)
    assert res == 8

    res2 = pipe(1) >> f >> (lambda x: x + 2) >> f >> pipe_out  # type: ignore

    assert isinstance(res2, int)
    assert res2 == 5