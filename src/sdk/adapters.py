from typing import Callable, Generator, Generic, Iterator, TypeVar

T = TypeVar("T")


class GeneratorAdapter(Generic[T]):
    """
    Adapter class to allow for the use of a generator as an iterator. In this way, we can automatically consume the generator more than once. Usage example:

    ```python
    def my_generator() -> Generator[int, None, None]:
        yield 1
        yield 2
        yield 3

    adapter = GeneratorAdapter(my_generator)

    for item in adapter:
        print(item)

    for item in adapter:
        print(item)
    ```
    """

    def __init__(self, iterator_factory: Callable[[], Generator[T, None, None]]) -> None:
        self.iterator_factory = iterator_factory

    def __iter__(self) -> Iterator[T]:
        return self.iterator_factory()
