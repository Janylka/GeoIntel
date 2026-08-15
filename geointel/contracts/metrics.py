from dataclasses import dataclass

from geointel.contracts.scope import Scope


class ScopeTooFineError(ValueError):
    def __init__(self, metric_id: str, min_scope: Scope, requested: Scope):
        self.metric_id = metric_id
        self.min_scope = min_scope
        self.requested = requested
        super().__init__(
            f"Metric '{metric_id}' cannot be displayed at '{requested.value}' scope. "
            f"Minimum scope is '{min_scope.value}'."
        )


@dataclass(frozen=True)
class MetricDef:
    id: str
    source: str
    native_resolution_m: int
    min_scope: Scope
    unit: str
    higher_is_better: bool
    decimals: int


METRICS: dict[str, MetricDef] = {
    "ndvi": MetricDef("ndvi", "Sentinel-2 SR Harmonized", 10, Scope.FIELD, "ratio", True, 3),
    "ndvi_hist": MetricDef(
        "ndvi_hist", "MODIS MOD13Q1", 250, Scope.DISTRICT, "ratio", True, 3
    ),
    "lst": MetricDef("lst", "MODIS MOD11A2", 1000, Scope.DISTRICT, "°C", False, 1),
    "vci": MetricDef("vci", "derived", 250, Scope.DISTRICT, "0-100", True, 1),
    "tci": MetricDef("tci", "derived", 1000, Scope.DISTRICT, "0-100", True, 1),
    "vhi": MetricDef("vhi", "derived", 1000, Scope.DISTRICT, "0-100", True, 1),
    "spi_1": MetricDef("spi_1", "CHIRPS Daily", 5000, Scope.DISTRICT, "sigma", True, 2),
    "spi_3": MetricDef("spi_3", "CHIRPS Daily", 5000, Scope.DISTRICT, "sigma", True, 2),
    # SMAP provides soil moisture at a 9km resolution.
    # A single pixel covers 81 sq km (8100 hectares).
    # Displaying this metric at the field level would be misleading, as a pixel can contain
    # a mix of fields, slopes, and bare rock, especially in Kyrgyzstan's terrain.
    # Therefore, we enforce a minimum scope of 'district'.
    "soil_moisture": MetricDef(
        "soil_moisture", "SMAP L4 SPL4SMGP", 9000, Scope.DISTRICT, "m3/m3", True, 3
    ),
    "ndwi": MetricDef("ndwi", "Sentinel-2", 10, Scope.FIELD, "ratio", True, 3),
    "yield_wheat": MetricDef("yield_wheat", "regression", 250, Scope.DISTRICT, "c/ha", True, 1),
}


def get_metric_def(metric_id: str) -> MetricDef:
    """
    Retrieves a metric definition by its ID.
    Raises a KeyError if the metric_id is not found.
    """
    if metric_id not in METRICS:
        raise KeyError(f"Metric '{metric_id}' is not defined.")
    return METRICS[metric_id]


def assert_scope_allowed(metric_id: str, scope: Scope) -> None:
    """
    Checks if a given metric can be displayed at the requested scope.

    Raises:
        ScopeTooFineError: If the requested scope is finer than the metric's minimum scope.
        KeyError: If the metric_id is not found.
    """
    metric_def = get_metric_def(metric_id)
    if scope.is_finer_than(metric_def.min_scope):
        raise ScopeTooFineError(
            metric_id=metric_id,
            min_scope=metric_def.min_scope,
            requested=scope,
        )
