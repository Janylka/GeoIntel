import firebase_admin
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from firebase_admin import auth
from sqlalchemy.orm import Session

from geointel.db.models.customer import Customer
from geointel.db.session import get_db

security = HTTPBearer()

if not firebase_admin._apps:
    try:
        firebase_admin.initialize_app()
    except Exception:
        pass


def get_current_user(
    token: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)
) -> Customer:
    try:
        # В DEV среде, если нет ключа, можно замокать, но по заданию нужна firebase auth
        decoded_token = auth.verify_id_token(token.credentials)
        uid = decoded_token.get("uid")
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    customer = db.query(Customer).filter(Customer.auth_uid == uid).first()
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not registered in database",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return customer
