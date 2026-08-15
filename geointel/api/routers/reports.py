import os
from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from geointel.api.deps import get_current_user
from geointel.db.models.customer import Customer
from geointel.db.models.metrics import MetricValue
from geointel.db.models.ops import Report
from geointel.db.session import get_db
from geointel.services.gemini import generate_explanation
from geointel.services.pdf import generate_report_pdf

router = APIRouter()


class ReportRequest(BaseModel):
    scope: str
    subject_id: int
    decade: date
    lang: str = "ru"


@router.post("/generate")
async def generate_report(
    req: ReportRequest,
    current_user: Customer = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    metrics = (
        db.query(MetricValue)
        .filter(
            MetricValue.unit_id == req.subject_id,
            MetricValue.decade_start == req.decade,
        )
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

    output_dir = os.path.join("reports", str(current_user.id))
    output_path = os.path.join(output_dir, f"report_{req.subject_id}_{req.decade}.pdf")

    generate_report_pdf(
        customer_name=current_user.name or current_user.email,
        metrics=metrics_data,
        explanation=explanation,
        output_path=output_path,
    )

    report = Report(
        customer_id=current_user.id,
        scope=req.scope,
        subject_id=req.subject_id,
        decade_start=req.decade,
        storage_path=output_path,
        lang=req.lang,
    )
    db.add(report)
    db.commit()
    db.refresh(report)

    return {
        "report_id": report.id,
        "storage_path": report.storage_path,
        "explanation": explanation,
    }
