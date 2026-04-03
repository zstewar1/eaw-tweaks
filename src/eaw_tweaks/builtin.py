import functools
import math
import re
from typing import Iterable, Literal

from lxml import etree

from .modbuilder import ModBuilder
from .tweaks import Tweak, TweakFilter, TweakFunctionFactory, tweak, tweak_factory, tweak_filter
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
PROJ_RENDER = "Projectile_Custom_Render"
PROJ_TEX_SLOT = "Projectile_Texture_Slot"
PROJ_WIDTH = "Projectile_Width"
PROJ_LEN = "Projectile_Length"
PROJ_COLOR = "Projectile_Laser_Color"


def name_contains_filter(fragment: str, case_sensitive=True) -> TweakFilter:
    case_sensitive = bool(case_sensitive)
    if case_sensitive:

        @tweak_filter
        def name_filter(element: etree.Element) -> bool:
            return fragment in element.get(NAME, "")
    else:
        fragment = fragment.lower()

        @tweak_filter
        def name_filter(element: etree.Element) -> bool:
            return fragment in element.get(NAME, "").lower()

    return name_filter


is_laser = name_contains_filter("Laser")
is_turbolaser = name_contains_filter("Turbolaser")
is_concussion = name_contains_filter("Concussion")
is_ion = name_contains_filter("Ion")
is_energy = is_laser | is_turbolaser | is_ion
is_proton = name_contains_filter("Proton")

is_space = name_contains_filter("Ship")
is_land = name_contains_filter("Ground")

is_small = name_contains_filter("Small")

is_space_proton = is_proton & is_space


def hardpoint_projectile_name_contains_filter(fragment: str, case_sensitive=True) -> TweakFilter:
    case_sensitive = bool(case_sensitive)
    if case_sensitive:

        @tweak_filter
        def name_filter(hardpoint: etree.Element) -> bool:
            pt = hardpoint.find(PROJECTILE_TYPE)
            if pt is None:
                return False
            return fragment in pt.text
    else:
        fragment = fragment.lower()

        @tweak_filter
        def name_filter(hardpoint: etree.Element) -> bool:
            pt = hardpoint.find(PROJECTILE_TYPE)
            if pt is None:
                return False
            return fragment in pt.text.lower()

    return name_filter


is_laser_hardpoint = hardpoint_projectile_name_contains_filter("Laser")
is_turbolaser_hardpoint = hardpoint_projectile_name_contains_filter("Turbolaser")
is_ion_hardpoint = hardpoint_projectile_name_contains_filter("Ion")

is_large_hardpoint = hardpoint_projectile_name_contains_filter("Large")
is_medium_hardpoint = hardpoint_projectile_name_contains_filter("Medium")


def support_common_filters(factory: TweakFunctionFactory) -> TweakFunctionFactory:
    """Adds support for a set of common filters as keyword arguments."""

    @tweak_factory
    @functools.wraps(factory)
    def factory_wrapper(
        *args,
        name_contains: None | str = None,
        name_contains_all: None | Iterable[str] = None,
        name_contains_any: None | Iterable[str] = None,
        proj_name_contains: None | str = None,
        proj_name_contains_all: None | Iterable[str] = None,
        proj_name_contains_any: None | Iterable[str] = None,
        **kwargs,
    ):
        tweak = factory(*args, **kwargs)
        if name_contains is not None:
            tweak = tweak.filter(name_contains_filter(name_contains))
        if name_contains_all is not None:
            tweak = tweak.filter(
                TweakFilter.all(*(name_contains_filter(substr) for substr in name_contains_all))
            )
        if name_contains_any is not None:
            tweak = tweak.filter(
                TweakFilter.any(*(name_contains_filter(substr) for substr in name_contains_any))
            )
        if proj_name_contains is not None:
            tweak = tweak.filter(hardpoint_projectile_name_contains_filter(proj_name_contains))
        if proj_name_contains_all is not None:
            filters = (
                hardpoint_projectile_name_contains_filter(substr)
                for substr in proj_name_contains_all
            )
            tweak = tweak.filter(TweakFilter.all(*filters))
        if proj_name_contains_any is not None:
            filters = (
                hardpoint_projectile_name_contains_filter(substr)
                for substr in proj_name_contains_any
            )
            tweak = tweak.filter(TweakFilter.any(*filters))
        return tweak

    return factory_wrapper


