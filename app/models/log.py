from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime
from app.core.database import Base

class Log(Base):
    __tablename__ = "logs"

    id = Column(Integer, primary_key=True, index=True)
    datetime = Column(DateTime, default=datetime.utcnow)
    type = Column(String, index=True)
    func = Column(String, index=True)
    desc = Column(String)
