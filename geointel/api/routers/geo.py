import hashlib
import json
from typing import Any

from fastapi import APIRouter, Depends, Header, Response, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from geointel.db.models.metrics import AdminUnit
from geointel.db.session import get_db

router = APIRouter()


@router.get("/units.geojson")
def get_units_geojson(
    response: Response,
    if_none_match: str | None = Header(None),
    db: Session = Depends(get_db),
) -> Any:
    units = db.query(
        AdminUnit.id,
        AdminUnit.name_ru,
        AdminUnit.level,
        func.ST_AsGeoJSON(AdminUnit.geom).label("geojson"),
    ).all()

    features = [
        {
            "type": "Feature",
            "id": u.id,
            "properties": {
                "id": u.id,
                "name_ru": u.name_ru,
                "level": u.level,
            },
            "geometry": json.loads(u.geojson) if u.geojson else None,
        }
        for u in units
    ]

    geojson_data = {"type": "FeatureCollection", "features": features}

    content_bytes = json.dumps(geojson_data, sort_keys=True).encode("utf-8")
    etag = f'"{hashlib.md5(content_bytes).hexdigest()}"'

    # Проверка ETag: если клиент передал актуальный хеш — отдаем 304 Not Modified
    if if_none_match and if_none_match == etag:
        return Response(status_code=status.HTTP_304_NOT_MODIFIED)

    response.headers["ETag"] = etag
    response.headers["Cache-Control"] = "public, max-age=3600"

    return geojson_data
