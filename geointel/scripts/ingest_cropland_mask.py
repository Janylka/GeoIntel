import json

import ee
from dotenv import load_dotenv
from sqlalchemy import MetaData, Table, text, update
from sqlalchemy.engine import Connection

from geointel.db.session import engine
from geointel.providers.base import AdminUnitRef
from geointel.providers.gee import get_cropland_mask, reduce_regions

load_dotenv()


def check_env() -> None:
    """No-op: this is a data ingestion script, meant to run in any environment."""
    pass


def get_districts(
    conn: Connection,
) -> tuple[list[AdminUnitRef], dict[int, str], dict[int, str]]:
    """Fetches districts, a mapping of id->name, and a mapping of id->oblast_name."""

    # Need geometry as GeoJSON to pass to Earth Engine
    query = text("""
        SELECT a1.id, a1.name_ru, a2.name_ru as oblast_name, ST_AsGeoJSON(a1.geom) as geom_json
        FROM admin_unit a1
        LEFT JOIN admin_unit a2 ON a1.parent_id = a2.id
        WHERE a1.level = 'district'
    """)
    result = conn.execute(query).fetchall()

    units = []
    id_to_name = {}
    id_to_oblast = {}
    for row in result:
        geom_dict = json.loads(row.geom_json)
        units.append(AdminUnitRef(id=row.id, geom=geom_dict))
        id_to_name[row.id] = row.name_ru
        id_to_oblast[row.id] = row.oblast_name

    return units, id_to_name, id_to_oblast


def main() -> None:
    print("Starting cropland mask ingestion...")

    with engine.connect() as conn:
        units, id_to_name, id_to_oblast = get_districts(conn)
        if not units:
            print("No districts found. Run ingest_admin_units.py first.")
            return

        print(f"Found {len(units)} districts. Computing cropland area via GEE...")

        # 1. Get ESA WorldCover mask (1 for cropland, 0/masked otherwise)
        mask = get_cropland_mask()

        # 2. Pixel area in sq meters, masked to only include cropland
        cropland_area_sqm = ee.Image.pixelArea().updateMask(mask)

        # 3. Reduce regions to sum the area. WorldCover is 10m resolution.
        #    We use scale=10.
        results = reduce_regions(
            image=cropland_area_sqm,
            units=units,
            reducer=ee.Reducer.sum(),
            scale=10,
        )

        # 4. Process results and convert to hectares (1 ha = 10,000 sq m)
        updates = []
        oblast_areas: dict[str, float] = {}

        meta = MetaData()
        admin_unit_table = Table("admin_unit", meta, autoload_with=conn)

        for unit in units:
            props = results.get(unit.id, {})
            # ee.Reducer.sum() outputs the key 'sum'
            area_sqm = props.get("sum", 0.0)
            area_ha = area_sqm / 10000.0

            updates.append({"b_id": unit.id, "b_cropland_ha": area_ha})

            oblast = id_to_oblast[unit.id]
            oblast_areas[oblast] = oblast_areas.get(oblast, 0.0) + area_ha

            print(f"District: {id_to_name[unit.id]} -> {area_ha:.2f} ha")

        chuy_ha = oblast_areas.get("Чуйская область", 0.0)
        naryn_ha = oblast_areas.get("Нарынская область", 0.0)

        print(f"\nSanity Check: Chuy Oblast = {chuy_ha:.2f} ha, Naryn Oblast = {naryn_ha:.2f} ha")

        if naryn_ha >= chuy_ha and chuy_ha > 0:
            print("ERROR: Sanity check failed! Naryn has more cropland than Chuy.")
            print("Aborting database update.")
            return

        if updates:
            print("Updating database...")
            stmt = (
                update(admin_unit_table)
                .where(admin_unit_table.c.id == text(":b_id"))
                .values(cropland_ha=text(":b_cropland_ha"))
            )
            conn.execute(stmt, updates)
            conn.commit()
            print("Database updated successfully.")


if __name__ == "__main__":
    main()
