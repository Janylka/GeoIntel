import json
import os
from typing import Any

import ee
from google.oauth2 import service_account

_INITIALIZED = False


def initialize() -> None:
    global _INITIALIZED
    if _INITIALIZED:
        return

    creds_json = os.environ.get("GEE_SERVICE_ACCOUNT_JSON")
    project_id = os.environ.get("GEE_PROJECT")

    if not creds_json or not project_id:
        raise ValueError("GEE_SERVICE_ACCOUNT_JSON and GEE_PROJECT must be set")

    creds_info = json.loads(creds_json)
    credentials = service_account.Credentials.from_service_account_info(
        creds_info, scopes=["https://www.googleapis.com/auth/earthengine"]
    )  # type: ignore[no-untyped-call]

    ee.Initialize(credentials=credentials, project=project_id)
    _INITIALIZED = True


def get_cropland_mask() -> ee.Image:
    """Returns a binary mask of ESA WorldCover 2021 cropland (class 40).
    Non-cropland pixels are masked out via selfMask().
    """
    initialize()
    esa = ee.ImageCollection("ESA/WorldCover/v200").first()
    return esa.eq(40).selfMask()  # type: ignore[no-any-return]


def reduce_regions(
    image: ee.Image,
    units: list[Any],  # list[AdminUnitRef]
    reducer: ee.Reducer,
    scale: int,
) -> dict[int, dict[str, float]]:
    """Helper to reduce an image over a list of AdminUnitRef geometries."""
    initialize()

    features = []
    for unit in units:
        geom = ee.Geometry(unit.geom)
        features.append(ee.Feature(geom, {"id": unit.id}))

    fc = ee.FeatureCollection(features)
    reduced = image.reduceRegions(collection=fc, reducer=reducer, scale=scale)
    info: dict[str, Any] = reduced.getInfo() or {}
    features_out = info.get("features", [])

    out = {}
    for feat in features_out:
        props = feat.get("properties", {})
        unit_id = props.get("id")
        if unit_id is not None:
            out[unit_id] = props

    return out
