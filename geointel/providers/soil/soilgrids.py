from datetime import date

import ee

from geointel.providers.base import AdminUnitRef, MeasuredValue
from geointel.providers.gee import reduce_regions


class SoilGridsProvider:
    """
    SoilGrids 250m 2.0
    Metric: soil_organic_carbon (or we could fetch sand/clay)
    This is static data, independent of date.
    """

    metric_id = "soilgrids_ocd"

    def fetch(self, units: list[AdminUnitRef], start: date, end: date) -> dict[int, MeasuredValue]:
        # Soil organic carbon density (ocd) at 0-5cm depth
        img = ee.Image("projects/soilgrids-isric/ocd_mean")

        # Select the 0-5cm band
        ocd = img.select("ocd_0-5cm_mean")

        # SoilGrids has data where soil exists
        is_valid = ocd.mask().rename("quality")

        # 250m resolution
        ocd_res = reduce_regions(ocd, units, ee.Reducer.mean(), scale=250)
        qual_res = reduce_regions(is_valid, units, ee.Reducer.mean(), scale=250)

        out = {}
        for unit in units:
            val = ocd_res.get(unit.id, {}).get("mean")
            qual = qual_res.get(unit.id, {}).get("mean")

            if val is None:
                val = 0.0
            if qual is None:
                qual = 0.0

            out[unit.id] = MeasuredValue(value=float(val), quality=float(qual))

        return out
