# ruff: noqa: E501
"""Loads real administrative boundaries for Kyrgyzstan (oblasts + districts).

The original version of this script inserted `ST_GeomFromText('MULTIPOLYGON EMPTY')`
placeholders for every unit -- fine to unblock early API work, but it means the map,
field-district lookups, and any ST_Intersects/ST_Contains query never had real
geometry to work with. This version loads real boundaries from geoBoundaries
(open data, ODbL license) and backfills geom on the existing rows so IDs already
referenced by seeded metrics/fields are preserved, then inserts the remaining
districts geoBoundaries has that the original dev seed didn't include.

Source: https://www.geoboundaries.org (KGZ ADM1 = oblasts, ADM2 = districts),
snapshot saved at geointel/scripts/data/adm1.geojson and adm2.geojson.

NAME CAVEAT: geoBoundaries only provides English names. The Russian/Kyrgyz names
below are filled in from general knowledge of Kyrgyzstan's administrative-territorial
division, not machine transliteration -- but per PROJECT.md's own warning
("Кыргызские названия проверь глазами"), a native speaker should still confirm the
Kyrgyz spellings before relying on them in a customer-facing product.
"""

import json
from pathlib import Path
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from geointel.db.session import SessionLocal

_DATA_DIR = Path(__file__).parent / "data"

# geoBoundaries shapeName -> (name_ru, name_ky), for the 7 oblasts (ADM1).
OBLASTS: dict[str, tuple[str, str]] = {
    "Batken Region": ("Баткенская область", "Баткен облусу"),
    "Chuy Region": ("Чуйская область", "Чүй облусу"),
    "Jalal-Abad Region": ("Джалал-Абадская область", "Жалал-Абад облусу"),
    "Naryn Region": ("Нарынская область", "Нарын облусу"),
    "Osh Region": ("Ошская область", "Ош облусу"),
    "Talas Region": ("Таласская область", "Талас облусу"),
    "Issyk-Kul Region": ("Иссык-Кульская область", "Ысык-Көл облусу"),
}

# geoBoundaries shapeName -> (name_ru, name_ky), for districts (ADM2).
DISTRICTS: dict[str, tuple[str, str]] = {
    "Batken": ("Баткенский район", "Баткен району"),
    "Kadamjay": ("Кадамжайский район", "Кадамжай району"),
    "Leilek": ("Лейлекский район", "Лейлек району"),
    "Ala-Buka": ("Ала-Букинский район", "Ала-Бука району"),
    "Aksy": ("Аксыйский район", "Аксы району"),
    "Bazar-Korgon": ("Базар-Коргонский район", "Базар-Коргон району"),
    "Nooken": ("Ноокенский район", "Ноокен району"),
    "Suzak": ("Сузакский район", "Сузак району"),
    "Toktogul": ("Токтогульский район", "Токтогул району"),
    "Toguz-Toro": ("Тогуз-Тороский район", "Тогуз-Торо району"),
    "Chatkal": ("Чаткальский район", "Чаткал району"),
    "At-Bashy": ("Ат-Башинский район", "Ат-Башы району"),
    "Ak-Talaa": ("Ак-Талинский район", "Ак-Талаа району"),
    "Jumgal": ("Жумгальский район", "Жумгал району"),
    "Kochkor": ("Кочкорский район", "Кочкор району"),
    "Naryn": ("Нарынский район", "Нарын району"),
    "Alay": ("Алайский район", "Алай району"),
    "Aravan": ("Араванский район", "Араван району"),
    "Chong-Alay": ("Чон-Алайский район", "Чоң-Алай району"),
    "Kara-Kulja": ("Кара-Кульджинский район", "Кара-Кулжа району"),
    "Kara-Suu": ("Кара-Сууский район", "Кара-Суу району"),
    "Nookat": ("Ноокатский район", "Ноокат району"),
    "Uzgen": ("Узгенский район", "Өзгөн району"),
    "Bakay-Ata": ("Бакай-Атинский район", "Бакай-Ата району"),
    "Kara-Buura": ("Кара-Бууринский район", "Кара-Буура району"),
    "Manas": ("Манасский район", "Манас району"),
    "Talas": ("Таласский район", "Талас району"),
    "Alamudun": ("Аламудунский район", "Аламүдүн району"),
    "Chuy": ("Чуйский район", "Чүй району"),
    "Jayyl": ("Жайылский район", "Жайыл району"),
    "Kemin": ("Кеминский район", "Кемин району"),
    "Moskva": ("Московский район", "Москва району"),
    "Panfilov": ("Панфиловский район", "Панфилов району"),
    "Sokuluk": ("Сокулукский район", "Сокулук району"),
    "Ysyk-Ata": ("Ысык-Атинский район", "Ысык-Ата району"),
    "Ak-Suu": ("Ак-Сууский район", "Ак-Суу району"),
    "Jeti-Oguz": ("Жети-Огузский район", "Жети-Огуз району"),
    "Issyk Kul": ("Иссык-Кульский район", "Ысык-Көл району"),
    "Tong": ("Тонский район", "Тон району"),
    "Tup": ("Тюпский район", "Түп району"),
    # geoBoundaries includes this small city-level unit; name unverified, see module docstring.
    "City of Tomok": ("Город Томок", "Томок шаары"),
}

