from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from geointel.api.deps import get_current_user
from geointel.db.models.customer import Customer
from geointel.db.session import get_db
from geointel.services.registration import RegistrationError, register_field

router = APIRouter()


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
