from datetime import date

import ee

from geointel.providers.base import AdminUnitRef, MeasuredValue
from geointel.providers.gee import reduce_regions


class Era5LandProvider:
    """
    ECMWF ERA5-Land Daily Aggregated
    Metric: potential_evaporation (useful for ET0 in water balance)
    """

    metric_id = "et0_era5"

    def fetch(self, units: list[AdminUnitRef], start: date, end: date) -> dict[int, MeasuredValue]:
        start_str = start.isoformat()
        end_str = end.isoformat()

        # ERA5-Land Daily
        col = ee.ImageCollection("ECMWF/ERA5_LAND/DAILY_AGGR").filterDate(start_str, end_str)

        # Potential evaporation sum (in meters)
        # We multiply by 1000 to get millimeters
        pe = col.select("potential_evaporation_sum").sum().multiply(1000.0)

        is_valid = col.select("potential_evaporation_sum").count().gt(0).rename("quality")

        # ERA5-Land resolution is ~11.1km
        pe_res = reduce_regions(pe, units, ee.Reducer.mean(), scale=11132)
        qual_res = reduce_regions(is_valid, units, ee.Reducer.mean(), scale=11132)

        out = {}
        for unit in units:
            val = pe_res.get(unit.id, {}).get("mean")
            qual = qual_res.get(unit.id, {}).get("mean")

            if val is None:
                val = 0.0
            if qual is None:
                qual = 0.0

            # Absolute value of potential evaporation (it can be negative in ERA5 convention)
            out[unit.id] = MeasuredValue(value=abs(float(val)), quality=float(qual))

        return out
