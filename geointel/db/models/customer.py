from datetime import date, datetime
from typing import Any

from geoalchemy2 import Geometry
from sqlalchemy import Date, DateTime, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from geointel.db.session import Base


class Customer(Base):
    __tablename__ = "customer"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    auth_uid: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    name: Mapped[str | None] = mapped_column(String)
    phone: Mapped[str | None] = mapped_column(String)
    org: Mapped[str | None] = mapped_column(String)
    plan: Mapped[str] = mapped_column(String, nullable=False)
    lang: Mapped[str] = mapped_column(String, server_default="ru", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    fields: Mapped[list["Field"]] = relationship(back_populates="customer")


class Field(Base):
    __tablename__ = "field"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customer.id"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    crop: Mapped[str | None] = mapped_column(String)
    sowing_date: Mapped[date | None] = mapped_column(Date)
    area_ha: Mapped[float] = mapped_column(Float, nullable=False)
    cropland_ha: Mapped[float | None] = mapped_column(Float)
    geom: Mapped[Any] = mapped_column(Geometry("POLYGON", srid=4326), nullable=False)
    center: Mapped[Any] = mapped_column(Geometry("POINT", srid=4326), nullable=False)
    radius_m: Mapped[float | None] = mapped_column(Float)
    district_id: Mapped[int] = mapped_column(ForeignKey("admin_unit.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    customer: Mapped["Customer"] = relationship(back_populates="fields")
