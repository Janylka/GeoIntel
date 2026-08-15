from sqlalchemy import func, select
from sqlalchemy.orm import Session

from geointel.db.models.customer import Field
from geointel.db.models.metrics import AdminUnit


class RegistrationError(Exception):
    pass


def register_field(
    db: Session, customer_id: int, name: str, geojson: str, crop: str | None = None
) -> Field:
    """
    Validates a field geometry and inserts it into the database.
    Calculates area_ha, center, radius_m and finds the district_id.
    """
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

    center_geom = db.execute(select(func.ST_Centroid(geom_ewkt))).scalar()

    # Approximate radius as the max distance from center to any point in the polygon
    radius_m = db.execute(
        select(func.ST_MaxDistance(func.ST_GeographyFromText(func.ST_AsText(center_geom)), geog))
    ).scalar()

    new_field = Field(
        customer_id=customer_id,
        name=name,
        crop=crop,
        area_ha=area_ha,
        geom=func.ST_GeomFromEWKT(func.ST_AsEWKT(geom_ewkt)),
        center=func.ST_GeomFromEWKT(func.ST_AsEWKT(center_geom)),
        radius_m=radius_m,
        district_id=district.id,
    )
    db.add(new_field)
    db.commit()
    db.refresh(new_field)
    return new_field
