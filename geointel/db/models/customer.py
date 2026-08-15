from datetime import datetime

from geoalchemy2 import Geometry
from sqlalchemy import DateTime, Float, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from geointel.db.base import Base


class Customer(Base):
    __tablename__ = "customer"

    id: Mapped[int] = mapped_column(primary_key=True)
    auth_uid: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String, nullable=False)
    name: Mapped[str | None] = mapped_column(String)
    phone: Mapped[str | None] = mapped_column(String)
    org: Mapped[str | None] = mapped_column(String)
    plan: Mapped[str] = mapped_column(String, default="trial", nullable=False)
    lang: Mapped[str] = mapped_column(String, server_default="ru", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    fields: Mapped[list["Field"]] = relationship(back_populates="customer")


class Field(Base):
    __tablename__ = "field"

    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customer.id"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    crop: Mapped[str | None] = mapped_column(String)
    sowing_date: Mapped[str | None] = mapped_column(String)
    area_ha: Mapped[float | None] = mapped_column(Float)
    cropland_ha: Mapped[float | None] = mapped_column(Float)
    geom: Mapped[str] = mapped_column(Geometry("POLYGON", srid=4326), nullable=False)
    center: Mapped[str] = mapped_column(Geometry("POINT", srid=4326), nullable=False)
    radius_m: Mapped[float | None] = mapped_column(Float)
    district_id: Mapped[int] = mapped_column(ForeignKey("admin_unit.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    customer: Mapped["Customer"] = relationship(back_populates="fields")
