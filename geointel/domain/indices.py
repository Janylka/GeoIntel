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
