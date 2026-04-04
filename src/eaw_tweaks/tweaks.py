import functools
from abc import ABC, abstractmethod
from collections.abc import Callable, Iterable
from typing import overload

from lxml import etree

from .collections import FilterFunc, FuncArgs
from .modbuilder import ModBuilder

type XPathable = etree.XPath | str | bytes | bytearray


def _make_xpath(pathable: XPathable) -> etree.XPath:
    if isinstance(pathable, etree.XPath):
        return pathable
    return etree.XPath(pathable)


class Tweak(ABC):
    """Defines an object which can apply tweaks to the EAW game files.."""

    @abstractmethod
    def __tweak_eaw__(self, configs: ModBuilder):
        pass


class _TweakSelector:
    """Container for an XPath based selector and an optional corresponding filter."""

    def __init__(self, xpath: etree.XPath, filter_func: FilterFunc | None = None):
        self._xpath = xpath
        self._filter_func = filter_func

    @property
    def xpath(self) -> etree.XPath:
        return self._xpath

    @property
    def filter_func(self) -> FilterFunc | None:
        return self._filter_func

    def filter(self, filter_func: FilterFunc) -> _TweakSelector:
        """Returns a new _TweakSelector that applies the given filter_func to the output of the
        current selector.
        """
        if self._filter_func is None:
            return _TweakSelector(self._xpath, filter_func)
        base_filter = self._filter_func

        def combined_filter(elem: etree.Element) -> bool:
            return base_filter(elem) and filter_func(elem)

        return _TweakSelector(self._xpath, combined_filter)

    def fetch(self, game_sources: ModBuilder) -> list[etree.Element]:
        """Fetch this swlector from the game sources."""
        return game_sources.fetch(self._xpath, filter_func=self._filter_func)


class TweakFunction(Tweak):
    """Wraps a function to make it operate as a Tweak.

    Takes a function and a FuncArgs of XPath-based TweakSelectors. When __tweak_eaw__ is called, it
    will map the XPath selectors for every argument to a matching list of elements, and then call
    the function with the corresponding list of xpath matches in each argument position.

    Any file which matches an XPath selector will be marked as modified, even if nothing from it is
    ever modified.
    """

    def __init__(self, func: Callable[..., None], selectors: FuncArgs[_TweakSelector]):
        """Internal."""
        self._func = func
        self._selectors = selectors

    @property
    def func(self) -> Callable[..., None]:
        """Gets the underlying tweak function."""
        return self._func

    def __tweak_eaw__(self, configs: ModBuilder):
        self._selectors.map(lambda selector: selector.fetch(configs)).apply(self.func)

    def filter(self, *afilters: FilterFunc | None, **kwfilters: FilterFunc | None) -> TweakFunction:
        """Returns a new TweakFunction with filters added to the selectors.

        The provided filters must structurally match a subset of the xpath values the tweak function
        is looking for. That is, if the XPath selector is positional, it can only be filtered
        positionally and if it is a keword argument it can only be filtered as a keyword argument.
        Additionally, the positional filters must be no longer than the list of args and the keword
        filters must be a strict subset of the keyword-based XPath selectors.

        Each arg filter or kwarg filter is allowed to be None. If None is provided no additional
        filtering is done, but existing filters are not removed.
        """
        if len(afilters) > len(self._selectors.args):
            raise ValueError(
                f"Provided {len(afilters)} positional filters, but there are only {len(self._selectors.args)} positional selectors"
            )
        # Note: we have to use 'not <=' because `>=` is superset, which is not the same as 'not
        # subset'!
        if not (kwfilters.keys() <= self._selectors.kwargs.keys()):
            raise ValueError(
                "Keyword filters must be a subset of keyword selectors, but the provided filters "
                "had the following keys which did not match any selectors: "
                f"{kwfilters.keys() - self._selectors.kwargs.keys()}"
            )

        newargs = list(self._selectors.args)
        for i, afilter in enumerate(afilters):
            if afilter is not None:
                newargs[i] = newargs[i].filter(afilter)
        newkwargs = dict(self._selectors.kwargs)
        for key, kwfilter in kwfilters.items():
            if kwfilter is not None:
                newkwargs[key] = newkwargs[key].filter(kwfilter)
        return TweakFunction(self._func, FuncArgs(newargs, newkwargs))


class TweakList(Tweak):
    """Combinator that merges several tweaks.

    Tweaks will be applied sequentially, so subsequent tweaks are affected by ones that run prior to
    them.
    """

    @classmethod
    def of(cls, *tweaks: Tweak) -> TweakList:
        return cls(tweaks)

    def __init__(self, tweaks: Iterable[Tweak]):
        self._tweaks = list(tweaks)

    def __iter__(self) -> Iterable[Tweak]:
        return iter(self._tweaks)

    def __len__(self) -> int:
        return len(self._tweaks)

    @overload
    def __getitem__(self, idx: int) -> Tweak: ...
    @overload
    def __getitem__(self, idx: range) -> list[Tweak]: ...
    def __getitem__(self, idx):
        return self._tweaks[idx]

    def __tweak_eaw__(self, configs: ModBuilder):
        for tweak in self._tweaks:
            tweak.__tweak_eaw__(configs)


