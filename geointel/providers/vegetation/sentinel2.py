from datetime import date

import ee

from geointel.providers.base import AdminUnitRef, MeasuredValue
from geointel.providers.gee import get_cropland_mask, reduce_regions


class Sentinel2Provider:
    metric_id = "ndvi"

    def fetch(self, units: list[AdminUnitRef], start: date, end: date) -> dict[int, MeasuredValue]:
        start_str = start.isoformat()
        end_str = end.isoformat()

        col = ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED").filterDate(start_str, end_str)

        def mask_s2_clouds(image: ee.Image) -> ee.Image:
            scl = image.select("SCL")
            # 4: Vegetation, 5: Bare soils, 6: Water, 7: Unclassified, 11: Snow
            mask = scl.eq(4).Or(scl.eq(5)).Or(scl.eq(6)).Or(scl.eq(7)).Or(scl.eq(11))
            return image.updateMask(mask)

        def add_ndvi(image: ee.Image) -> ee.Image:
            # Sentinel-2 NDVI: (B8 - B4) / (B8 + B4)
            ndvi = image.normalizedDifference(["B8", "B4"]).rename("ndvi")
            return image.addBands(ndvi)

        # Apply cloud mask and compute NDVI for all images
        processed_col = col.map(mask_s2_clouds).map(add_ndvi)

        # Median composite for the decade
        ndvi_median = processed_col.select("ndvi").median()

        # Quality: 1 if pixel has at least one cloud-free observation, 0 otherwise
        valid_obs_count = processed_col.select("ndvi").count()
        is_valid = valid_obs_count.gt(0).rename("quality")

        # Restrict to cropland
        cropland_mask = get_cropland_mask()
        ndvi_masked = ndvi_median.updateMask(cropland_mask)
        # For quality, we want to know what fraction of the cropland has data.
        # So we update mask with cropland mask (it makes non-cropland transparent),
        # leaving 0s where there was no cloud-free observation on cropland, and 1s where there was.
        is_valid_masked = is_valid.updateMask(cropland_mask)

        # Combine into one image so we only reduce once?
        # If we combine, Earth Engine will apply the intersection of masks (which is ndvi_masked's mask).
        # We don't want that. We run reduceRegions twice to be safe.

        ndvi_res = reduce_regions(ndvi_masked, units, ee.Reducer.mean(), scale=10)
        qual_res = reduce_regions(is_valid_masked, units, ee.Reducer.mean(), scale=10)

        out = {}
        for unit in units:
            val = ndvi_res.get(unit.id, {}).get("mean")
            qual = qual_res.get(unit.id, {}).get("mean")

            # Handle cases where area has no data at all
            if val is None:
                val = 0.0
            if qual is None:
                qual = 0.0

            out[unit.id] = MeasuredValue(value=float(val), quality=float(qual))

        return out
