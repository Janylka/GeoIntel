from collections.abc import Sequence

from geoalchemy2 import Geography
from sqlalchemy import func, select, type_coerce
from sqlalchemy.orm import Session

from geointel.db.models.customer import Field


class FieldRepository:
    def __init__(self, session: Session):
        self.session = session

    def find_fields_near_point(
        self, lat: float, lon: float, radius_meters: float
    ) -> Sequence[Field]:
        """
        Ищет поля, центр или границы которых находятся в пределах radius_meters
        от заданной точки (lat, lon). Использует PostGIS ST_DWithin по типу geography.
        """
        # Создаем геометрию точки в WGS84 (SRID 4326)
        point_geom = func.ST_SetSRID(func.ST_MakePoint(lon, lat), 4326)

        # Выполняем запрос ST_DWithin с приведением к geography для точного расчета в метрах
        stmt = select(Field).where(
            func.ST_DWithin(
                type_coerce(Field.center, Geography),
                type_coerce(point_geom, Geography),
                radius_meters,
            )
        )

        return self.session.scalars(stmt).all()
