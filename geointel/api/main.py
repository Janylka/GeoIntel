from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from geointel.api.routers import explain, geo, units
from geointel.db.session import get_db

app = FastAPI(
    title="GeoIntel API",
    version="1.0.0",
    description="API Блока Б для геопространственной аналитики и мониторинга засухи",
)

# Настройка CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Регистрация эндпоинтов Блока Б
app.include_router(units.router, prefix="/api/units", tags=["Units"])
app.include_router(geo.router, prefix="/api/geo", tags=["GeoJSON"])
app.include_router(explain.router, prefix="/api/explain", tags=["LLM Explain"])


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