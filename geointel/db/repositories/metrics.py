from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from geointel.db.models.metrics import FieldMetric, MetricValue


def get_unit_metrics(
    session: Session, unit_id: int, metric_id: str, start_date: date, end_date: date
) -> list[MetricValue]:
    stmt = (
        select(MetricValue)
        .where(
            MetricValue.unit_id == unit_id,
            MetricValue.metric_id == metric_id,
            MetricValue.decade_start >= start_date,
            MetricValue.decade_start <= end_date,
        )
        .order_by(MetricValue.decade_start)
    )
    return list(session.scalars(stmt))


def get_field_metrics(
    session: Session, field_id: int, metric_id: str, start_date: date, end_date: date
) -> list[FieldMetric]:
    stmt = (
        select(FieldMetric)
        .where(
            FieldMetric.field_id == field_id,
            FieldMetric.metric_id == metric_id,
            FieldMetric.decade_start >= start_date,
            FieldMetric.decade_start <= end_date,
        )
        .order_by(FieldMetric.decade_start)
    )
    return list(session.scalars(stmt))
