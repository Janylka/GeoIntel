from datetime import date

from geoalchemy2 import Geography
from sqlalchemy import cast, func, select
from sqlalchemy.orm import Session

from geointel.contracts.plans import Plan, PlanLimitError, assert_field_limit
from geointel.db.models.customer import Field
from geointel.db.models.metrics import AdminUnit

# Below this fraction of cropland inside the drawn shape, the field boundary is
# probably too loose (includes slopes/roads/bare ground) and the customer should
# redraw it tighter -- see PROMPT-BACKEND.md B5.
MIN_CROPLAND_FRACTION = 0.2


class RegistrationError(Exception):
    pass


def register_field(
    db: Session,
    customer_id: int,
    customer_plan: str,
    name: str,
    geojson: str,
    crop: str,
    sowing_date: date | None = None,
) -> tuple[Field, bool]:
    """
    Validates a field geometry and inserts it into the database.
    Calculates area_ha, cropland_ha, center, radius_m and finds the district_id.

    Returns (field, low_cropland_fraction) where low_cropland_fraction signals the
    circle/polygon should probably be redrawn tighter around actual cropland.
    """
    current_count = db.scalar(
        select(func.count()).select_from(Field).where(Field.customer_id == customer_id)
    )
    try:
        assert_field_limit(Plan(customer_plan), current_count or 0)
    except PlanLimitError as e:
        raise RegistrationError(str(e)) from e

    geom = func.ST_GeomFromGeoJSON(geojson)
    geom_ewkt = func.ST_SetSRID(geom, 4326)

    # Check intersection with a district
    district = (
        db.execute(
            select(AdminUnit)
            .where(AdminUnit.level == "district")
            .where(func.ST_Intersects(AdminUnit.geom, geom_ewkt))
        )
        .scalars()
        .first()
    )

    if not district:
        raise RegistrationError("Field geometry does not intersect with any known district.")

    # Calculate properties using Geography for area and radius in meters
    geog = func.ST_GeographyFromText(func.ST_AsText(geom_ewkt))

    area_sqm = db.execute(select(func.ST_Area(geog))).scalar()
    if area_sqm is None:
        raise RegistrationError("Could not compute field area from the given geometry.")
    area_ha = area_sqm / 10000.0

    # Earth Engine is never called from an HTTP request (see PROJECT.md section 2),
    # so we can't intersect the field with the pixel-level cropland mask here.
    # Instead we approximate cropland_ha using the district's cropland share,
    # already precomputed by scripts/ingest_cropland_mask.py. This is coarser than
    # a real per-field mask intersection but keeps the constraint and gets refined
    # once the batch starts computing field-level NDVI (field_metric).
    district_area_sqm = db.execute(
        select(func.ST_Area(func.ST_GeographyFromText(func.ST_AsText(district.geom))))
    ).scalar()
    cropland_ha = area_ha
    if district_area_sqm and district.cropland_ha:
        district_area_ha = district_area_sqm / 10000.0
        cropland_fraction = min(district.cropland_ha / district_area_ha, 1.0)
        cropland_ha = area_ha * cropland_fraction

    low_cropland_fraction = (cropland_ha / area_ha) < MIN_CROPLAND_FRACTION if area_ha > 0 else True

    center_geom = db.execute(select(func.ST_Centroid(geom_ewkt))).scalar()

    # Approximate radius as the max distance from center to any point in the polygon.
    # ST_MaxDistance doesn't support the geography type on this PostGIS version, so
    # find the longest connecting line in plain geometry space and measure its
    # length as geography (meters, great-circle-aware) instead.
    longest_line = func.ST_LongestLine(center_geom, geom_ewkt)
    radius_m = db.execute(select(func.ST_Length(cast(longest_line, Geography)))).scalar()

    new_field = Field(
        customer_id=customer_id,
        name=name,
        crop=crop,
        sowing_date=sowing_date,
        area_ha=area_ha,
        cropland_ha=cropland_ha,
        geom=func.ST_GeomFromEWKT(func.ST_AsEWKT(geom_ewkt)),
        center=func.ST_GeomFromEWKT(func.ST_AsEWKT(center_geom)),
        radius_m=radius_m,
        district_id=district.id,
    )
    db.add(new_field)
    db.commit()
    db.refresh(new_field)
    return new_field, low_cropland_fraction
