"""Contains my preferred tweaks."""

from eaw_tweaks.builtin import (
    LAND_ACCURACY_CATEGORIES,
    SPACE_ACCURACY_CATEGORIES,
    accuracy_on_larger_targets,
    colorize_projectile,
    fire_projectile_name_contains,
    fires_ion,
    fires_large,
    fires_laser,
    fires_medium,
    fires_turbolaser,
    hardpoint_pulse_balance,
    name_contains,
    named_concussion,
    named_ion,
    named_laser,
    named_proton,
    named_ship,
    named_small,
    named_turbolaser,
    projectile_aspect_ratio,
    projectile_speed_multiplier,
    scale_projectiles,
    set_projectile_size,
    teardrop_projectiles,
)
from eaw_tweaks.tweaks import TweakFilter, TweakList

# Makes all lasers into the turbolaser style used for turbolasers, and makes them longer and
# narrower.
energy_projectile_tweaks = TweakList.of(
    teardrop_projectiles(length_scale=0.7, width_scale=3).filter(named_laser),
    # Slightly increase ion and turbo size to keep them above large lasers. We'll also increase the
    # aspect ratio later which makes them look less chonky.
    scale_projectiles(length_scale=1.5, width_scale=1.5).filter(named_turbolaser | named_ion),
    # Boost the size of small lasers
    scale_projectiles(length_scale=1.5, width_scale=1.5).filter(named_laser & named_small),
    projectile_aspect_ratio(aspect=8).filter(named_laser | named_turbolaser | named_ion),
)

# Makes concussion missiles into orange glow streaks instead of mechanical projectile missiles.
concussion_missile_tweaks = TweakList.of(
    teardrop_projectiles().filter(named_concussion & named_ship),
    set_projectile_size(width=5, length=4).filter(named_concussion & named_ship),
    colorize_projectile(color="255,210,90,255").filter(named_concussion & named_ship),
)

# Makes proton torpedoes purple and makes them longer.
proton_tweaks = TweakList.of(
    colorize_projectile(color="190,130,255,255").filter(named_proton & named_ship),
    projectile_aspect_ratio(aspect=6, scale=1.5).filter(named_proton & named_ship),
)

projectile_tweaks = TweakList.of(
    projectile_speed_multiplier(2),
    energy_projectile_tweaks,
    concussion_missile_tweaks,
    proton_tweaks,
)

SINGLE_FIRE_TURBOLASERS = TweakFilter.any(
    name_contains("Acclamator"),
    fire_projectile_name_contains("Red") & ~name_contains("Assault_Frigate"),
)

MEDIUM_LASER_DOUBLE_FIRE = TweakFilter.any(
    name_contains("Corellian_Corvette"),
    name_contains("Interdictor"),
)

DOUBLE_FIRE_ION = TweakFilter.any(
    name_contains("Star_Destroyer"),
)

# Re-balances all hardpoint fire-rates.
hardpoint_tweaks = TweakList.of(
    # Make all large lasers fire single shots continuously.
    hardpoint_pulse_balance(pulse_count=1).filter(fires_laser & fires_large),
    # Make all ion cannons fire single shots continuously, except Star Destroyers which fire double
    # shots.
    hardpoint_pulse_balance(pulse_count=1).filter(fires_ion & ~DOUBLE_FIRE_ION),
    hardpoint_pulse_balance(pulse_count=2, pulse_delay=0.06).filter(fires_ion & DOUBLE_FIRE_ION),
    # Make rebel ships and acclamators fire single turbolasers, and make imperial ships fire dual
    # turbolasers.
    hardpoint_pulse_balance(pulse_count=1).filter(fires_turbolaser & SINGLE_FIRE_TURBOLASERS),
    hardpoint_pulse_balance(pulse_count=2, pulse_delay=0.06).filter(
        fires_turbolaser & ~SINGLE_FIRE_TURBOLASERS & ~name_contains("Assault_Frigate")
    ),
    # Make the assult frigate fire in pairs but slightly slower for a little variety.
    hardpoint_pulse_balance(pulse_count=2, pulse_delay=0.2).filter(
        fires_turbolaser & ~SINGLE_FIRE_TURBOLASERS & name_contains("Assault_Frigate")
    ),
    # Make medium lasers (mostly corvettes) fire single shots unless they are in the double fire
    # list. Note that I believe this possibly breaks the boost-fire modifier.
    hardpoint_pulse_balance(pulse_count=1).filter(
        fires_laser & fires_medium & ~MEDIUM_LASER_DOUBLE_FIRE
    ),
    hardpoint_pulse_balance(pulse_delay=0.02, pulse_count=2).filter(MEDIUM_LASER_DOUBLE_FIRE),
)


accuracy_tweaks = TweakList.of(
    accuracy_on_larger_targets(SPACE_ACCURACY_CATEGORIES),
    accuracy_on_larger_targets(LAND_ACCURACY_CATEGORIES),
)


all = TweakList.of(
    projectile_tweaks,
    hardpoint_tweaks,
    accuracy_tweaks,
)
