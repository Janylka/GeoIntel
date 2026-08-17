from datetime import date

import ee

from geointel.providers.base import AdminUnitRef, MeasuredValue
from geointel.providers.gee import get_cropland_mask, reduce_regions


class SmapProvider:
    """
    NASA/USDA SMAP Global Soil Moisture.
    Metric: sm (soil moisture)
    """

    metric_id = "soil_moisture"

    def fetch(self, units: list[AdminUnitRef], start: date, end: date) -> dict[int, MeasuredValue]:
        start_str = start.isoformat()
        end_str = end.isoformat()

        # Using SMAP Level 4 Soil Moisture. "NASA_USDA/SMAP/SMAP_L4_SM_aup" (the
        # original asset ID here) doesn't exist in the EE catalog at all --
        # confirmed live: NASA/SMAP/SPL4SMGP/007 is the real (if deprecated) ID,
        # already superseded by /008.
        col = ee.ImageCollection("NASA/SMAP/SPL4SMGP/008").filterDate(start_str, end_str)

        # 'sm_surface' or 'sm_rootzone'
        sm = col.select("sm_rootzone").median()

        is_valid = col.select("sm_rootzone").count().gt(0).rename("quality")

        cropland_mask = get_cropland_mask()
        sm_masked = sm.updateMask(cropland_mask)
        is_valid_masked = is_valid.updateMask(cropland_mask)

        # SMAP L4 resolution is 9000m
        sm_res = reduce_regions(sm_masked, units, ee.Reducer.mean(), scale=9000)
        qual_res = reduce_regions(is_valid_masked, units, ee.Reducer.mean(), scale=9000)

        out = {}
        for unit in units:
            val = sm_res.get(unit.id, {}).get("mean")
            qual = qual_res.get(unit.id, {}).get("mean")

            if val is None:
                val = 0.0
            if qual is None:
                qual = 0.0

            out[unit.id] = MeasuredValue(value=float(val), quality=float(qual))

        return out
