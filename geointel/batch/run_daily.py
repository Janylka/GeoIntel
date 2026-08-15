import argparse
import logging
from datetime import date
from typing import Any

from sqlalchemy import Connection, MetaData, Table, create_engine, text
from sqlalchemy.dialects.postgresql import insert

from geointel.db.session import DATABASE_URL
from geointel.domain.decade import decade_start
from geointel.domain.indices import compute_tci, compute_vci, compute_vhi
from geointel.providers.gee import initialize
from geointel.providers.vegetation.modis import ModisLstProvider, ModisNdviProvider
from geointel.scripts.ingest_cropland_mask import get_districts

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def get_historical_extremes(conn: Connection, unit_id: int, metric_id: str, target_decade: date) -> tuple[float | None, float | None]:
    """
    Fetches the historical min and max for a specific metric and admin unit,
    matching the same month and day (decade) across all years.
    """
    query = text("""
        SELECT MIN(value), MAX(value)
        FROM metric_value
        WHERE unit_id = :unit_id
          AND metric_id = :metric_id
          AND EXTRACT(MONTH FROM decade_start) = :month
          AND EXTRACT(DAY FROM decade_start) = :day
    """)
    result = conn.execute(
        query,
        {
            "unit_id": unit_id,
            "metric_id": metric_id,
            "month": target_decade.month,
            "day": target_decade.day,
        },
    ).fetchone()

    if result and result[0] is not None and result[1] is not None:
        return float(result[0]), float(result[1])
    return None, None


def upsert_metrics(conn: Connection, metric_value_table: Table, records: list[dict[str, Any]]) -> None:
    if not records:
        return
    stmt = insert(metric_value_table).values(records)
    upsert_stmt = stmt.on_conflict_do_update(
        index_elements=["unit_id", "metric_id", "decade_start"],
        set_={
            "value": stmt.excluded.value,
            "quality": stmt.excluded.quality,
            "computed_at": text("now()"),
        },
    )
    conn.execute(upsert_stmt)
    conn.commit()


def run_batch(target_date: date) -> None:
    logger.info(f"Starting batch for date: {target_date}")
    if not DATABASE_URL:
        raise ValueError("DATABASE_URL is not set")
    engine = create_engine(DATABASE_URL)
    meta = MetaData()

    with engine.connect() as conn:
        metric_value_table = Table("metric_value", meta, autoload_with=conn)

        # 1. Determine target decade
        d_start = decade_start(target_date)

        # 2. Get districts
        units, _, _ = get_districts(conn)
        logger.info(f"Loaded {len(units)} districts.")

        # 3. Fetch remote sensing data
        initialize()
        ndvi_provider = ModisNdviProvider()
        lst_provider = ModisLstProvider()

        logger.info("Fetching MODIS NDVI...")
        ndvi_results = ndvi_provider.fetch(units, d_start, d_start)

        logger.info("Fetching MODIS LST...")
        lst_results = lst_provider.fetch(units, d_start, d_start)

        # 4. Save raw metrics and compute indices
        raw_records: list[dict[str, Any]] = []
        derived_records: list[dict[str, Any]] = []

        for unit in units:
            ndvi_res = ndvi_results.get(unit.id)
            lst_res = lst_results.get(unit.id)

            if ndvi_res:
                raw_records.append({
                    "unit_id": unit.id,
                    "metric_id": "ndvi_hist",
                    "decade_start": d_start,
                    "value": ndvi_res.value,
                    "quality": ndvi_res.quality,
                })

            if lst_res:
                raw_records.append({
                    "unit_id": unit.id,
                    "metric_id": "lst",
                    "decade_start": d_start,
                    "value": lst_res.value,
                    "quality": lst_res.quality,
                })

            # If we don't have both, we can't compute VHI
            if not ndvi_res or not lst_res:
                logger.warning(f"Missing NDVI or LST for unit {unit.id}, skipping indices.")
                continue

            # Fetch extremes
            ndvi_min, ndvi_max = get_historical_extremes(conn, unit.id, "ndvi_hist", d_start)
            lst_min, lst_max = get_historical_extremes(conn, unit.id, "lst", d_start)

            # If no history, use current as min/max (will result in 50.0)
            if ndvi_min is None or ndvi_max is None:
                ndvi_min = ndvi_max = ndvi_res.value
            if lst_min is None or lst_max is None:
                lst_min = lst_max = lst_res.value

            vci = compute_vci(ndvi_res.value, ndvi_min, ndvi_max)
            tci = compute_tci(lst_res.value, lst_min, lst_max)
            vhi = compute_vhi(vci, tci)

            # Use the minimum quality of the two inputs
            quality = min(ndvi_res.quality, lst_res.quality)

            for metric_id, val in [("vci", vci), ("tci", tci), ("vhi", vhi)]:
                derived_records.append({
                    "unit_id": unit.id,
                    "metric_id": metric_id,
                    "decade_start": d_start,
                    "value": val,
                    "quality": quality,
                })

        # 5. Upsert raw records
        logger.info(f"Upserting {len(raw_records)} raw metric records.")
        upsert_metrics(conn, metric_value_table, raw_records)

        # 6. Upsert derived records
        logger.info(f"Upserting {len(derived_records)} derived index records.")
        upsert_metrics(conn, metric_value_table, derived_records)

        logger.info("Batch completed successfully.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run daily batch to fetch data and compute indices.")
    parser.add_argument("--date", type=str, help="Target date (YYYY-MM-DD). Defaults to today.")
    args = parser.parse_args()

    target = date.fromisoformat(args.date) if args.date else date.today()
    run_batch(target)
