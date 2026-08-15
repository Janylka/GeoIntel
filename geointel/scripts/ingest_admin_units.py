# ruff: noqa: E501
from sqlalchemy import text
from sqlalchemy.orm import Session

from geointel.db.session import SessionLocal


def main() -> None:
    """
    Seeds the database with administrative units for Kyrgyzstan (oblasts and districts).
    This script is idempotent and will not insert data if units already exist.
    """
    db: Session = SessionLocal()
    print("Starting to ingest administrative units...")

    try:
        count = db.execute(text("SELECT count(*) FROM admin_unit")).scalar()
        if count and count > 0:
            print(f"Found {count} units. Skipping ingestion as data already exists.")
            return

        db.commit()  # End implicit transaction from the select

        with db.begin():
            # Insert Oblasts (ADM1)
            oblasts_res = db.execute(
                text(
                    """
                INSERT INTO admin_unit (level, name_ru, name_ky, name_en, geom) VALUES
                ('oblast', 'Баткенская область', 'Баткен облусу', 'Batken Region', ST_GeomFromText('MULTIPOLYGON EMPTY', 4326)),
                ('oblast', 'Чуйская область', 'Чүй облусу', 'Chuy Region', ST_GeomFromText('MULTIPOLYGON EMPTY', 4326)),
                ('oblast', 'Джалал-Абадская область', 'Жалал-Абад облусу', 'Jalal-Abad Region', ST_GeomFromText('MULTIPOLYGON EMPTY', 4326)),
                ('oblast', 'Нарынская область', 'Нарын облусу', 'Naryn Region', ST_GeomFromText('MULTIPOLYGON EMPTY', 4326)),
                ('oblast', 'Ошская область', 'Ош облусу', 'Osh Region', ST_GeomFromText('MULTIPOLYGON EMPTY', 4326)),
                ('oblast', 'Таласская область', 'Талас облусу', 'Talas Region', ST_GeomFromText('MULTIPOLYGON EMPTY', 4326)),
                ('oblast', 'Иссык-Кульская область', 'Ысык-Көл облусу', 'Issyk-Kul Region', ST_GeomFromText('MULTIPOLYGON EMPTY', 4326)),
                ('oblast', 'Город Бишкек', 'Бишкек шаары', 'Bishkek City', ST_GeomFromText('MULTIPOLYGON EMPTY', 4326)),
                ('oblast', 'Город Ош', 'Ош шаары', 'Osh City', ST_GeomFromText('MULTIPOLYGON EMPTY', 4326))
                RETURNING id, name_ru
                """
                )
            ).fetchall()

            oblasts = {name: id for id, name in oblasts_res}
            print(f"Inserted {len(oblasts)} oblasts.")

            # Insert a few Districts (ADM2) for development purposes
            districts = [
                {
                    "p": "Баткенская область",
                    "n_ru": "Баткенский район",
                    "n_ky": "Баткен району",
                    "n_en": "Batken District",
                },
                {
                    "p": "Чуйская область",
                    "n_ru": "Аламудунский район",
                    "n_ky": "Аламүдүн району",
                    "n_en": "Alamudun District",
                },
                {
                    "p": "Джалал-Абадская область",
                    "n_ru": "Сузакский район",
                    "n_ky": "Сузак району",
                    "n_en": "Suzak District",
                },
                {
                    "p": "Нарынская область",
                    "n_ru": "Ат-Башинский район",
                    "n_ky": "Ат-Башы району",
                    "n_en": "At-Bashi District",
                },
                {
                    "p": "Ошская область",
                    "n_ru": "Кара-Сууский район",
                    "n_ky": "Кара-Суу району",
                    "n_en": "Kara-Suu District",
                },
                {
                    "p": "Таласская область",
                    "n_ru": "Манасский район",
                    "n_ky": "Манас району",
                    "n_en": "Manas District",
                },
                {
                    "p": "Иссык-Кульская область",
                    "n_ru": "Тюпский район",
                    "n_ky": "Түп району",
                    "n_en": "Tup District",
                },
            ]

            districts_to_insert = [
                {
                    "parent_id": oblasts[d["p"]],
                    "name_ru": d["n_ru"],
                    "name_ky": d["n_ky"],
                    "name_en": d["n_en"],
                }
                for d in districts
                if d["p"] in oblasts
            ]

            if districts_to_insert:
                db.execute(
                    text(
                        """
                    INSERT INTO admin_unit (level, parent_id, name_ru, name_ky, name_en, geom)
                    VALUES ('district', :parent_id, :name_ru, :name_ky, :name_en, ST_GeomFromText('MULTIPOLYGON EMPTY', 4326))
                    """
                    ),
                    districts_to_insert,
                )
                print(f"Inserted {len(districts_to_insert)} districts.")

        print("Finished ingesting administrative units.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