def tweak(
    *aselectors: XPathable, **kwselectors: XPathable
) -> Callable[[Callable[..., None]], TweakFunction]:
    """Decorator which converts a function into a TweakFunction.

    The decorator factory takes args and keyword arguments that specify XPaths to fetch from across
    all of the game's configs. When the tweak is run, those xpaths will be fetched and the inner
    function will be called with a list[etree.Element] corresponding to each argument and keyword
    argument of xpaths provided to `tweak_function`.
    """
    selectors = FuncArgs(aselectors, kwselectors).map(
        lambda selector: _TweakSelector(_make_xpath(selector))
    )

    def tweak_decorator(func: Callable[..., None]) -> TweakFunction:
        return TweakFunction(func, selectors)

    return tweak_decorator


type TweakFactory = Callable[..., Tweak]


class TweakFunctionFactory[**P](ABC):
    """Utility class which wraps a function that produces a TweakFunction to provide utility
    methods.
    """

    @abstractmethod
    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> TweakFunction:
        pass

    def filter(
        self, *afilters: FilterFunc | None, **kwfilters: FilterFunc | None
    ) -> TweakFunctionFactory:
        """Applies the given filters to the constructed TweakFunction. See TweakFunction.filter"""
        return _FilteredTweakFunctionFactory(self, FuncArgs(afilters, kwfilters))


class tweak_factory[**P](TweakFunctionFactory[P]):
    """Wraps a function that returns a TweakFunction to add support for the filter method at the
    factory level.
    """

    def __init__(self, func: Callable[P, TweakFunction]):
        if not isinstance(func, TweakFunctionFactory):
            functools.update_wrapper(self, func)
        self._func = func

    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> TweakFunction:
        return self._func(*args, **kwargs)


class _FilteredTweakFunctionFactory[**P](TweakFunctionFactory[P]):
    def __init__(self, inner: TweakFunctionFactory[P], filters: FuncArgs[FilterFunc | None]):
        self._inner = inner
        self._filters = filters

    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> TweakFunction:
        return self._filters.apply(self._inner(*args, **kwargs).filter)


class TweakFilter(ABC):
    """A filter which can be applied to a tweak function or tweak function factory as a decorator."""

    @abstractmethod
    def __call__(self, *args, **kwargs) -> bool:
        pass

    @overload
    def apply(self, tweak: TweakFunction) -> TweakFunction: ...
    @overload
    def apply(self, tweak: TweakFunctionFactory) -> TweakFunctionFactory: ...
    def apply(self, tweak: TweakFunction | TweakFunctionFactory):
        return tweak.filter(self)

    @staticmethod
    def any(*funcs: FilterFunc) -> TweakFilter:
        """Creates a filter that matches if any of the given filters matches."""
        return _TweakOr(*funcs)

    @staticmethod
    def all(*funcs: FilterFunc) -> TweakFilter:
        """Creates a filter that matches if all of the given filters match."""
        return _TweakAnd(*funcs)

    def __or__(self, other: FilterFunc) -> TweakFilter:
        return _TweakOr(self, other)

    def __ior__(self, other: FilterFunc) -> TweakFilter:
        return _TweakOr(other, self)

    def __and__(self, other: FilterFunc) -> TweakFilter:
        return _TweakAnd(self, other)

    def __iand__(self, other: FilterFunc) -> TweakFilter:
        return _TweakAnd(other, self)

    def __invert__(self) -> TweakFilter:
        return _TweakNot(self)


class tweak_filter(TweakFilter):
    """Utility wrapper for a function that acts as a filter for Tweaks which allows it to be used as
    a decorator for a TweakFunction or TweakFunctionFactory.
    """

    def __init__(self, func: FilterFunc):
        functools.update_wrapper(self, func)
        self._func = func

    def __call__(self, *args, **kwargs) -> bool:
        return self._func(*args, **kwargs)


class _TweakOr(TweakFilter):
    def __init__(self, *funcs: FilterFunc):
        self._funcs = funcs

    def __call__(self, *args, **kwargs) -> bool:
        return any(func(*args, **kwargs) for func in self._funcs)


class _TweakAnd(TweakFilter):
    def __init__(self, *funcs: FilterFunc):
        self._funcs = funcs

    def __call__(self, *args, **kwargs) -> bool:
        return all(func(*args, **kwargs) for func in self._funcs)


class _TweakNot(TweakFilter):
    def __init__(self, inner: TweakFilter):
        self._inner = inner

    def __invert__(self) -> TweakFilter:
        return self._inner

    def __call__(self, *args, **kwargs) -> bool:
        return not self._inner(*args, **kwargs)
