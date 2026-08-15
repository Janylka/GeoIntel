from datetime import date, datetime
from typing import Any

from geoalchemy2 import Geometry
from sqlalchemy import JSON, Date, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from geointel.db.session import Base


class AdminUnit(Base):
    __tablename__ = "admin_unit"
    id: Mapped[int] = mapped_column(primary_key=True)
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("admin_unit.id"))
    level: Mapped[str] = mapped_column(String, nullable=False)
    name_ru: Mapped[str] = mapped_column(String, nullable=False)
    name_ky: Mapped[str] = mapped_column(String, nullable=False)
    name_en: Mapped[str] = mapped_column(String, nullable=False)
    geom: Mapped[Any] = mapped_column(Geometry("MULTIPOLYGON", srid=4326), nullable=False)
    cropland_ha: Mapped[float | None] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class MetricValue(Base):
    __tablename__ = "metric_value"
    unit_id: Mapped[int] = mapped_column(ForeignKey("admin_unit.id"), primary_key=True)
    metric_id: Mapped[str] = mapped_column(String, primary_key=True)
    decade_start: Mapped[date] = mapped_column(Date, primary_key=True)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    quality: Mapped[float | None] = mapped_column(Float)
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class FieldMetric(Base):
    __tablename__ = "field_metric"
    field_id: Mapped[int] = mapped_column(ForeignKey("field.id"), primary_key=True)
    metric_id: Mapped[str] = mapped_column(String, primary_key=True)
    decade_start: Mapped[date] = mapped_column(Date, primary_key=True)
    value: Mapped[float] = mapped_column(Float, nullable=False)


class YieldForecast(Base):
    __tablename__ = "yield_forecast"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    unit_id: Mapped[int] = mapped_column(ForeignKey("admin_unit.id"), nullable=False)
    crop: Mapped[str] = mapped_column(String, nullable=False)
    season_year: Mapped[int] = mapped_column(Integer, nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    lo: Mapped[float] = mapped_column(Float, nullable=False)
    hi: Mapped[float] = mapped_column(Float, nullable=False)
    model_version: Mapped[str] = mapped_column(String, nullable=False)
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class WeatherForecast(Base):
    __tablename__ = "weather_forecast"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    field_id: Mapped[int] = mapped_column(ForeignKey("field.id"), nullable=False)
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    payload_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
