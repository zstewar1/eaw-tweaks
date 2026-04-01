from lxml import etree

from .modbuilder import ModBuilder
from .tweaks import Tweak, tweak, tweak_factory
from .xmlutil import elem, get_or_insert_child


class extractall(Tweak):
    """A utility tweak which builds a Mod containing all source XML files from the base game."""

    def __tweak_eaw__(self, configs: ModBuilder):
        print("Extracting all XML configs")
        configs.mark_modified(*configs.files())


@tweak_factory
def projectile_speed_multiplier(factor=2.0):
    """Applies a speed multiplier to all projectiles."""

    @tweak("/*/Projectile")
    def proj_speed_mul(projectiles):
        for projectile in projectiles:
            ms = projectile.find("Max_Speed")
            if ms is None:
                continue
            speed = float(ms.text)
            speed *= factor
            ms.text = str(speed)

    return proj_speed_mul


NAME = "Name"
SPACE_MODEL = "Space_Model_Name"
LAND_MODEL = "Land_Model_Name"
PROJ_TEX_SLOT = "Projectile_Texture_Slot"
PROJ_WIDTH = "Projectile_Width"
PROJ_LEN = "Projectile_Length"


def is_laser(projectile: etree.Element) -> bool:
    name = projectile.get(NAME, "").lower()
    return 'laser' in name


@tweak_factory
def beam_energy_weapons(
    length_scale=3, width_scale=0.5, fallback_length=12, fallback_width=1.5
):
    """Converts all Lasers and Ion cannons to use 'beam' style models."""
    @tweak("/*/Projectile")
    def beam_energy(projectiles):
        for projectile in projectiles:
            name = projectile.get(NAME, "").lower()
            if "laser" not in name and "ion" not in name:
                continue
            pcr = get_or_insert_child(projectile, "Projectile_Custom_Render")
            if pcr.text.strip() == "1":
                # Don't edit projectiles which are already using mode 1.
                continue
            pcr.text = "1"
            smn = projectile.find(SPACE_MODEL)
            if smn is None and "ship" in name:
                smn = get_or_insert_child(projectile, SPACE_MODEL)
            lmn = projectile.find(LAND_MODEL)
            if lmn is None and "ground" in name:
                lmn = get_or_insert_child(projectile, LAND_MODEL)
            pts = get_or_insert_child(projectile, PROJ_TEX_SLOT)
            if "green" in name:
                pts.text = "3,0"
                if smn is not None:
                    smn.text = "W_LASER_LARGEG.ALO"
                if lmn is not None:
                    lmn.text = "W_LASER_LARGEG.ALO"
            elif "ion" in name:
                pts.text = "2,0"
                if smn is not None:
                    smn.text = "W_LASER_LARGEG.ALO"
                if lmn is not None:
                    lmn.text = "W_LASER_LARGEG.ALO"
            else:
                pts.text = "0,0"
                if smn is not None:
                    smn.text = "W_LASER_LARGE.ALO"
                if lmn is not None:
                    lmn.text = "W_LASER_LARGE.ALO"
            width = projectile.find(PROJ_WIDTH)
            length = projectile.find(PROJ_LEN)
            if width is None:
                projectile.append(elem(PROJ_WIDTH, str(fallback_width)))
            else:
                width.text = str(float(width.text) * width_scale)
            if length is None:
                projectile.append(elem(PROJ_LEN, str(fallback_length)))
            else:
                length.text = str(float(length.text) * length_scale)

    return beam_energy


beamp_lasers = beam_energy_weapons.filter(is_laser)


@tweak("/*/Projectile")
def teardrop_lasers(projectiles):
    """Converts all lasers to use teardrop renderer."""
    print("Converting all lasers to use teardrop rendering")
