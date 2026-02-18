from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime
from datetime import datetime
from app.core.database import Base

class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    datetime = Column(DateTime, default=datetime.utcnow)
    symbol = Column(String, index=True)
    type = Column(String) # long_open, etc.
    price = Column(Float)
    is_processed = Column(Boolean, default=False)
