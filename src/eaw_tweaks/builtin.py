from typing import Literal
from lxml import etree
from .tweaks import tweak
from .xmlutil import get_or_insert_child, elem


@tweak("*")
def extractall(all):
    """A utility tweak which builds a Mod containing all source XML files from the base game."""
    print("Extracting all XML configs")


def projectile_speed_multiplier(factor=2.0):
    """Applies a speed multiplier to all projectiles."""

    @tweak("/*/Projectile")
    def proj_speed_mul(projectiles):
        print(f'Adjusting all projectile speeds by {factor}')
        for projectile in projectiles:
            ms = projectile.find("Max_Speed")
            if ms is None:
                continue
            speed = float(ms.text)
            speed *= factor
            ms.text = str(speed)

    return proj_speed_mul


def uniform_lasers(mode: Literal["beam", "teardrop"]):
    match mode.lower():
        case "beam":
            return beam_lasers
        case "teardrop":
            return teardrop_lasers
        case _:
            raise ValueError(f"Unknown mode: {mode!r}")


SPACE_MODEL = 'Space_Model_Name'
LAND_MODEL = 'Land_Model_Name'
PROJ_TEX_SLOT = 'Projectile_Texture_Slot'
PROJ_WIDTH = 'Projectile_Width'
PROJ_LEN = 'Projectile_Length'


@tweak("/*/Projectile")
def beam_lasers(projectiles):
    """Converts all lasers to use beam models."""
    print('Converting all lasers to use beam models')
    for projectile in projectiles:
        name = projectile.get('Name', '').lower()
        if 'laser' not in name:
            continue
        pcr = get_or_insert_child(projectile, 'Projectile_Custom_Render')
        if pcr.text.strip() == '1':
            # Don't edit projectiles which are already using mode 1.
            continue
        pcr.text = '1'
        smn = projectile.find(SPACE_MODEL)
        if smn is None and 'ship' in name:
            smn = get_or_insert_child(projectile, SPACE_MODEL)
        lmn = projectile.find(LAND_MODEL)
        if lmn is None and 'ground' in name:
            lmn = get_or_insert_child(projectile, LAND_MODEL)
        pts = get_or_insert_child(projectile, PROJ_TEX_SLOT)
        if 'green' in name:
            pts.text = '3,0'
            if smn is not None:
                smn.text = 'W_LASER_LARGEG.ALO'
            if lmn is not None:
                lmn.text = 'W_LASER_LARGEG.ALO'
        else:
            pts.text = '0,0'
            if smn is not None:
                smn.text = 'W_LASER_LARGE.ALO'
            if lmn is not None:
                lmn.text = 'W_LASER_LARGE.ALO'
        width = projectile.find(PROJ_WIDTH)
        length = projectile.find(PROJ_LEN)
        if width is None:
            projectile.append(elem(PROJ_WIDTH, '1.5'))
        else:
            width.text = str(float(width.text) * 0.5)
        if length is None:
            projectile.append(elem(PROJ_LEN, '12.0'))
        else:
            length.text = str(float(length.text) * 3)


@tweak("/*/Projectile")
def teardrop_lasers(projectiles):
    """Converts all lasers to use teardrop renderer."""
    print('Converting all lasers to use teardrop rendering')
    pass
