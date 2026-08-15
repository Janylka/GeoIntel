"""The `notifier` agent (PROMPT-BACKEND.md B7).

After the daily batch writes alerts, this script emails the affected customers,
marks each alert as notified, and logs every decision to agent_event. Idempotent:
re-running only processes alerts that haven't been notified yet, and decade
summaries are deduplicated against prior agent_event rows for the same
(customer, decade) pair.

Usage:
    uv run python -m geointel.scripts.notify_alerts             # threshold alerts
    uv run python -m geointel.scripts.notify_alerts --decade-summary 2026-08-01
"""

import argparse
import logging
from datetime import date
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from geointel.db.models.customer import Customer, Field
from geointel.db.models.metrics import AdminUnit, MetricValue
from geointel.db.models.ops import AgentEvent, Alert
from geointel.db.session import SessionLocal
from geointel.services.email import send_email
from geointel.services.email_templates import render_decade_summary, render_threshold_breach

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("notifier")


def _log_event(
    db: Session, action: str, subject: str, payload: dict[str, Any], status: str
) -> None:
    db.add(
        AgentEvent(
            agent="notifier",
            action=action,
            subject=subject,
            payload_json=payload,
            status=status,
        )
    )
    db.commit()


def notify_threshold_alerts(db: Session) -> int:
    """Emails customers for every unnotified alert, field-scoped or district-scoped."""
    alerts = db.scalars(
        select(Alert).where(Alert.notified_at.is_(None), Alert.state != "dismissed")
    ).all()

    sent = 0
    for alert in alerts:
        recipients: list[tuple[Customer, str]] = []

        if alert.field_id:
            field = db.get(Field, alert.field_id)
            if field:
                customer = db.get(Customer, field.customer_id)
                if customer:
                    recipients.append((customer, field.name))
        elif alert.unit_id:
            unit = db.get(AdminUnit, alert.unit_id)
            subject_name = unit.name_ru if unit else f"unit #{alert.unit_id}"
            fields_in_district = db.scalars(
                select(Field).where(Field.district_id == alert.unit_id)
            ).all()
            seen_customers = set()
            for field in fields_in_district:
                if field.customer_id in seen_customers:
                    continue
                seen_customers.add(field.customer_id)
                customer = db.get(Customer, field.customer_id)
                if customer:
                    recipients.append((customer, subject_name))

        for customer, subject_name in recipients:
            try:
                subject, body = render_threshold_breach(
                    subject_name,
                    alert.metric_id,
                    alert.severity,
                    alert.decade_start.isoformat(),
                    customer.lang,
                )
                send_email(customer.email, subject, body)
                sent += 1
            except Exception:
                logger.warning("Failed to email customer %s for alert %s", customer.id, alert.id)

        alert.notified_at = func.now()
        db.commit()

        _log_event(
            db,
            action="notify_threshold_alert",
            subject=str(alert.id),
            payload={
                "alert_id": alert.id,
                "metric_id": alert.metric_id,
                "severity": alert.severity,
                "recipients": [c.email for c, _ in recipients],
            },
            status="ok" if recipients else "skipped_no_recipients",
        )

    logger.info("Processed %s alerts, sent %s emails", len(alerts), sent)
    return sent


def _summary_already_sent(db: Session, customer_id: int, decade: date) -> bool:
    subject = f"{customer_id}:{decade.isoformat()}"
    existing = db.scalars(
        select(AgentEvent).where(
            AgentEvent.agent == "notifier",
            AgentEvent.action == "send_decade_summary",
            AgentEvent.subject == subject,
        )
    ).first()
    return existing is not None


def notify_decade_summary(db: Session, decade: date) -> int:
    """Emails every customer with at least one field a summary of that decade's metrics."""
    customers = db.scalars(
        select(Customer).join(Field, Field.customer_id == Customer.id).distinct()
    ).all()

    sent = 0
    for customer in customers:
        if _summary_already_sent(db, customer.id, decade):
            continue

        fields = db.scalars(select(Field).where(Field.customer_id == customer.id)).all()
        items = []
        for field in fields:
            metric = db.scalars(
                select(MetricValue).where(
                    MetricValue.unit_id == field.district_id,
                    MetricValue.metric_id == "vhi",
                    MetricValue.decade_start == decade,
                )
            ).first()
            value = f"{metric.value:.1f}" if metric else "n/a"
            items.append(f"{field.name}: VHI={value}")

        try:
            subject, body = render_decade_summary(
                customer.name or customer.email, decade.isoformat(), items, customer.lang
            )
            send_email(customer.email, subject, body)
            sent += 1
            status = "ok"
        except Exception:
            logger.warning("Failed to email decade summary to customer %s", customer.id)
            status = "error"

        _log_event(
            db,
            action="send_decade_summary",
            subject=f"{customer.id}:{decade.isoformat()}",
            payload={"customer_id": customer.id, "decade": decade.isoformat(), "items": items},
            status=status,
        )

    logger.info("Sent %s decade summaries for %s", sent, decade.isoformat())
    return sent


def main() -> None:
    parser = argparse.ArgumentParser(description="GeoIntel notifier agent")
    parser.add_argument(
        "--decade-summary",
        metavar="YYYY-MM-DD",
        help="Send decade summaries for this decade_start instead of threshold alerts.",
    )
    args = parser.parse_args()

    db = SessionLocal()
    try:
        if args.decade_summary:
            decade = date.fromisoformat(args.decade_summary)
            notify_decade_summary(db, decade)
        else:
            notify_threshold_alerts(db)
    finally:
        db.close()


if __name__ == "__main__":
    main()
