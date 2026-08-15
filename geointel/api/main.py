from fastapi import Depends, FastAPI
from sqlalchemy.orm import Session

from geointel.db.session import get_db

app = FastAPI(
    title="GeoIntel API",
    version="0.1.0",
)

from sqlalchemy import text


@app.get("/health", tags=["Health"])
def health_check(db: Session = Depends(get_db)) -> dict[str, str]:
    """
    Checks if the API is running and can connect to the database.
    """
    try:
        db.execute(text("SELECT 1"))
        return {"status": "ok", "database": "ok"}
    except Exception:
        return {"status": "ok", "database": "error"}
