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
    crop: str | None = None


@router.post("/register")
def create_field(
    request: FieldRegisterRequest,
    current_user: Customer = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    try:
        field = register_field(db, current_user.id, request.name, request.geojson, request.crop)
        return {
            "status": "ok",
            "field_id": field.id,
            "area_ha": field.area_ha,
            "district_id": field.district_id,
        }
    except RegistrationError as e:
        raise HTTPException(status_code=400, detail=str(e))
