from sqlalchemy import JSON, Column, DateTime, Integer, String, text

from geointel.db.models.base import Base


class AgentEvent(Base):
    __tablename__ = "agent_event"

    id = Column(Integer, primary_key=True, autoincrement=True)
    agent = Column(String, nullable=False)
    action = Column(String, nullable=False)
    subject = Column(String)
    payload_json = Column(JSON)
    status = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=text("now()"), nullable=False)
