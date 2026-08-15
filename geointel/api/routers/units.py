from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from geointel.api.errors import validate_metric_scope
from geointel.contracts.scope import Scope
from geointel.db.models.metrics import AdminUnit, MetricValue
from geointel.db.session import get_db

router = APIRouter()


@router.get("/{unit_id}/series")
def get_unit_series(
    unit_id: int,
    metric: str = Query(..., description="ID метрики (например, vci, spi3)"),
    db: Session = Depends(get_db),
):
    unit = db.query(AdminUnit).filter(AdminUnit.id == unit_id).first()
    if not unit:
        raise HTTPException(status_code=404, detail="Admin unit not found")

    unit_scope = Scope(unit.level.lower())

    # Валидация ограничения min_scope
    validate_metric_scope(metric, unit_scope)

    series = (
        db.query(MetricValue)
        .filter(MetricValue.unit_id == unit_id, MetricValue.metric_id == metric)
        .order_by(MetricValue.decade_start.asc())
        .all()
    )

    return {
        "unit_id": unit_id,
        "metric_id": metric,
        "series": [
            {
                "decade_start": item.decade_start,
                "value": item.value,
                "quality": item.quality,
            }
            for item in series
        ],
    }