def compute_crop_evapotranspiration(et0: float, kc: float) -> float:
    """
    Computes Crop Evapotranspiration (ETc) using FAO-56.
    ETc = Kc * ET0
    """
    return et0 * kc


def update_soil_water_balance(
    prev_sw: float, precip: float, etc: float, runoff: float = 0.0, deep_perc: float = 0.0
) -> float:
    """
    Computes updated Soil Water content (SW) using simplified water balance equation.
    SW_t = SW_{t-1} + P - ETc - RO - DP
    """
    new_sw = prev_sw + precip - etc - runoff - deep_perc
    return max(0.0, new_sw)