@support_common_filters
@is_energy.apply
@tweak_factory
def beam_energy_weapons(length_scale=3, width_scale=0.5, fallback_length=12, fallback_width=1.5):
    """Converts all Lasers and Ion cannons to use 'beam' style models."""

    @tweak("/*/Projectile")
    def beam_energy(projectiles):
        for projectile in projectiles:
            name = projectile.get(NAME, "")
            pcr = get_or_insert_child(projectile, PROJ_RENDER)
            if pcr.text.strip() == "1":
                # Don't edit projectiles which are already using mode 1.
                continue
            pcr.text = "1"
            smn = projectile.find(SPACE_MODEL)
            if smn is None and "Ship" in name:
                smn = get_or_insert_child(projectile, SPACE_MODEL)
            lmn = projectile.find(LAND_MODEL)
            if lmn is None and "Ground" in name:
                lmn = get_or_insert_child(projectile, LAND_MODEL)
            pts = get_or_insert_child(projectile, PROJ_TEX_SLOT)
            if "Green" in name:
                pts.text = "3,0"
                if smn is not None:
                    smn.text = "W_LASER_LARGEG.ALO"
                if lmn is not None:
                    lmn.text = "W_LASER_LARGEG.ALO"
            elif "Ion" in name:
                pts.text = "0,1"
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


@support_common_filters
@tweak_factory
def teardrop_projectiles(length_scale=0.4, width_scale=2):
    """Converts all lasers to use teardrop renderer."""

    @tweak("/*/Projectile")
    def teardrop(projectiles):
        for projectile in projectiles:
            name = projectile.get(NAME, "")
            pcr = get_or_insert_child(projectile, PROJ_RENDER)
            if pcr.text.strip() == "2":
                continue
            pcr.text = "2"
            smn = projectile.find(SPACE_MODEL)
            if smn is not None:
                projectile.remove(smn)
            lmn = projectile.find(LAND_MODEL)
            if lmn is not None:
                projectile.remove(lmn)
            color = get_or_insert_child(projectile, PROJ_COLOR)
            if "Green" in name:
                color.text = "139,230,104,255"
            else:
                color.text = "238,71,54,255"
            pts = get_or_insert_child(projectile, PROJ_TEX_SLOT)
            pts.text = "2,0"
            width = projectile.find(PROJ_WIDTH)
            if width is not None:
                width.text = str(float(width.text) * width_scale)
            length = projectile.find(PROJ_LEN)
            if length is not None:
                length.text = str(float(length.text) * length_scale)

    return teardrop


@support_common_filters
@tweak_factory
def set_projectile_size(length=1, width=1):
    @tweak("/*/Projectile")
    def scaler(projectiles):
        for projectile in projectiles:
            width_elem = get_or_insert_child(projectile, PROJ_WIDTH)
            length_elem = get_or_insert_child(projectile, PROJ_LEN)
            width_elem.text = str(width)
            length_elem.text = str(length)

    return scaler


@support_common_filters
@tweak_factory
def scale_projectiles(length_scale=1, width_scale=1):
    @tweak("/*/Projectile")
    def scaler(projectiles):
        for projectile in projectiles:
            width = projectile.find(PROJ_WIDTH)
            length = projectile.find(PROJ_LEN)
            if width is not None:
                width.text = str(float(width.text) * width_scale)
            if length is not None:
                length.text = str(float(length.text) * length_scale)

    return scaler


@support_common_filters
@tweak_factory
def projectile_aspect_ratio(aspect=50):
    """Scales projectiles to a target aspect ratio, where length is aspect * width."""

    @tweak("/*/Projectile")
    def scaler(projectiles):
        for projectile in projectiles:
            width_elem = projectile.find(PROJ_WIDTH)
            length_elem = projectile.find(PROJ_LEN)
            if width_elem is not None and length_elem is not None:
                # Re-scale maintaining roughly the same effective visual area
                width = float(width_elem.text)
                length = float(length_elem.text)
                area = width * length
                # We want area = length * wwidth and l = width * aspect
                # So we have area = width * aspect * width
                # area = width**2 * aspect
                # area / aspect = width**2
                width = math.sqrt(area / aspect)
                length = width * aspect
                width_elem.text = str(round(width, 1))
                length_elem.text = str(round(length, 1))

    return scaler


