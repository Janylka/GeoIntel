import os
import random
from datetime import date, datetime
from typing import Any

from dotenv import load_dotenv
from sqlalchemy import MetaData, Table
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.engine import Connection

from geointel.contracts.metrics import METRICS
from geointel.db.session import engine
from geointel.domain.decade import decade_start, previous_decade

# Load environment variables from .env file
load_dotenv()


def check_env() -> None:
    """Ensure script is not run in production."""
    app_env = os.getenv("APP_ENV", "production")
    if app_env != "local":
        print(
            f"Error: This script is for local development only (APP_ENV=local). "
            f"Current APP_ENV is '{app_env}'."
        )
        exit(1)


def get_admin_units(conn: Connection) -> list[dict[str, Any]]:
    """Fetches districts and their parent oblasts from the database."""
    meta = MetaData()
    # Reflect the table from the database
    admin_unit_table = Table("admin_unit", meta, autoload_with=conn)

    oblasts_query = admin_unit_table.select().where(admin_unit_table.c.level == "oblast")
    oblasts_result = conn.execute(oblasts_query).fetchall()
    # The result is a list of Row objects. Access columns by name.
    oblasts = {row.id: row.name_ru for row in oblasts_result}

    districts_query = admin_unit_table.select().where(admin_unit_table.c.level == "district")
    districts_result = conn.execute(districts_query).fetchall()

    district_data = []
    for district in districts_result:
        oblast_name = oblasts.get(district.parent_id, "Unknown")
        district_data.append({"id": district.id, "name": district.name_ru, "oblast": oblast_name})
    return district_data


def generate_plausible_metrics(oblast_name: str) -> dict[str, float]:
    """Generates a dictionary of metric values based on region."""
    # Per A0: Юг (Баткен, Ош) — низкие VHI (18-35), север (Чуй, Иссык-Куль) — высокие (50-65).
    southern_oblasts = ["Баткенская область", "Ошская область", "Джалал-Абадская область"]
    northern_oblasts = ["Чуйская область", "Иссык-Кульская область", "Таласская область"]

    if oblast_name in southern_oblasts:
        vhi = random.uniform(18, 35)
    elif oblast_name in northern_oblasts:
        vhi = random.uniform(50, 65)
    else:  # Naryn, or cities like Bishkek/Osh
        vhi = random.uniform(35, 50)

    # Generate other metrics to have a complete dataset for development
    return {
        "vhi": vhi,
        "vci": max(0, vhi + random.uniform(-5, 5)),
        "tci": max(0, vhi + random.uniform(-5, 5)),
        "ndvi": random.uniform(0.2, 0.75),
        "ndvi_hist": random.uniform(0.2, 0.75),
        "lst": random.uniform(15, 38),  # Summer temperatures
        "spi_1": random.uniform(-1.5, 1.5),
        "spi_3": random.uniform(-2.0, 2.0),
        "soil_moisture": random.uniform(0.1, 0.4),
    }


def main() -> None:
    """Main script function to seed the database with development data."""
    check_env()
    print("Starting to seed development metrics for the last 12 decades...")

    meta = MetaData()
    metric_value_table = Table("metric_value", meta, autoload_with=engine)

    with engine.connect() as conn:
        districts = get_admin_units(conn)
        if not districts:
            print("No districts found. Please run 'make seed' to ingest admin units first.")
            return

        print(f"Found {len(districts)} districts. Generating data...")

        decades = [decade_start(date.today())]
        for _ in range(11):
            decades.append(previous_decade(decades[-1]))

        values_to_insert = []
        for d in decades:
            for district in districts:
                metrics = generate_plausible_metrics(district["oblast"])
                for metric_id, value in metrics.items():
                    if metric_id in METRICS:
                        values_to_insert.append(
                            {
                                "unit_id": district["id"],
                                "metric_id": metric_id,
                                "decade_start": d,
                                "value": round(value, METRICS[metric_id].decimals),
                                "quality": random.uniform(0.85, 1.0),
                                "computed_at": datetime.utcnow(),
                            }
                        )

        if not values_to_insert:
            print("No values to insert.")
            return

        # Use on_conflict_do_update for idempotency (upsert)
        stmt = insert(metric_value_table).values(values_to_insert)
        update_dict = {
            "value": stmt.excluded.value,
            "quality": stmt.excluded.quality,
            "computed_at": stmt.excluded.computed_at,
        }
        stmt = stmt.on_conflict_do_update(
            index_elements=["unit_id", "metric_id", "decade_start"], set_=update_dict
        )

        conn.execute(stmt)
        conn.commit()

        print(
            f"Successfully seeded/updated {len(values_to_insert)} metric values "
            f"for {len(districts)} districts across {len(decades)} decades."
        )


if __name__ == "__main__":
    main()