# geoBoundaries doesn't split Bishkek/Osh out as separate ADM1 shapes, so these two
# get an approximate circular boundary around the city center instead of a real
# municipal boundary. Radii are rough (city extents), not survey-grade.
CITY_APPROXIMATIONS = {
    "Город Бишкек": (74.5698, 42.8746, 15000),
    "Город Ош": (72.7985, 40.5283, 8000),
}


def _load_geojson(filename: str) -> dict[str, Any]:
    with open(_DATA_DIR / filename, encoding="utf-8") as f:
        data: dict[str, Any] = json.load(f)
        return data


def _upsert_unit(
    db: Session,
    level: str,
    name_ru: str,
    name_ky: str,
    name_en: str,
    geom_geojson: str | None,
    circle: tuple[float, float, float] | None,
) -> None:
    existing = db.execute(
        text("SELECT id FROM admin_unit WHERE name_ru = :name_ru AND level = :level"),
        {"name_ru": name_ru, "level": level},
    ).first()

    if circle is not None:
        lon, lat, radius_m = circle
        geom_sql = "ST_Multi(ST_Buffer(ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography, :radius)::geometry)"
        params: dict[str, Any] = {"lon": lon, "lat": lat, "radius": radius_m}
    else:
        geom_sql = "ST_Multi(ST_GeomFromGeoJSON(:geom_json))"
        params = {"geom_json": geom_geojson}

    if existing:
        db.execute(
            text(f"UPDATE admin_unit SET geom = {geom_sql}, name_en = :name_en WHERE id = :id"),
            {**params, "name_en": name_en, "id": existing[0]},
        )
    else:
        db.execute(
            text(
                f"""
                INSERT INTO admin_unit (level, name_ru, name_ky, name_en, geom)
                VALUES (:level, :name_ru, :name_ky, :name_en, {geom_sql})
                """
            ),
            {**params, "level": level, "name_ru": name_ru, "name_ky": name_ky, "name_en": name_en},
        )


def main() -> None:
    db: Session = SessionLocal()
    print("Loading real administrative boundaries for Kyrgyzstan...")

    try:
        adm1 = _load_geojson("adm1.geojson")
        adm2 = _load_geojson("adm2.geojson")

        with db.begin():
            for feature in adm1["features"]:
                shape_name = feature["properties"]["shapeName"]
                if shape_name not in OBLASTS:
                    print(f"  Skipping unrecognized ADM1 unit: {shape_name}")
                    continue
                name_ru, name_ky = OBLASTS[shape_name]
                _upsert_unit(
                    db, "oblast", name_ru, name_ky, shape_name, json.dumps(feature["geometry"]), None
                )
            print(f"Upserted {len(OBLASTS)} oblasts with real geometry.")

            for name_ru, (lon, lat, radius_m) in CITY_APPROXIMATIONS.items():
                _upsert_unit(
                    db, "oblast", name_ru, name_ru, name_ru, None, (lon, lat, radius_m)
                )
            print(f"Approximated {len(CITY_APPROXIMATIONS)} independent cities (Bishkek, Osh).")

            district_count = 0
            for feature in adm2["features"]:
                shape_name = feature["properties"]["shapeName"]
                if shape_name not in DISTRICTS:
                    print(f"  Skipping unrecognized ADM2 unit: {shape_name}")
                    continue
                name_ru, name_ky = DISTRICTS[shape_name]
                _upsert_unit(
                    db, "district", name_ru, name_ky, shape_name, json.dumps(feature["geometry"]), None
                )
                district_count += 1
            print(f"Upserted {district_count} districts with real geometry.")

            # Resolve parent_id spatially now that real geometry exists, rather
            # than relying on a hardcoded name mapping.
            db.execute(
                text(
                    """
                    UPDATE admin_unit d
                    SET parent_id = o.id
                    FROM admin_unit o
                    WHERE d.level = 'district'
                      AND o.level = 'oblast'
                      AND ST_Contains(o.geom, ST_PointOnSurface(d.geom))
                    """
                )
            )
            print("Resolved district -> oblast parent_id via spatial containment.")

        print("Finished loading administrative units.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
