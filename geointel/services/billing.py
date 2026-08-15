import json
import os
from typing import Any

from sqlalchemy.orm import Session

from geointel.contracts.plans import PLANS, Plan
from geointel.db.models.billing import Invoice

# Bank transfer, confirmed manually -- no online acquiring for the hackathon MVP
# (see PROMPT-BACKEND.md B8). Falls back to a placeholder so the invoice flow
# still works before real requisites are configured.
_DEFAULT_PAYMENT_DETAILS = {
    "method": "bank_transfer",
    "note": "PAYMENT_DETAILS_JSON is not configured; contact GeoIntel to arrange payment.",
}


def get_payment_details() -> dict[str, Any]:
    raw = os.getenv("PAYMENT_DETAILS_JSON")
    if not raw:
        return _DEFAULT_PAYMENT_DETAILS
    details: dict[str, Any] = json.loads(raw)
    return details


def create_invoice(db: Session, customer_id: int, plan: Plan) -> Invoice:
    plan_def = PLANS[plan]
    if plan_def.price_tiyin_month == 0:
        # Free plans are auto-paid
        status = "paid"
    else:
        status = "pending"

    invoice = Invoice(
        customer_id=customer_id,
        plan=plan.value,
        amount_tiyin=plan_def.price_tiyin_month,
        status=status,
    )
    db.add(invoice)
    db.commit()
    db.refresh(invoice)
    return invoice


def confirm_invoice(db: Session, invoice_id: int, admin_uid: str) -> Invoice:
    invoice = db.get(Invoice, invoice_id)
    if not invoice:
        raise ValueError("Invoice not found")

    invoice.status = "paid"
    invoice.confirmed_by = admin_uid

    from sqlalchemy.sql import func

    invoice.paid_at = func.now()

    # Update customer's plan
    from geointel.db.models.customer import Customer

    customer = db.get(Customer, invoice.customer_id)
    if customer:
        customer.plan = invoice.plan

    db.commit()
    db.refresh(invoice)
    return invoice
