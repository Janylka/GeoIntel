import hashlib
import json
from fastapi import APIRouter, Depends, Response
from sqlalchemy import func
from sqlalchemy.orm import Session

from geointel.db.models.metrics import AdminUnit
from geointel.db.session import get_db

router = APIRouter()

@router.get("/units.geojson")
def get_units_geojson(response: Response, db: Session = Depends(get_db)):
    # Преобразуем PostGIS геометрию напрямую в GeoJSON через ST_AsGeoJSON
    units = (
        db.query(
            AdminUnit.id,
            AdminUnit.name_ru,
            AdminUnit.level,
            func.ST_AsGeoJSON(AdminUnit.geom).label("geojson")
        )
        .all()
    )
    
    features = []
    for u in units:
        features.append({
            "type": "Feature",
            "id": u.id,
            "properties": {
                "id": u.id,
                "name_ru": u.name_ru,
                "level": u.level
            },
            "geometry": json.loads(u.geojson) if u.geojson else None
        })
    
    geojson_data = {
        "type": "FeatureCollection",
        "features": features
    }
    
    # Генерация ETag для кэширования
    content_bytes = json.dumps(geojson_data).encode("utf-8")
    etag = hashlib.md5(content_bytes).hexdigest()
    
    response.headers["ETag"] = f'"{etag}"'
    response.headers["Cache-Control"] = "public, max-age=3600"
    
    return geojson_data