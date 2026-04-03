import copy
import io
import os
from collections.abc import Iterable, Mapping
from pathlib import Path, PureWindowsPath
from typing import Literal, cast

from lxml import etree
from petro_meg import MegBuilder

from .collections import Dictable, FilterFunc

BUNDLE_MEGA_XML = PureWindowsPath("Data") / "megafiles.xml"
BUNDLE_MEGA_XML_CONTENT = (
    b'<?xml version="1.0" ?>\r\n\r\n'
    b"<Mega_Files>\r\n\r\n"
    b"\t<File> Data\\Overrides.meg </File>\r\n\r\n"
    b"</Mega_Files>\r\n\r\n"
)
BUNDLE_OVERRIDES_MEG = PureWindowsPath("Data") / "Overrides.meg"


class ModBuilder:
    """Holds the source configs for the game and tracks which have been modified."""

    def __init__(self, configs: Dictable[os.PathLike, etree.ElementTree] | ModBuilder):
        """Initialize a set of Mod from a collection of file paths and corresponding element
        trees.

        If the input is another ModBuilder, the element trees will be deep-copied to avoid linking.
        If the input is a dict or map, the trees are not copied so changes stay linked to the input.
        """
        if isinstance(configs, ModBuilder):
            self._configs = {
                path: copy.deepcopy(config) for path, config in configs._configs.items()
            }
            self._modified = set(configs._modified)
        else:
            if isinstance(configs, Mapping):
                configs = cast(
                    Iterable[tuple[os.PathLike, etree.ElementTree]], configs.items()
                )
            self._configs = {PureWindowsPath(path): config for path, config in configs}
            self._modified = set()

    def overlay(
        self,
        configs: Dictable[os.PathLike, etree.ElementTree] | ModBuilder,
        mark_modified: bool | Literal["propagate"] = True,
    ):
        """Overlay additional configs, replacing ones with the same path.

        This is intended for overlaying files from an existing Mod on top of the base game's files.
        By default all overlayed files will be marked as modified unless you pass
        mark_modified=False

        When overlaying an existing Mod, mark_modified can be set to "propagate" instead,
        which will copy the modified state from the overlay. That means that 'propagate' can un-mark
        files from modified back to unmodified.

        When passing Mod, the ElementTrees will be copied, so changes will not be linked
        between the two Mod. For dict or iterable inputs, no copy is performed.
        """
        if isinstance(configs, ModBuilder):
            for path, config in configs._configs.items():
                self._configs[path] = copy.deepcopy(config)
            if mark_modified == "propagate":
                self._modified -= configs._configs.keys()
                self._modified |= configs._modified
            elif mark_modified:
                self._modified |= configs._modified
        else:
            if mark_modified == "propagate":
                raise ValueError('"propagate" can only be used for Mod')
            if isinstance(configs, Mapping):
                configs = cast(
                    Iterable[tuple[os.PathLike, etree.ElementTree]], configs.items()
                )
            for path, config in configs:
                path = PureWindowsPath(path)
                self._configs[path] = config
                if mark_modified:
                    self._modified.add(path)

    def mark_modified(self, *paths: os.PathLike):
        """Mark a config as modified."""
        for orig_path in paths:
            path = PureWindowsPath(orig_path)
            if path not in self._configs:
                raise ValueError(f"File {orig_path} is not in the game files")
            self._modified.add(path)

    def modified(self) -> dict[PureWindowsPath, etree.ElementTree]:
        """Get all currently Modified files from the game."""
        return {
            path: config
            for path, config in self._configs.items()
            if path in self._modified
        }

    def files(self) -> set[PureWindowsPath]:
        """Get a set of all files in this Mod.

        Does not mark anything as modified.
        """
        return set(self._configs.keys())

    def get_file(
        self, path: os.PathLike, mark_modified=True
    ) -> etree.ElementTree | None:
        """Gets the file with the specified path.

        Returns None if the file does not exist.

        Marks the file as modified unless mark_modified is False.
        """
        path = PureWindowsPath(path)
        config = self._configs.get(path)
        if mark_modified and config is not None:
            self._modified.add(path)
        return config

    def fetch(
        self,
        xpath: etree.XPath,
        mark_modified=True,
        filter_func: FilterFunc | None = None,
    ) -> list[etree.Element]:
        """Fetch every match of the given xpath from across all configs in the game sources.

        This will mark all matching files as modified unless you pass mark_modified=False.

        If a filter function is provided, it will be applied before marking a file as modified.
        """
        collector = []
        for path, config in self._configs.items():
            matches = xpath(config.getroot())
            if filter_func is not None:
                matches = list(filter(filter_func, matches))
            if mark_modified and matches:
                self._modified.add(path)
            collector.extend(matches)
        return collector

    def write_dir(
        self, mod: os.PathLike, /, bundle: bool = False, overwrite: bool = False
    ):
        """Write this Mod to the given directory.

        If bundle is true, pack the mod into a MEGA file.
        If overwrite is true, clear the output directory before writing.
        """
        mod = Path(mod)
        mod.mkdir(exist_ok=True, parents=True)
        if not overwrite and next(mod.iterdir(), None) is not None:
            raise ModExistsError(
                "Refusing to overwrite non-empty mod directory without overwrite flag"
            )
        existing = relative_contents(mod)
        output_files = self._write_inner(mod, bundle)
        to_remove = existing - output_files
        for file in to_remove:
            (mod / file).unlink()

    def _write_inner(self, mod: Path, bundle: bool) -> frozenset[PureWindowsPath]:
        if bundle:
            return self._write_packed(mod)
        return self._write_loose(mod)

    def _write_packed(self, mod: Path) -> frozenset[PureWindowsPath]:
        builder = MegBuilder("v1")
        for path, file in self.modified().items():
            content = io.BytesIO()
            file.write(content, encoding='utf-8', xml_declaration=True)
            builder[str(path)] = content

        (mod / "Data").mkdir(exist_ok=True)
        with open(mod / BUNDLE_OVERRIDES_MEG, "wb") as meg_out:
            builder.build(meg_out)
        with open(mod / BUNDLE_MEGA_XML, "wb") as meg_xml:
            meg_xml.write(BUNDLE_MEGA_XML_CONTENT)
        return frozenset((BUNDLE_OVERRIDES_MEG, BUNDLE_MEGA_XML))

    def _write_loose(self, mod: Path) -> frozenset[PureWindowsPath]:
        modified = self.modified()
        for path, file in modified.items():
            (mod / path.parent).mkdir(exist_ok=True, parents=True)
            with open(mod / path, "wb") as xml_out:
                file.write(
                    xml_out, encoding='utf-8', xml_declaration=True
                )
        return frozenset(modified.keys())


class ModExistsError(FileExistsError):
    pass


def relative_contents(path: Path) -> set[PureWindowsPath]:
    """Gets a set of windows-style paths for all files relative to the given path."""
    output = set()
    for dirpath, _, filenames in path.walk():
        dirpath = PureWindowsPath(dirpath.relative_to(path))
        for filename in filenames:
            output.add(dirpath / filename)
    return output
