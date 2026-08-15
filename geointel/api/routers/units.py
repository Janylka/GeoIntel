from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from geointel.contracts.metrics import assert_scope_allowed
from geointel.contracts.scope import Scope
from geointel.db.repositories.metrics import get_unit_metrics
from geointel.db.repositories.units import get_districts, get_oblasts, get_unit_by_id
from geointel.db.session import get_db

router = APIRouter()


@router.get("/")
def get_admin_units(db: Session = Depends(get_db)) -> Any:
    oblasts = get_oblasts(db)
    result = []
    for oblast in oblasts:
        districts = get_districts(db, oblast.id)
        result.append(
            {
                "id": oblast.id,
                "name_ru": oblast.name_ru,
                "name_ky": oblast.name_ky,
                "name_en": oblast.name_en,
                "level": oblast.level,
                "districts": [
                    {
                        "id": d.id,
                        "name_ru": d.name_ru,
                        "name_ky": d.name_ky,
                        "name_en": d.name_en,
                        "level": d.level,
                    }
                    for d in districts
                ],
            }
        )
    return result


@router.get("/{unit_id}/series")
def get_unit_series(
    unit_id: int,
    metric: str = Query(..., description="ID метрики (например, vci, spi_3)"),
    start_date: date = Query(date(2000, 1, 1)),
    end_date: date = Query(date.today()),
    db: Session = Depends(get_db),
) -> Any:
    unit = get_unit_by_id(db, unit_id)
    if not unit:
        raise HTTPException(status_code=404, detail="Admin unit not found")

    unit_scope = Scope(unit.level.lower())
    assert_scope_allowed(metric, unit_scope)

    series = get_unit_metrics(db, unit_id, metric, start_date, end_date)

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
