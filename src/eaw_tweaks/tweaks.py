from typing import cast, runtime_checkable, Protocol
from collections.abc import Callable
import functools
from lxml import etree
from .collections import FuncArgs, ArgTree, map_arg_tree


type XPathable = etree.XPath | str | bytes | bytearray


def _make_xpath(pathable: XPathable) -> etree.XPath:
    if isinstance(pathable, etree.XPath):
        return pathable
    return etree.XPath(pathable)


type TweakArg[T] = T | ArgTree[T]


@runtime_checkable
class TweakFunction(Protocol):
    """Defines a function which can be used to apply tweaks."""

    def __call__(self, *args, **kwargs): ...

    @property
    def __eaw_selector__(self) -> ArgTree[etree.XPath]: ...


def bin(o):
    if o is None:
        breakpoint()
    return o


class TweakList(TweakFunction):
    """Combinator that merges several sets of tweaks."""

    def __init__(self, *tweaks: TweakFunction):
        self._tweaks = tweaks

    @property
    def __eaw_selector__(self) -> ArgTree[etree.XPath]:
        return FuncArgs(bin(tweak).__eaw_selector__ for tweak in self._tweaks)

    def __call__(self, *args: ArgTree[list[etree.Element]]):
        if len(args) != len(self._tweaks):
            raise ValueError(
                f"Have {len(self._tweaks)} tweak functions to apply, but got {len(args)} sets of "
                "tweak function args."
            )
        for arg, tweak in zip(args, self._tweaks):
            arg.apply(tweak)


def tweak(
    *args: TweakArg[XPathable], **kwargs: TweakArg[XPathable]
) -> Callable[[Callable[..., None]], TweakFunction]:
    """Decorator which labels a function as a tweak definition by declaring which XPath selectors it
    requires."""

    def tweak_decorator(func: Callable[..., None]) -> TweakFunction:
        func_args = map_arg_tree(FuncArgs(args, kwargs), _make_xpath)

        @functools.wraps(func)
        def tweak_wrapper(
            *wrapped_args: TweakArg[list[etree.Element]],
            **wrapped_kwargs: TweakArg[list[etree.Element]],
        ):
            func(*wrapped_args, **wrapped_kwargs)

        setattr(tweak_wrapper, "__eaw_selector__", func_args)
        return cast(TweakFunction, tweak_wrapper)

    return tweak_decorator


def _extract_visit(
    xml: etree.ElementTree, selector: TweakArg[etree.XPath], output: TweakArg[list[etree.Element]]
) -> bool:
    """Visit a single arg or kwarg for extract.

    selector and output must either both be leaf nodes or both be FuncArgs.
    """
    match selector, output:
        case FuncArgs() as selector, FuncArgs() as output:
            return _extract(xml, selector, output)
        case etree.XPath() as selector, list() as output:
            extracted = selector(xml.getroot())
            output.extend(extracted)
            return bool(extracted)
        case _:
            raise TypeError("selector and output must either both be FuncArgs or both leaves")


def _extract(
    xml: etree.ElementTree,
    selectors: ArgTree[etree.XPath],
    output: ArgTree[list[etree.Element]],
) -> bool:
    """Recursivly visit the selectors and output, extracting all real selectors from the tree.

    Return true if anything was extracted, otherwise false.
    """
    extracted = False
    for sel, out in zip(selectors.args, output.args):
        # Make sure not short circuit the recursive call.
        extracted = _extract_visit(xml, sel, out) or extracted
    for key in selectors.kwargs:
        sel = selectors.kwargs[key]
        out = output.kwargs[key]
        # Make sure not short circuit the recursive call.
        extracted = _extract_visit(xml, sel, out) or extracted
    return extracted


class SelectorCollector(object):
    """Collects XPath selector values across many XML files."""

    def __init__(self, selectors: ArgTree[etree.XPath]):
        self._selectors = selectors
        self._collectors: ArgTree[list[etree.Element]] = map_arg_tree(selectors, lambda _: [])

    def visit_document(self, tree: etree.ElementTree) -> bool:
        """Visit the document, returning true if anything was extracted from it."""
        return _extract(tree, self._selectors, self._collectors)

    def collected(self) -> ArgTree[list[etree.Element]]:
        """Create a deep copy of the elements collected so far."""
        return map_arg_tree(self._collectors, lambda lst: list(lst))
