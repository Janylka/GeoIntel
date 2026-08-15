from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from geointel.db.models.ops import Alert
from geointel.db.session import get_db

router = APIRouter()


@router.get("/")
def get_alerts(db: Session = Depends(get_db)) -> Any:
    stmt = select(Alert).order_by(Alert.created_at.desc())
    alerts = db.scalars(stmt).all()
    return alerts


@router.put("/{alert_id}/dismiss")
def dismiss_alert(alert_id: int, db: Session = Depends(get_db)) -> Any:
    alert = db.get(Alert, alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    alert.state = "dismissed"
    db.commit()
    return {"status": "ok", "alert_id": alert_id}
