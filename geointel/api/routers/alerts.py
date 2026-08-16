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
    return [
        {
            "id": a.id,
            "unit_id": a.unit_id,
            "field_id": a.field_id,
            "metric_id": a.metric_id,
            "decade_start": a.decade_start,
            "severity": a.severity,
            "state": a.state,
            "notified_at": a.notified_at,
            "created_at": a.created_at,
        }
        for a in alerts
    ]


@router.put("/{alert_id}/dismiss")
def dismiss_alert(alert_id: int, db: Session = Depends(get_db)) -> Any:
    alert = db.get(Alert, alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    alert.state = "dismissed"
    db.commit()
    return {"status": "ok", "alert_id": alert_id}
