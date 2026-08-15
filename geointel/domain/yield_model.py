def predict_yield(
    baseline_yield: float, vhi: float, spi: float, alpha: float = 0.2, beta: float = 0.1
) -> float:
    """
    Simple statistical crop yield model based on VHI and SPI.

    :param baseline_yield: Historical average yield (e.g. ton/ha)
    :param vhi: Vegetation Health Index (0-100)
    :param spi: Standardized Precipitation Index (Z-score)
    :param alpha: Sensitivity to VHI
    :param beta: Sensitivity to SPI
    :return: Predicted yield
    """
    # Normalize VHI from [0, 100] to [-1, 1] relative to normal (50)
    vhi_factor = (vhi - 50.0) / 50.0

    # Calculate yield multiplier
    multiplier = 1.0 + (alpha * vhi_factor) + (beta * spi)

    predicted = baseline_yield * multiplier
    return max(0.0, predicted)
