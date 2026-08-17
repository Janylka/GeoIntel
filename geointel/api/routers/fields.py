from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from geointel.api.deps import get_current_user
from geointel.contracts.metrics import assert_scope_allowed
from geointel.contracts.scope import Scope
from geointel.db.models.customer import Customer, Field
from geointel.db.models.metrics import FieldMetric
from geointel.db.models.ops import AgentEvent
from geointel.db.session import get_db
from geointel.services.registration import RegistrationError, register_field

router = APIRouter()


@router.get("/")
def list_fields(
    current_user: Customer = Depends(get_current_user), db: Session = Depends(get_db)
) -> Any:
    fields = db.scalars(
        select(Field).where(Field.customer_id == current_user.id).order_by(Field.created_at.desc())
    ).all()
    return [
        {
            "field_id": f.id,
            "name": f.name,
            "crop": f.crop,
            "sowing_date": f.sowing_date,
            "area_ha": f.area_ha,
            "cropland_ha": f.cropland_ha,
            "district_id": f.district_id,
            "created_at": f.created_at,
        }
        for f in fields
    ]


@router.get("/{field_id}/series")
def get_field_series(
    field_id: int,
    metric: str = Query(..., description="ID метрики (сейчас доступен только ndvi)"),
    start_date: date = Query(date(2000, 1, 1)),
    end_date: date = Query(date.today()),
    current_user: Customer = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    field = db.get(Field, field_id)
    if not field or field.customer_id != current_user.id:
        raise HTTPException(status_code=404, detail="Field not found")

    assert_scope_allowed(metric, Scope.FIELD)

    rows = db.scalars(
        select(FieldMetric)
        .where(
            FieldMetric.field_id == field_id,
            FieldMetric.metric_id == metric,
            FieldMetric.decade_start >= start_date,
            FieldMetric.decade_start <= end_date,
        )
        .order_by(FieldMetric.decade_start.asc())
    ).all()

    return {
        "field_id": field_id,
        "metric_id": metric,
        "series": [{"decade_start": r.decade_start, "value": r.value} for r in rows],
    }


class FieldRegisterRequest(BaseModel):
    name: str
    geojson: str
    # Crop and sowing date are asked before any analysis: they drive growth-stage
    # thresholds and water demand (see PROMPT-BACKEND.md B5).
    crop: str
    sowing_date: date


@router.post("/register")
def create_field(
    request: FieldRegisterRequest,
    current_user: Customer = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    try:
        field, low_cropland_fraction = register_field(
            db,
            current_user.id,
            current_user.plan,
            request.name,
            request.geojson,
            request.crop,
            request.sowing_date,
        )

        db.add(
            AgentEvent(
                agent="concierge",
                action="field_registered",
                subject=str(field.id),
                payload_json={
                    "input": {
                        "customer_id": current_user.id,
                        "name": request.name,
                        "crop": request.crop,
                        "sowing_date": request.sowing_date.isoformat(),
                    },
                    "output": {
                        "field_id": field.id,
                        "area_ha": field.area_ha,
                        "cropland_ha": field.cropland_ha,
                        "district_id": field.district_id,
                        "low_cropland_fraction": low_cropland_fraction,
                    },
                },
                status="ok",
            )
        )
        db.commit()

        return {
            "status": "ok",
            "field_id": field.id,
            "area_ha": field.area_ha,
            "cropland_ha": field.cropland_ha,
            "district_id": field.district_id,
            "low_cropland_fraction": low_cropland_fraction,
            "hint": (
                "Less than 20% of the drawn shape overlaps cropland. "
                "Try redrawing the boundary tighter around the actual field."
                if low_cropland_fraction
                else None
            ),
        }
    except RegistrationError as e:
        raise HTTPException(status_code=400, detail=str(e))
