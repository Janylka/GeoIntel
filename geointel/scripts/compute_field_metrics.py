"""Computes per-field NDVI (the `ndvi` contract metric, min_scope=FIELD).

Registering a field only ever stored geometry/crop/area -- nothing computed
an index for the field's own polygon. The daily batch (batch/run_daily.py)
only ever touches admin_unit-level geometry, never field. This script closes
that gap using the same Sentinel2Provider the district pipeline already
relies on, since RasterProvider.fetch() only needs objects with .id/.geom
and doesn't care whether they're districts or fields.

Requires Earth Engine access (GEE_SERVICE_ACCOUNT_JSON / GEE_PROJECT), same
as everything else under providers/.

Usage:
    uv run python -m geointel.scripts.compute_field_metrics
    uv run python -m geointel.scripts.compute_field_metrics --date 2026-08-01
"""

import argparse
import json
import logging
from datetime import date

from sqlalchemy import MetaData, Table, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.engine import Connection

from geointel.db.session import engine
from geointel.domain.decade import decade_start
from geointel.providers.base import AdminUnitRef
from geointel.providers.vegetation.sentinel2 import Sentinel2Provider

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def get_fields(conn: Connection) -> list[AdminUnitRef]:
    """Fetches every registered field as an AdminUnitRef (id + GeoJSON geometry)."""
    rows = conn.execute(text("SELECT id, ST_AsGeoJSON(geom) AS geom_json FROM field")).fetchall()
    return [AdminUnitRef(id=row.id, geom=json.loads(row.geom_json)) for row in rows]


def run(target_date: date) -> None:
    d_start = decade_start(target_date)
    logger.info("Computing field NDVI for decade %s", d_start)

    with engine.connect() as conn:
        meta = MetaData()
        field_metric_table = Table("field_metric", meta, autoload_with=conn)
        agent_event_table = Table("agent_event", meta, autoload_with=conn)

        fields = get_fields(conn)
        logger.info("Loaded %s fields.", len(fields))
        if not fields:
            logger.info("No fields registered yet, nothing to compute.")
            return

        provider = Sentinel2Provider()
        results = provider.fetch(fields, d_start, d_start)

        records = [
            {"field_id": field_id, "metric_id": "ndvi", "decade_start": d_start, "value": res.value}
            for field_id, res in results.items()
        ]

        if records:
            stmt = insert(field_metric_table).values(records)
            upsert_stmt = stmt.on_conflict_do_update(
                index_elements=["field_id", "metric_id", "decade_start"],
                set_={"value": stmt.excluded.value},
            )
            conn.execute(upsert_stmt)

        conn.execute(
            insert(agent_event_table).values(
                agent="monitor",
                action="compute_field_ndvi",
                subject=str(d_start),
                payload_json={
                    "decade_start": d_start.isoformat(),
                    "fields_processed": len(fields),
                    "fields_with_data": len(records),
                },
                status="ok",
            )
        )
        conn.commit()

    logger.info("Upserted NDVI for %s/%s fields.", len(records), len(fields))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Compute per-field NDVI via Sentinel-2.")
    parser.add_argument("--date", type=str, help="Target date (YYYY-MM-DD). Defaults to today.")
    args = parser.parse_args()

    target = date.fromisoformat(args.date) if args.date else date.today()
    run(target)
