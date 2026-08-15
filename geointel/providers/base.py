from dataclasses import dataclass
from datetime import date
from typing import Any, Protocol


@dataclass(frozen=True)
class AdminUnitRef:
    id: int
    geom: dict[str, Any]  # GeoJSON representation


@dataclass(frozen=True)
class MeasuredValue:
    value: float
    quality: float  # 0..1


class RasterProvider(Protocol):
    metric_id: str

    def fetch(self, units: list[AdminUnitRef], start: date, end: date) -> dict[int, MeasuredValue]:
        ...
