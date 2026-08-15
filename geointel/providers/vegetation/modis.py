from datetime import date

import ee

from geointel.providers.base import AdminUnitRef, MeasuredValue
from geointel.providers.gee import get_cropland_mask, reduce_regions


class ModisNdviProvider:
    metric_id = "ndvi_hist"

    def fetch(self, units: list[AdminUnitRef], start: date, end: date) -> dict[int, MeasuredValue]:
        start_str = start.isoformat()
        end_str = end.isoformat()

        col = ee.ImageCollection("MODIS/061/MOD13Q1").filterDate(start_str, end_str)

        def mask_qa(image: ee.Image) -> ee.Image:
            # SummaryQA: 0=Good, 1=Marginal, 2=Snow/Ice, 3=Cloudy
            qa = image.select("SummaryQA")
            mask = qa.lte(1)
            return image.updateMask(mask)

        processed_col = col.map(mask_qa)

        # Scale factor is 0.0001
        ndvi = processed_col.select("NDVI").median().multiply(0.0001)

        is_valid = processed_col.select("NDVI").count().gt(0).rename("quality")

        cropland_mask = get_cropland_mask()
        ndvi_masked = ndvi.updateMask(cropland_mask)
        is_valid_masked = is_valid.updateMask(cropland_mask)

        # MODIS NDVI is 250m scale
        ndvi_res = reduce_regions(ndvi_masked, units, ee.Reducer.mean(), scale=250)
        qual_res = reduce_regions(is_valid_masked, units, ee.Reducer.mean(), scale=250)

        out = {}
        for unit in units:
            val = ndvi_res.get(unit.id, {}).get("mean")
            qual = qual_res.get(unit.id, {}).get("mean")

            if val is None:
                val = 0.0
            if qual is None:
                qual = 0.0

            out[unit.id] = MeasuredValue(value=float(val), quality=float(qual))

        return out


class ModisLstProvider:
    metric_id = "lst"

    def fetch(self, units: list[AdminUnitRef], start: date, end: date) -> dict[int, MeasuredValue]:
        start_str = start.isoformat()
        end_str = end.isoformat()

        col = ee.ImageCollection("MODIS/061/MOD11A2").filterDate(start_str, end_str)

        def mask_qa(image: ee.Image) -> ee.Image:
            # QC_Day bit 0-1: 00 = good quality, 01 = other quality.
            # 10 = not produced due to cloud effects, 11 = not produced other reasons.
            # We can use a simple check or bitwise. It's an 8-day composite.
            # LST error flag is bits 6-7.
            # Let's keep if pixel was produced.
            # A simple way to check if it's produced is just check if LST is > 0,
            # but QC_Day bit 1 is 'not produced'. Let's bitwise AND with 0x02.
            # If bit 1 is 1 (value 2), it's bad.
            qc = image.select("QC_Day")
            mask = qc.bitwiseAnd(2).eq(0)
            return image.updateMask(mask)

        processed_col = col.map(mask_qa)

        # Scale factor 0.02, unit Kelvin. Convert to Celsius.
        lst = processed_col.select("LST_Day_1km").median().multiply(0.02).subtract(273.15)

        is_valid = processed_col.select("LST_Day_1km").count().gt(0).rename("quality")

        cropland_mask = get_cropland_mask()
        lst_masked = lst.updateMask(cropland_mask)
        is_valid_masked = is_valid.updateMask(cropland_mask)

        # MODIS LST is 1000m scale
        lst_res = reduce_regions(lst_masked, units, ee.Reducer.mean(), scale=1000)
        qual_res = reduce_regions(is_valid_masked, units, ee.Reducer.mean(), scale=1000)

        out = {}
        for unit in units:
            val = lst_res.get(unit.id, {}).get("mean")
            qual = qual_res.get(unit.id, {}).get("mean")

            if val is None:
                val = 0.0
            if qual is None:
                qual = 0.0

            out[unit.id] = MeasuredValue(value=float(val), quality=float(qual))

        return out