@support_common_filters
@tweak_factory
def colorize_projectile(color: str):
    @tweak("/*/Projectile")
    def recolor(projectiles):
        for projectile in projectiles:
            color_elem = projectile.find(PROJ_COLOR)
            if color_elem is not None:
                color_elem.text = color

    return recolor


MIN_RECHARGE = "Fire_Min_Recharge_Seconds"
MAX_RECHARGE = "Fire_Max_Recharge_Seconds"
PULSE_COUNT = "Fire_Pulse_Count"
PULSE_DELAY = "Fire_Pulse_Delay_Seconds"
PROJECTILE_TYPE = "Fire_Projectile_Type"
INACCURACY = "Fire_Inaccuracy_Distance"

# Ordered by increasing size!
SPACE_ACCURACY_CATEGORIES = (
    "Fighter",
    "Bomber",
    "Transport",
    "Corvette",
    "Frigate",
    "Capital",
    "Super",
)
LAND_ACCURACY_CATEGORIES = (
    "Air",
    "Infantry",
    "Vehicle",
    "Structure",
)


@support_common_filters
@tweak_factory
def hardpoint_pulse_balance(
    pulse_delay=None,
    pulse_count=None,
    min_avg_delay_multiplier=None,
    max_avg_delay_multiplier=None,
    pulse_delay_multiplier=None,
    pulse_count_multiplier=None,
):
    """Recalculates hardpoint pulse fire rates to rebalance while keeping same overall fire rate."""

    @tweak("/*/HardPoint")
    def reburst(hardpoints):
        for hardpoint in hardpoints:
            pulse_count_elem = hardpoint.find(PULSE_COUNT)
            if pulse_count_elem is None:
                continue
            pulse_delay_elem = hardpoint.find(PULSE_DELAY)
            min_recharge_elem = hardpoint.find(MIN_RECHARGE)
            max_recharge_elem = hardpoint.find(MAX_RECHARGE)

            old_delay = float(pulse_delay_elem.text)
            old_count = int(pulse_count_elem.text)
            old_min = float(min_recharge_elem.text)
            old_max = float(max_recharge_elem.text)

            # we assume that pulse_delay applies only between shots not after.
            old_fire_time = max(old_count - 1, 0) * old_delay
            old_min_total = old_fire_time + old_min
            old_max_total = old_fire_time + old_max
            min_avg = old_min_total / old_count
            if min_avg_delay_multiplier is not None:
                min_avg *= min_avg_delay_multiplier
            max_avg = old_max_total / old_count
            if max_avg_delay_multiplier is not None:
                max_avg *= max_avg_delay_multiplier

            new_pulse_delay = old_delay if pulse_delay is None else pulse_delay
            if pulse_delay_multiplier is not None:
                new_pulse_delay *= pulse_delay_multiplier
            new_pulse_count = old_count if pulse_count is None else pulse_count
            if pulse_count_multiplier is not None:
                new_pulse_count = round(pulse_count * pulse_count_multiplier)

            fire_time = max(new_pulse_count - 1, 0) * new_pulse_delay
            min_total = min_avg * new_pulse_count
            max_total = max_avg * new_pulse_count
            min_recharge = min_total - fire_time
            max_recharge = max_total - fire_time

            pulse_count_elem.text = str(new_pulse_count)
            pulse_delay_elem.text = str(new_pulse_delay)
            min_recharge_elem.text = str(round(min_recharge, 2))
            max_recharge_elem.text = str(round(max_recharge, 2))

    return reburst


