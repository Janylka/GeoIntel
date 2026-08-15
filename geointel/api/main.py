from pathlib import Path

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from sqlalchemy.orm import Session

from geointel.api.errors import register_error_handlers
from geointel.api.routers import admin, alerts, billing, explain, fields, geo, ops, reports, units
from geointel.db.session import get_db

app = FastAPI(
    title="GeoIntel API",
    version="1.0.0",
    description="API Блока Б для геопространственной аналитики и мониторинга засухи",
)

register_error_handlers(app)

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
app.include_router(alerts.router, prefix="/api/alerts", tags=["Alerts"])
app.include_router(ops.router, prefix="/api/ops", tags=["Operations"])
app.include_router(fields.router, prefix="/api/fields", tags=["Fields"])
app.include_router(billing.router, prefix="/api/billing", tags=["Billing"])
app.include_router(admin.router, prefix="/api/admin", tags=["Admin"])
app.include_router(reports.router, prefix="/api/reports", tags=["Reports"])


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


# Static frontend, served from the same origin as the API so auth cookies/tokens
# and CORS stay simple. Must be mounted last: it's a catch-all for "/".
FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"
if FRONTEND_DIR.is_dir():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
