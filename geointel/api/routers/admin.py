from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from geointel.api.deps import get_current_user
from geointel.db.models.customer import Customer
from geointel.db.session import get_db
from geointel.services.billing import confirm_invoice

router = APIRouter()


@router.post("/invoices/{invoice_id}/confirm")
def admin_confirm_invoice(
    invoice_id: int,
    current_user: Customer = Depends(get_current_user),  # In real app, check if admin
    db: Session = Depends(get_db),
) -> Any:
    # DUMMY CHECK: ideally check if current_user has admin role
    try:
        invoice = confirm_invoice(db, invoice_id, current_user.auth_uid)
        return {"status": "ok", "invoice_id": invoice.id, "invoice_status": invoice.status}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
