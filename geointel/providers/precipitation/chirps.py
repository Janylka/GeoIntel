from datetime import date

import ee

from geointel.providers.base import AdminUnitRef, MeasuredValue
from geointel.providers.gee import reduce_regions


class ChirpsProvider:
    metric_id = "precipitation"

    def fetch(self, units: list[AdminUnitRef], start: date, end: date) -> dict[int, MeasuredValue]:
        start_str = start.isoformat()
        end_str = end.isoformat()

        # CHIRPS daily precipitation (mm)
        # Using UCSB-CHG/CHIRPS/DAILY
        col = ee.ImageCollection("UCSB-CHG/CHIRPS/DAILY").filterDate(start_str, end_str)

        # Sum precipitation for the period
        precip = col.select("precipitation").sum()

        # Check if we have valid data (CHIRPS is wall-to-wall but good for quality metric)
        is_valid = col.select("precipitation").count().gt(0).rename("quality")

        # CHIRPS has a resolution of ~5566 meters (0.05 degrees)
        # We don't apply the cropland mask to precipitation since rain falls everywhere,
        # but if we wanted to only measure over cropland, we could.
        # Usually, precipitation is measured over the entire admin unit.
        precip_res = reduce_regions(precip, units, ee.Reducer.mean(), scale=5566)
        qual_res = reduce_regions(is_valid, units, ee.Reducer.mean(), scale=5566)

        out = {}
        for unit in units:
            val = precip_res.get(unit.id, {}).get("mean")
            qual = qual_res.get(unit.id, {}).get("mean")

            if val is None:
                val = 0.0
            if qual is None:
                qual = 0.0

            out[unit.id] = MeasuredValue(value=float(val), quality=float(qual))

        return out
