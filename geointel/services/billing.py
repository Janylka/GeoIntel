from sqlalchemy.orm import Session

from geointel.contracts.plans import PLANS, Plan
from geointel.db.models.billing import Invoice


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
