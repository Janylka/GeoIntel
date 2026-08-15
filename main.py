from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session

from geointel.db.session import get_db, engine

app = FastAPI(
    title="GeoIntel API",
    version="0.1.0",
)

@app.get("/health", tags=["Health"])
def health_check(db: Session = Depends(get_db)):
    """
    Checks if the API is running and can connect to the database.
    """
    try:
        db.execute(engine.dialect.do_ping, {})
        return {"status": "ok", "database": "ok"}
    except Exception:
        return {"status": "ok", "database": "error"}