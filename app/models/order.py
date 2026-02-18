from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime
from datetime import datetime
from app.core.database import Base

class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    datetime = Column(DateTime, default=datetime.utcnow)
    symbol = Column(String, index=True)
    side = Column(String) # LONG/SHORT
    is_open = Column(Boolean, default=True)
    leverage = Column(Integer)
    quantity_coin = Column(Float)
    quantity_quote = Column(Float)
    entry_price = Column(Float)
    exit_price = Column(Float, nullable=True)
    pnl = Column(Float, nullable=True)
