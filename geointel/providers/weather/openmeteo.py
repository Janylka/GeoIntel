import json
import urllib.request
from datetime import date
from typing import Any

from geointel.providers.base import AdminUnitRef, MeasuredValue


def get_centroid(geom: dict[str, Any]) -> tuple[float, float]:
    """
    Very basic centroid calculation from GeoJSON.
    Returns (longitude, latitude).
    """
    if geom["type"] == "Polygon":
        coords = geom["coordinates"][0]
    elif geom["type"] == "MultiPolygon":
        coords = geom["coordinates"][0][0]
    else:
        return 0.0, 0.0

    lons = [c[0] for c in coords]
    lats = [c[1] for c in coords]
    if not lons or not lats:
        return 0.0, 0.0

    return sum(lons) / len(lons), sum(lats) / len(lats)


class OpenMeteoProvider:
    """
    Provider for Weather data via Open-Meteo Historical API.
    Does not use Google Earth Engine.
    """

    metric_id = "weather"

    def fetch(self, units: list[AdminUnitRef], start: date, end: date) -> dict[int, MeasuredValue]:
        out = {}
        start_str = start.isoformat()
        end_str = end.isoformat()

        for unit in units:
            lon, lat = get_centroid(unit.geom)
            if lon == 0.0 and lat == 0.0:
                continue

            # We fetch daily temperature (mean) and precipitation sum
            url = (
                f"https://archive-api.open-meteo.com/v1/archive?"
                f"latitude={lat}&longitude={lon}&start_date={start_str}&end_date={end_str}"
                f"&daily=temperature_2m_mean,precipitation_sum&timezone=auto"
            )

            try:
                with urllib.request.urlopen(url) as response:
                    data = json.loads(response.read().decode())
                    daily = data.get("daily", {})

                    temps = daily.get("temperature_2m_mean", [])
                    precips = daily.get("precipitation_sum", [])

                    valid_temps = [t for t in temps if t is not None]
                    valid_precips = [p for p in precips if p is not None]

                    if valid_temps and valid_precips:
                        # Return mean temp as the primary value for this metric.
                        # (Or we can define different metric_ids, but standard signature returns one value).
                        # Let's return mean temperature here, or we can adapt the protocol for multiple.
                        # Since MeasuredValue has one value, let's return temperature.
                        mean_t = sum(valid_temps) / len(valid_temps)
                        out[unit.id] = MeasuredValue(value=mean_t, quality=1.0)
            except Exception:
                # Log or handle error if needed
                pass

        return out
