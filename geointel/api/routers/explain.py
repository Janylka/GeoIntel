from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from geointel.db.models.metrics import MetricValue
from geointel.db.session import get_db
from geointel.services.gemini import generate_explanation

router = APIRouter()


class ExplainRequest(BaseModel):
    scope: str
    subject_id: int
    decade: date
    lang: str = "ru"


@router.post("")
async def explain_metrics(req: ExplainRequest, db: Session = Depends(get_db)) -> Any:
    # Собираем метрики из базы данных
    metrics = (
        db.query(MetricValue)
        .filter(MetricValue.unit_id == req.subject_id, MetricValue.decade_start == req.decade)
        .all()
    )

    if not metrics:
        raise HTTPException(
            status_code=404, detail="No metrics found for the specified subject and decade"
        )

    metrics_data = {m.metric_id: m.value for m in metrics}

    explanation = await generate_explanation(
        scope=req.scope,
        subject_id=req.subject_id,
        decade=req.decade.isoformat(),
        lang=req.lang,
        metrics_data=metrics_data,
    )

    return {
        "scope": req.scope,
        "subject_id": req.subject_id,
        "decade": req.decade,
        "explanation": explanation,
    }
