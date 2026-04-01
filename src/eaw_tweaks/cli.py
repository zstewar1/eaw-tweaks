import argparse
import importlib
import json
import sys
from pathlib import Path
from typing import Any

from . import megafiles
from .collections import FuncArgs
from .modbuilder import ModBuilder, ModExistsError
from .tweaks import Tweak, TweakList

DEFAULT_PATH = Path(
    "~/.steam/steam/steamapps/common/Star Wars Empire at War/corruption"
)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="eaw_tweaks",
        description="Creates mods for Empire at War which perform some tweaking",
    )
    parser.add_argument(
        "--eaw",
        help=(
            "Path to the Empire at War GameData directory. This is the one which contains the "
            '"Data" directory. For Steam, it is "common/Star Wars Empire at War/GameData" for base '
            'Empire at War, and "common/Star Wars Empire at War/corruption" for Forces of '
            "Corruption. If not specified, we automatically look for the Steam Forces of "
            "Corruption path. Currently auto-seeking only supports Steam-on-Linux at the default "
            'location. (In other words, we just default to "~/.steam/steam/steamapps/common/...")'
        ),
        default=None,
        type=Path,
    )
    parser.add_argument(
        "modname",
        help=(
            "Name to give the generated Mod. The new mod will be written to a folder with this "
            "name within GameData/Mods"
        ),
    )
    parser.add_argument(
        "--overwrite",
        help="If a mod with the same name already exists, overwrite it.",
        action="store_true",
        default=False,
    )
    parser.add_argument(
        "--bundle",
        help="If true, bundle the output into a MEGA file instead of loose XML files.",
        action="store_true",
        default=False,
    )
    parser.add_argument(
        "--tweaks",
        help=(
            "Paths to tweaks to run. These take the form of a module path followed by a colon "
            "then an item to import from that module."
        ),
        nargs="*",
        default=[
            "eaw_tweaks.builtin:projectile_speed_multiplier:2",
            'eaw_tweaks.builtin:beam_energy_weapons',
        ],
    )

    args = parser.parse_args()
    game_data = args.eaw if args.eaw is not None else DEFAULT_PATH.expanduser()
    try:
        tweaks = TweakList(_load_tweak(tweak) for tweak in args.tweaks)
    except Exception as e:
        print(f"Error loading tweaks: {e}", file=sys.stderr)
        sys.exit(1)
    sources = megafiles.list_mega_files(game_data)
    builder = ModBuilder(megafiles.get_xml_files(sources))
    tweaks.__tweak_eaw__(builder)

    try:
        builder.write_dir(
            game_data / "Mods" / args.modname,
            bundle=args.bundle,
            overwrite=args.overwrite,
        )
    except ModExistsError:
        print(
            "Refusing to overwrite non-empty mod directory without overwrite flag",
            file=sys.stderr,
        )
        sys.exit(1)


def _load_tweak(name: str) -> Tweak:
    module, item, *args = name.split(":", maxsplit=2)
    module = importlib.import_module(module)
    item = getattr(module, item)
    if args or not isinstance(item, Tweak):
        # Assume this is a factory function instead, so try to call it with optional args.
        args = _parse_tweak_args(args)
        item = args.apply(item)
    if not isinstance(item, Tweak):
        raise ValueError(f"{item!r} is not a Tweak")
    return item


def _parse_tweak_args(args: list[str]) -> Any:
    """Handle arguments to a tweak function.

    args is a list containing at most 1 item.
    """
    match args:
        case []:
            return FuncArgs()
        case [arg]:
            match json.loads(arg):
                case list() as listargs:
                    return FuncArgs(args=listargs)
                case dict() as dictargs:
                    return FuncArgs(kwargs=dictargs)
                case otherargs:
                    return FuncArgs([otherargs])
        case _:
            raise ValueError("args must have at most 1 item")
