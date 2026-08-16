import json
import logging
import os

import firebase_admin
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from firebase_admin import auth, credentials
from sqlalchemy.orm import Session

from geointel.contracts.plans import Plan
from geointel.db.models.customer import Customer
from geointel.db.models.ops import AgentEvent
from geointel.db.session import get_db
from geointel.services.email import send_email
from geointel.services.email_templates import render_welcome

security = HTTPBearer()

if not firebase_admin._apps:
    # A bare initialize_app() creates an app with no project ID attached (it
    # doesn't raise), and verify_id_token() then fails for every token with
    # "A project ID is required to access the auth service." Building explicit
    # credentials from FIREBASE_CREDENTIALS_JSON is what actually makes the
    # app usable.
    creds_json = os.getenv("FIREBASE_CREDENTIALS_JSON")
    if creds_json:
        firebase_admin.initialize_app(credentials.Certificate(json.loads(creds_json)))
    else:
        logging.warning("FIREBASE_CREDENTIALS_JSON is not set; sign-in will fail.")

_SUPPORTED_LANGS = {"ru", "ky", "en"}


def _lang_from_header(accept_language: str | None) -> str:
    if not accept_language:
        return "ru"
    primary = accept_language.split(",")[0].strip().split("-")[0].lower()
    return primary if primary in _SUPPORTED_LANGS else "ru"


def get_current_user(
    token: HTTPAuthorizationCredentials = Depends(security),
    accept_language: str | None = Header(None),
    db: Session = Depends(get_db),
) -> Customer:
    try:
        decoded_token = auth.verify_id_token(token.credentials)
        uid = decoded_token.get("uid")
    except Exception:
        logging.warning("Firebase token verification failed", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    customer = db.query(Customer).filter(Customer.auth_uid == uid).first()
    if customer:
        return customer

    # First sign-in: find-or-create per spec, not a 401. The customer's email
    # comes from the verified Firebase token, never from client input.
    email = decoded_token.get("email") or f"{uid}@unknown.geointel"
    lang = _lang_from_header(accept_language)
    customer = Customer(auth_uid=uid, email=email, plan=Plan.TRIAL.value, lang=lang)
    db.add(customer)
    db.commit()
    db.refresh(customer)

    db.add(
        AgentEvent(
            agent="concierge",
            action="customer_registered",
            subject=str(customer.id),
            payload_json={"auth_uid": uid, "email": email, "plan": customer.plan, "lang": lang},
            status="ok",
        )
    )
    db.commit()

    try:
        subject, body = render_welcome(customer.name or customer.email, customer.plan, lang)
        send_email(customer.email, subject, body)
    except Exception:
        logging.warning("Failed to send welcome email to %s", customer.email, exc_info=True)

    return customer


def _admin_emails() -> set[str]:
    raw = os.getenv("ADMIN_EMAILS", "")
    return {e.strip().lower() for e in raw.split(",") if e.strip()}


def require_admin(current_user: Customer = Depends(get_current_user)) -> Customer:
    """
    Gate for admin-only endpoints (e.g. confirming invoices).

    Schema is frozen for the hackathon (see AGENTS.md -- no new migrations),
    so admin status is an ADMIN_EMAILS allowlist rather than a customer.role
    column. Revisit as a real column once migrations reopen.
    """
    if current_user.email.lower() not in _admin_emails():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This action requires admin privileges.",
        )
    return current_user
