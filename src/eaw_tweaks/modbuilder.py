from typing import cast
from collections.abc import Iterable, Mapping
from pathlib import PureWindowsPath, Path
import os
import io
from lxml import etree
from petro_meg import MegBuilder
from . import megafiles
from .tweaks import TweakFunction, TweakList, SelectorCollector


BUNDLE_MEGA_XML = PureWindowsPath("Data") / "megafiles.xml"
BUNDLE_MEGA_XML_CONTENT = (
    b'<?xml version="1.0" ?>\r\n\r\n'
    b"<Mega_Files>\r\n\r\n"
    b"\t<File> Data\\Overrides.meg </File>\r\n\r\n"
    b"</Mega_Files>\r\n\r\n"
)
BUNDLE_OVERRIDES_MEG = PureWindowsPath("Data") / "Overrides.meg"


def build_mod(game_data: os.PathLike, tweaks: Iterable[TweakFunction]) -> Mod:
    mega_files = megafiles.list_mega_files(game_data)
    tweaks: TweakList = TweakList(*tweaks)
    input_collector = SelectorCollector(tweaks.__eaw_selector__)
    affected_files = {}
    for path, xml in megafiles.get_xml_files(mega_files):
        if input_collector.visit_document(xml):
            affected_files[path] = xml
    input_collector.collected().apply(tweaks)
    return Mod(affected_files)


class ModExistsError(FileExistsError):
    pass


class Mod:
    """Represents a Mod as a list of XML files."""

    def __init__(
        self,
        files: Mapping[os.PathLike, etree.ElementTree]
        | Iterable[tuple[os.PathLike, etree.ElementTree]] = [],
    ):
        """Construct a Mod from a mapping of relative file paths to XML contents."""
        if isinstance(files, Mapping):
            files = cast(Iterable[tuple[os.PathLike, etree.ElementTree]], files.items())
        self._files = {PureWindowsPath(path): xml for path, xml in files}

    def write_dir(self, mod: os.PathLike, /, bundle: bool = False, overwrite: bool = False):
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
        for path, file in self._files.items():
            content = io.BytesIO()
            file.write(content, encoding=file.docinfo.encoding, xml_declaration=True)
            builder[str(path)] = content

        (mod / 'Data').mkdir(exist_ok=True)
        with open(mod / BUNDLE_OVERRIDES_MEG, "wb") as meg_out:
            builder.build(meg_out)
        with open(mod / BUNDLE_MEGA_XML, "wb") as meg_xml:
            meg_xml.write(BUNDLE_MEGA_XML_CONTENT)
        return frozenset((BUNDLE_OVERRIDES_MEG, BUNDLE_MEGA_XML))

    def _write_loose(self, mod: Path) -> frozenset[PureWindowsPath]:
        for path, file in self._files.items():
            (mod / path.parent).mkdir(exist_ok=True, parents=True)
            with open(mod / path, 'wb') as xml_out:
                file.write(xml_out, encoding=file.docinfo.encoding, xml_declaration=True)
        return frozenset(self._files.keys())


def relative_contents(path: Path) -> set[PureWindowsPath]:
    """Gets a set of windows-style paths for all files relative to the given path."""
    output = set()
    for dirpath, _, filenames in path.walk():
        dirpath = PureWindowsPath(dirpath.relative_to(path))
        for filename in filenames:
            output.add(dirpath / filename)
    return output
