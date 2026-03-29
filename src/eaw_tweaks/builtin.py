from .tweaks import tweak

@tweak()
def default():
    print('No tweaks applied')


@tweak('*')
def extractall(all):
    """A utility tweak which builds a Mod containing all source XML files from the base game."""
    print("Extracting all XML configs")


def projectile_speed_multiplier(factor = 2.0):
    """Applies a speed multiplier to all projectiles."""
    @tweak('/*/Projectile')
    def proj_speed_mul(projectiles):
        for projectile in projectiles:
            ms = projectile.find('Max_Speed')
            if ms is not None:
                speed = float(ms.text)
                speed *= factor
                ms.text = str(speed)
    return proj_speed_mul
