import argparse
from pathlib import Path
from . import megafiles


DEFAULT_PATH = Path(
    '~/.steam/steam/steamapps/common/Star Wars Empire at War/corruption'
)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog='eaw_tweaks',
        description='Creates mods for Empire at War which perform some tweaking',
    )
    parser.add_argument(
        "--eaw",
        help=(
            'Path to the Empire at War GameData directory. This is the one which contains the '
            '"Data" directory. For Steam, it is "common/Star Wars Empire at War/GameData" for base '
            'Empire at War, and "common/Star Wars Empire at War/corruption" for Forces of '
            'Corruption. If not specified, we automatically look for the Steam Forces of '
            'Corruption path. Currently auto-seeking only supports Steam-on-Linux at the default '
            'location. (In other words, we just default to "~/.steam/steam/steamapps/common/...")'
        ),
        default=None,
        type=Path,
    )
    parser.add_argument(
        'modname',
        help=(
            'Name to give the generated Mod. The new mod will be written to a folder with this '
            'name within GameData/Mods',
        ),
    )
    parser.add_argument(
        '--overwrite',
        help='If a mode with the same name already exists, overwrite it.',
    )

    args = parser.parse_args()
    game_data = args.eaw if args.eaw is not None else DEFAULT_PATH.expanduser()

    mega_files = megafiles.list_mega_files(game_data)
    with megafiles.find_config_files(mega_files) as config_files:
        for file in config_files:
            print('Found XML file:', file.name)
