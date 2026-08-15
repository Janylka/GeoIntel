from datetime import date, datetime

from geoalchemy2 import Geometry
from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from geointel.db.session import Base


class AdminUnit(Base):
    __tablename__ = "admin_unit"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    level: Mapped[str] = mapped_column(String, nullable=False)  # oblast, district
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("admin_unit.id"))
    geom: Mapped[str] = mapped_column(Geometry("MULTIPOLYGON", srid=4326), nullable=False)
    cropland_ha: Mapped[float | None] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class MetricValue(Base):
    __tablename__ = "metric_value"

    unit_id: Mapped[int] = mapped_column(ForeignKey("admin_unit.id"), primary_key=True)
    metric_id: Mapped[str] = mapped_column(String, primary_key=True)
    decade_start: Mapped[date] = mapped_column(Date, primary_key=True)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    quality: Mapped[float | None] = mapped_column(Float)
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class FieldMetric(Base):
    __tablename__ = "field_metric"

    field_id: Mapped[int] = mapped_column(ForeignKey("field.id"), primary_key=True)
    metric_id: Mapped[str] = mapped_column(String, primary_key=True)
    decade_start: Mapped[date] = mapped_column(Date, primary_key=True)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class YieldForecast(Base):
    __tablename__ = "yield_forecast"

    id: Mapped[int] = mapped_column(primary_key=True)
    unit_id: Mapped[int] = mapped_column(ForeignKey("admin_unit.id"), nullable=False)
    crop: Mapped[str] = mapped_column(String, nullable=False)
    forecast_year: Mapped[int] = mapped_column(Integer, nullable=False)
    decade_start: Mapped[date] = mapped_column(Date, nullable=False)
    p10: Mapped[float] = mapped_column(Float, nullable=False)
    p50: Mapped[float] = mapped_column(Float, nullable=False)
    p90: Mapped[float] = mapped_column(Float, nullable=False)
    hi: Mapped[float] = mapped_column(Float, nullable=False)
    model_version: Mapped[str] = mapped_column(String, nullable=False)
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class WeatherForecast(Base):
    __tablename__ = "weather_forecast"

    id: Mapped[int] = mapped_column(primary_key=True)
    unit_id: Mapped[int] = mapped_column(ForeignKey("admin_unit.id"), nullable=False)
    forecast_date: Mapped[date] = mapped_column(Date, nullable=False)
    temp_min: Mapped[float] = mapped_column(Float)
    temp_max: Mapped[float] = mapped_column(Float)
    precip_mm: Mapped[float] = mapped_column(Float)
    humidity: Mapped[float] = mapped_column(Float)
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
