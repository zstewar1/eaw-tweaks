from collections.abc import Generator, Iterable
import os
from lxml import etree
from pathlib import Path, PureWindowsPath
from petro_meg import read_meg


def list_mega_files(game_data: os.PathLike) -> list[Path]:
    """Load the list of MEGA files from megafiles.xml in the given GameData dir."""
    if not isinstance(game_data, Path):
        game_data = Path(game_data)
    data_dir = game_data / "Data"
    megafiles = game_data / "Data" / "megafiles.xml"

    with open(megafiles, "r") as megafiles:
        megafiles = etree.parse(megafiles).getroot()
    available_files = {
        PureWindowsPath(path.relative_to(game_data)): path
        for path in data_dir.glob("*")
        if path.is_file()
    }
    true_paths = []
    for file in megafiles.xpath("/Mega_Files/File/text()"):
        win_path = PureWindowsPath(file.strip())
        real_path = available_files.get(win_path)
        if real_path is not None:
            true_paths.append(real_path)

    return true_paths


def get_xml_files(mega_files: Iterable[Path]) -> Generator[tuple[PureWindowsPath, etree.ElementTree]]:
    """Gets all XML files in the given mega files as etree.ElementTree, along with the relative
    paths within the MEGA file."""
    for mega_file in mega_files:
        with open(mega_file, "rb") as mega_file:
            for file in read_meg(mega_file, version="v1"):
                path = PureWindowsPath(str(file.name))
                if path.suffix.upper() == ".XML":
                    data = file.read()
                    encoding = "utf-8"
                    try:
                        data.decode("utf-8")
                    except UnicodeDecodeError:
                        encoding = "cp1252"
                    parser = etree.XMLParser(encoding=encoding, recover=True)
                    root = etree.XML(data, parser=parser)
                    yield path, etree.ElementTree(root)
