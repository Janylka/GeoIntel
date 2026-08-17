import logging
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from geointel.api.deps import get_current_user
from geointel.contracts.plans import Plan
from geointel.db.models.billing import Invoice
from geointel.db.models.customer import Customer
from geointel.db.models.ops import AgentEvent
from geointel.db.session import get_db
from geointel.services.billing import create_invoice, get_payment_details
from geointel.services.email import send_email
from geointel.services.email_templates import render_invoice

router = APIRouter()


class InvoiceCreateRequest(BaseModel):
    plan: Plan


@router.post("/invoices")
def request_invoice(
    request: InvoiceCreateRequest,
    current_user: Customer = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    invoice = create_invoice(db, current_user.id, request.plan)
    payment_details = get_payment_details()

    try:
        subject, body = render_invoice(
            current_user.name or current_user.email,
            invoice.id,
            invoice.plan,
            invoice.amount_tiyin,
            invoice.status,
            current_user.lang,
        )
        send_email(current_user.email, subject, body)
    except Exception:
        logging.warning("Failed to send invoice email for invoice %s", invoice.id, exc_info=True)

    db.add(
        AgentEvent(
            agent="concierge",
            action="invoice_issued",
            subject=str(invoice.id),
            payload_json={
                "input": {"customer_id": current_user.id, "plan": request.plan.value},
                "output": {
                    "invoice_id": invoice.id,
                    "amount_tiyin": invoice.amount_tiyin,
                    "status": invoice.status,
                },
            },
            status="ok",
        )
    )
    db.commit()

    return {
        "invoice_id": invoice.id,
        "amount_tiyin": invoice.amount_tiyin,
        "status": invoice.status,
        "payment_details": payment_details,
    }


@router.get("/invoices")
def get_invoices(
    current_user: Customer = Depends(get_current_user), db: Session = Depends(get_db)
) -> Any:
    invoices = (
        db.query(Invoice)
        .filter(Invoice.customer_id == current_user.id)
        .order_by(Invoice.issued_at.desc())
        .all()
    )
    return [
        {
            "id": inv.id,
            "customer_id": inv.customer_id,
            "plan": inv.plan,
            "amount_tiyin": inv.amount_tiyin,
            "status": inv.status,
            "issued_at": inv.issued_at,
            "paid_at": inv.paid_at,
            "confirmed_by": inv.confirmed_by,
        }
        for inv in invoices
    ]
