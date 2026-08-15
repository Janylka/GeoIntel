from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from geointel.db.models.ops import AgentEvent
from geointel.db.session import get_db

router = APIRouter()


@router.get("/events")
def get_agent_events(db: Session = Depends(get_db)) -> Any:
    stmt = select(AgentEvent).order_by(AgentEvent.created_at.desc()).limit(100)
    events = db.scalars(stmt).all()
    return events
