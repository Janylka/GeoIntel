import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from geointel.api.deps import require_admin
from geointel.db.models.customer import Customer
from geointel.db.session import get_db
from geointel.services.billing import confirm_invoice
from geointel.services.email import send_email
from geointel.services.email_templates import render_payment_confirmed

router = APIRouter()


@router.post("/invoices/{invoice_id}/confirm")
def admin_confirm_invoice(
    invoice_id: int,
    current_user: Customer = Depends(require_admin),
    db: Session = Depends(get_db),
) -> Any:
    try:
        invoice = confirm_invoice(db, invoice_id, current_user.auth_uid)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    customer = db.get(Customer, invoice.customer_id)
    if customer:
        try:
            subject, body = render_payment_confirmed(
                customer.name or customer.email, invoice.id, invoice.plan, customer.lang
            )
            send_email(customer.email, subject, body)
        except Exception:
            logging.warning(
                "Failed to send payment confirmation email for invoice %s", invoice.id,
                exc_info=True,
            )

    return {"status": "ok", "invoice_id": invoice.id, "invoice_status": invoice.status}
