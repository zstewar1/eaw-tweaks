from typing import Generator, List
import contextlib
from lxml import etree
from pathlib import Path, PureWindowsPath
from petro_meg import FileEntry, read_meg, MegPath


def list_mega_files(game_data: Path) -> List[Path]:
    """Load the list of MEGA files from megafiles.xml in the given GameData dir."""
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


@contextlib.contextmanager
def find_config_files(mega_files: List[Path]) -> Generator[List[FileEntry]]:
    """Opens every mega file in the given list of mega_files and returns FileEntries for xml files.

    Finds all files in the given MEGA files list that have .XML extensions and retuns them.

    This function works as a context manager. It will keep all of the MEGA files for the returned
    FileEntry list open, so you can safely use FileEntry.read.
    """
    config_files = []
    keep_mega_files = contextlib.ExitStack()
    try:
        for mega_file in mega_files:
            mega_file = open(mega_file, "rb")
            try:
                configs = [
                    entry
                    for entry in read_meg(mega_file, version="v1")
                    if _is_xml(entry.name)
                ]
            except:
                # In case of error, close this MEGA file. others will be handled by the ExitStack.
                mega_file.close()
                raise
            if configs:
                # Add the file to the exit stack before extending the config_files to ensure its set
                # to be closed ASAP.
                keep_mega_files.enter_context(mega_file)
                config_files.extend(configs)
            else:
                # If there were no configs in this MEGA file, we can close it immediately.
                mega_file.close()

        yield config_files
    finally:
        keep_mega_files.close()


def _is_xml(path: MegPath) -> bool:
    """Returns true if the path ends with .XML."""
    return str(path).upper().endswith('.XML')
