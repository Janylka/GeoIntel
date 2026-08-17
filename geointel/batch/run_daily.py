import argparse
import logging
from datetime import date
from typing import Any

from sqlalchemy import Connection, MetaData, Table, create_engine, text
from sqlalchemy.dialects.postgresql import insert

from geointel.db.session import DATABASE_URL
from geointel.domain.decade import decade_start, next_decade
from geointel.domain.indices import compute_spi, compute_tci, compute_vci, compute_vhi
from geointel.providers.gee import initialize
from geointel.providers.precipitation.chirps import ChirpsProvider
from geointel.providers.soil.era5_land import Era5LandProvider
from geointel.providers.soil.smap import SmapProvider
from geointel.providers.soil.soilgrids import SoilGridsProvider
from geointel.providers.vegetation.modis import ModisLstProvider, ModisNdviProvider
from geointel.providers.weather.openmeteo import OpenMeteoProvider
from geointel.scripts.ingest_cropland_mask import get_districts

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def get_historical_extremes(
    conn: Connection, unit_id: int, metric_id: str, target_decade: date
) -> tuple[float | None, float | None]:
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


def get_historical_stats(
    conn: Connection, unit_id: int, metric_id: str, target_decade: date
) -> tuple[float | None, float | None]:
    """
    Fetches the historical mean and stddev for a specific metric and admin unit.
    """
    query = text("""
        SELECT AVG(value), STDDEV(value)
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


def upsert_metrics(
    conn: Connection, metric_value_table: Table, records: list[dict[str, Any]]
) -> None:
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
        # GEE's filterDate() is a half-open [start, end) interval -- passing the
        # same date twice produces a zero-width range, which GEE rejects outright
        # ("Empty date ranges not supported"). The upper bound has to be the start
        # of the *next* decade to cover the full 10-day (or shorter, month-end)
        # window a decade actually spans.
        d_end = next_decade(d_start)

        # 2. Get districts
        units, _, _ = get_districts(conn)
        logger.info(f"Loaded {len(units)} districts.")

        # 3. Fetch remote sensing data
        initialize()
        ndvi_provider = ModisNdviProvider()
        lst_provider = ModisLstProvider()
        chirps_provider = ChirpsProvider()
        smap_provider = SmapProvider()
        era5_provider = Era5LandProvider()
        soilgrids_provider = SoilGridsProvider()
        openmeteo_provider = OpenMeteoProvider()

        logger.info("Fetching MODIS NDVI...")
        ndvi_results = ndvi_provider.fetch(units, d_start, d_end)

        logger.info("Fetching MODIS LST...")
        lst_results = lst_provider.fetch(units, d_start, d_end)

        logger.info("Fetching CHIRPS Precipitation...")
        precip_results = chirps_provider.fetch(units, d_start, d_end)

        logger.info("Fetching SMAP Soil Moisture...")
        smap_results = smap_provider.fetch(units, d_start, d_end)

        logger.info("Fetching ERA5-Land ET0...")
        era5_results = era5_provider.fetch(units, d_start, d_end)

        logger.info("Fetching SoilGrids OCD...")
        sg_results = soilgrids_provider.fetch(units, d_start, d_end)

        logger.info("Fetching OpenMeteo Weather...")
        weather_results = openmeteo_provider.fetch(units, d_start, d_end)

        # 4. Save raw metrics and compute indices
        raw_records: list[dict[str, Any]] = []
        derived_records: list[dict[str, Any]] = []

        for unit in units:
            ndvi_res = ndvi_results.get(unit.id)
            lst_res = lst_results.get(unit.id)
            precip_res = precip_results.get(unit.id)
            smap_res = smap_results.get(unit.id)
            era5_res = era5_results.get(unit.id)
            sg_res = sg_results.get(unit.id)
            weather_res = weather_results.get(unit.id)

            def add_raw(metric_id: str, res: Any) -> None:
                if res:
                    raw_records.append(
                        {
                            "unit_id": unit.id,
                            "metric_id": metric_id,
                            "decade_start": d_start,
                            "value": res.value,
                            "quality": res.quality,
                        }
                    )

            add_raw("ndvi_hist", ndvi_res)
            add_raw("lst", lst_res)
            add_raw("precipitation", precip_res)
            # metric_id values below must match contracts/metrics.py exactly --
            # the API and frontend query by these names, and the contract is
            # frozen (AGENTS.md), so this file has to match it, not the other
            # way around.
            add_raw("soil_moisture", smap_res)
            add_raw("et0_era5", era5_res)
            add_raw("soilgrids_ocd", sg_res)
            add_raw("weather", weather_res)

            # Compute VHI
            if ndvi_res and lst_res:
                ndvi_min, ndvi_max = get_historical_extremes(conn, unit.id, "ndvi_hist", d_start)
                lst_min, lst_max = get_historical_extremes(conn, unit.id, "lst", d_start)

                if ndvi_min is None or ndvi_max is None:
                    ndvi_min = ndvi_max = ndvi_res.value
                if lst_min is None or lst_max is None:
                    lst_min = lst_max = lst_res.value

                vci = compute_vci(ndvi_res.value, ndvi_min, ndvi_max)
                tci = compute_tci(lst_res.value, lst_min, lst_max)
                vhi = compute_vhi(vci, tci)
                quality = min(ndvi_res.quality, lst_res.quality)

                for m_id, val in [("vci", vci), ("tci", tci), ("vhi", vhi)]:
                    derived_records.append(
                        {
                            "unit_id": unit.id,
                            "metric_id": m_id,
                            "decade_start": d_start,
                            "value": val,
                            "quality": quality,
                        }
                    )

            # Compute SPI
            if precip_res:
                p_mean, p_std = get_historical_stats(conn, unit.id, "precipitation", d_start)
                if p_mean is None or p_std is None:
                    # If no history, SPI is 0
                    spi = 0.0
                else:
                    spi = compute_spi(precip_res.value, p_mean, p_std)

                derived_records.append(
                    {
                        "unit_id": unit.id,
                        "metric_id": "spi_1",
                        "decade_start": d_start,
                        "value": spi,
                        "quality": precip_res.quality,
                    }
                )

        # 5. Upsert raw records
        logger.info(f"Upserting {len(raw_records)} raw metric records.")
        upsert_metrics(conn, metric_value_table, raw_records)

        # 6. Upsert derived records
        logger.info(f"Upserting {len(derived_records)} derived index records.")
        upsert_metrics(conn, metric_value_table, derived_records)

        logger.info("Batch completed successfully.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run daily batch to fetch data and compute indices."
    )
    parser.add_argument("--date", type=str, help="Target date (YYYY-MM-DD). Defaults to today.")
    args = parser.parse_args()

    target = date.fromisoformat(args.date) if args.date else date.today()
    run_batch(target)
