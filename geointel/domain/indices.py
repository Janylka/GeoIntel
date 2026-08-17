def compute_vci(ndvi: float, ndvi_min: float, ndvi_max: float) -> float:
    """
    Computes Vegetation Condition Index (VCI).
    Range: 0 to 100.
    """
    if ndvi_max == ndvi_min:
        return 50.0

    vci = 100.0 * (ndvi - ndvi_min) / (ndvi_max - ndvi_min)
    return max(0.0, min(100.0, vci))


def compute_tci(lst: float, lst_min: float, lst_max: float) -> float:
    """
    Computes Temperature Condition Index (TCI).
    Range: 0 to 100.
    Note: Lower temperatures correspond to better conditions (higher TCI).
    """
    if lst_max == lst_min:
        return 50.0

    tci = 100.0 * (lst_max - lst) / (lst_max - lst_min)
    return max(0.0, min(100.0, tci))


def compute_vhi(vci: float, tci: float, alpha: float = 0.5) -> float:
    """
    Computes Vegetation Health Index (VHI) from VCI and TCI.
    Range: 0 to 100.
    """
    return alpha * vci + (1.0 - alpha) * tci


# Named per PROJECT.md section 3.5 -- kept as constants (not magic numbers)
# specifically so alert/severity logic and the batch's agent_event log always
# agree on the same thresholds.
VHI_EXTREME_MAX = 30.0
VHI_SEVERE_MAX = 40.0
VHI_MODERATE_MAX = 45.0
VHI_NORMAL_MAX = 60.0


def classify_vhi(vhi: float) -> str:
    """Maps a VHI value to its drought severity band."""
    if vhi < VHI_EXTREME_MAX:
        return "extreme"
    if vhi < VHI_SEVERE_MAX:
        return "severe"
    if vhi < VHI_MODERATE_MAX:
        return "moderate"
    if vhi < VHI_NORMAL_MAX:
        return "normal"
    return "favorable"


def compute_spi(precip: float, precip_mean: float, precip_std: float) -> float:
    """
    Computes a simplified Standardized Precipitation Index (SPI) using Z-score.
    SPI = (P - mean) / std
    """
    if precip_std == 0.0:
        return 0.0
    return (precip - precip_mean) / precip_std