@support_common_filters
@tweak_factory
def accuracy_on_larger_targets(
    # As long as nothing has both land and space accuracy categories, merging them works.
    size_order: Iterable[str] = SPACE_ACCURACY_CATEGORIES + LAND_ACCURACY_CATEGORIES,
    max_increase=10,
    limit_mode: Literal["min", "previous"] = "previous",
    increase_mode: Literal["add", "mul"] = "add",
):
    """Makes it so larger space targets never have lower inaccuracy distances than smaller targets.

    Checks the inaccuracy distance of each size of ship in order from smallest to largest. Every
    larger size can have an inaccuracy distance of at most 'max_increase' from a smaller size ship,
    either the smallest size if limit_mode is 'min' or the inaccuracy of the previous size ship
    (after transform) if limit_mode is 'previous'.

    The max_increase allows some increase in shot dispersion for larger targets, since larger
    targets have more surface area to hit.

    increaes_mode determines whether the max_increase is an additive amount or a multiplicative
    amount.
    """

    @tweak("/*/SpaceUnit[Fire_Inaccuracy_Distance] | /*/HardPoint[Fire_Inaccuracy_Distance]")
    def inaccuracy(shooters):
        for shooter in shooters:
            inaccuracies = InaccuracyMap(shooter)
            prev = None
            for category in size_order:
                inaccuracy = inaccuracies.get(category)
                if inaccuracy is None:
                    continue
                if prev is None:
                    prev = inaccuracy.value
                    continue
                match increase_mode:
                    case "add":
                        limit = prev + max_increase
                    case "mul":
                        limit = prev * max_increase
                    case _:
                        raise ValueError(f"Unexpected incrase_mode: {increase_mode}")
                inaccuracy.value = min(inaccuracy.value, limit)
                match limit_mode:
                    case "min":
                        prev = min(prev, inaccuracy.value)
                    case "previous":
                        prev = inaccuracy.value
                    case _:
                        raise ValueError(f"Unexpected limit_mode: {limit_mode}")

    return inaccuracy


class InaccuracyEntry:
    """Represents one Fire_Inaccuracy_Distance element."""

    def __init__(self, name: str, value: float, element: etree.Element):
        self._name = name
        self._value = value
        self._element = element

    def _update_element(self):
        self._element.text = f" {self._name}, {round(self._value, 1)} "

    @property
    def name(self) -> str:
        return self._name

    @property
    def value(self) -> float:
        return self._value

    @value.setter
    def value(self, value: float):
        self._value = value
        self._update_element()


class InaccuracyMap:
    """Map that collects all Fire_Inaccuracy_Distance entries from an XML node."""

    INACCURACY_MATCHER = re.compile(
        r"^\s*(?P<category>\w+)\s*,\s*(?P<distance>\d+(?:\.(?:\d+)?)?)\s*$"
    )

    def __init__(self, shooter: etree.Element):
        self._entries = {}
        for inaccuracy in shooter.findall(INACCURACY):
            match = InaccuracyMap.INACCURACY_MATCHER.match(inaccuracy.text)
            if match is None:
                raise ValueError(f"Inaccuracy entry not in expected format: {inaccuracy.text}")
            category = match["category"]
            distance = float(match["distance"])
            self._entries[category] = InaccuracyEntry(category, distance, inaccuracy)

    def __getitem__(self, category: str) -> InaccuracyEntry:
        return self._entries[category]

    def get(self, category: str) -> InaccuracyEntry | None:
        return self._entries.get(category)

    def __contains__(self, category: str) -> bool:
        return category in self._entries

    def __iter__(self) -> Iterable[InaccuracyEntry]:
        return self._entries.values()


@tweak_factory
def increase_max_zoom_out(max_scale_factor=1.8):
    """Tries to increase the max zoom out.

    This doesn't work, for some unknown reason. Having this file in the mod at all makes the view
    permanently zoom in more rather than allowing you to zoom out more.
    """

    @tweak("/*/TacticalCamera")
    def zoom(cameras):
        for camera in cameras:
            max_distance = get_or_insert_child(camera, "Distance_Max")
            max_dist = float(max_distance.text)
            tac_overview1 = camera.find("Tactical_Overview_Distance")
            tac_ov1 = float(tac_overview1.text) if tac_overview1 is not None else max_dist
            tac_overview2 = camera.find("Tactical_Overview_Distance2")
            tac_ov2 = float(tac_overview2.text) if tac_overview2 is not None else tac_ov1
            tac_ov1_multiplier = tac_ov1 / max_dist
            tac_ov2_multiplier = tac_ov2 / max_dist

            max_dist *= max_scale_factor
            max_distance.text = str(round(max_dist, 1))
            tac_ov1 = max_dist * tac_ov1_multiplier
            tac_ov2 = max_dist * tac_ov2_multiplier
            if tac_overview1 is not None:
                tac_overview1.text = str(round(tac_ov1, 1))
            if tac_overview2 is not None:
                tac_overview2.text = str(round(tac_ov2, 1))

    return zoom
