from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from geointel.api.deps import get_current_user
from geointel.contracts.plans import Plan
from geointel.db.models.billing import Invoice
from geointel.db.models.customer import Customer
from geointel.db.session import get_db
from geointel.services.billing import create_invoice

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
    return {
        "invoice_id": invoice.id,
        "amount_tiyin": invoice.amount_tiyin,
        "status": invoice.status,
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
    return invoices
