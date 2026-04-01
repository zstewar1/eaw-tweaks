from collections.abc import Callable, Iterable, Mapping
from typing import overload

from lxml import etree

type FilterFunc = Callable[[etree.Element], bool]
type Dictable[K, V] = Mapping[K, V] | Iterable[tuple[K, V]]


class FuncArgs[T]:
    """Collection that contains both a list and dict. Can be used to supply both args and kwargs at
    the same time.
    """

    @overload
    def __init__(self, args: FuncArgs[T]): ...
    @overload
    def __init__(
        self,
        args: Iterable[T] | None = None,
        kwargs: Dictable[str, T] | None = None,
    ): ...
    def __init__(
        self,
        args: Iterable[T] | FuncArgs[T] | None = None,
        kwargs: Dictable[str, T] | None = None,
    ):
        if isinstance(args, FuncArgs):
            if kwargs is not None:
                raise TypeError(
                    "Cannot pass a FuncArgs to copy and pass separate kwargs."
                )
            self._args = list(args.args)
            self._kwargs = dict(args.kwargs)
        else:
            self._args = list(args) if args is not None else []
            self._kwargs = dict(kwargs) if kwargs is not None else {}

    @property
    def args(self) -> list[T]:
        """Get the Args portion of this FuncArgs."""
        return self._args

    @property
    def kwargs(self) -> dict[str, T]:
        """Get the KWArgs portion of this FuncArgs."""
        return self._kwargs

    def apply[R](self, func: Callable[..., R]) -> R:
        """Call a function using the args and kwargs from self."""
        return func(*self._args, **self._kwargs)

    def map[U](self, func: Callable[[T], U]) -> FuncArgs[U]:
        """Map the values (in both args and kwargs) to new values."""
        return FuncArgs(
            args=(func(arg) for arg in self._args),
            kwargs=((key, func(value)) for key, value in self._kwargs.items()),
        )
