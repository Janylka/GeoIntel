from sqlalchemy import select
from sqlalchemy.orm import Session

from geointel.db.models.metrics import AdminUnit


def get_oblasts(session: Session) -> list[AdminUnit]:
    stmt = select(AdminUnit).where(AdminUnit.level == "oblast").order_by(AdminUnit.name_ru)
    return list(session.scalars(stmt))


def get_districts(session: Session, oblast_id: int) -> list[AdminUnit]:
    stmt = (
        select(AdminUnit)
        .where(AdminUnit.level == "district", AdminUnit.parent_id == oblast_id)
        .order_by(AdminUnit.name_ru)
    )
    return list(session.scalars(stmt))


def get_unit_by_id(session: Session, unit_id: int) -> AdminUnit | None:
    return session.get(AdminUnit, unit_id)
