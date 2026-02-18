from sqlalchemy.orm import Session
from app.models.log import Log
from app.models.order import Order
from app.models.alert import Alert
from datetime import datetime

# Logs
def create_log(db: Session, type: str, func: str, desc: str):
    db_log = Log(type=type, func=func, desc=str(desc))
    db.add(db_log)
    db.commit()
    db.refresh(db_log)
    return db_log

def get_logs(db: Session, skip: int = 0, limit: int = 100):
    return db.query(Log).order_by(Log.datetime.desc()).offset(skip).limit(limit).all()

# Alerts
def create_alert(db: Session, symbol: str, type: str, price: float):
    db_alert = Alert(symbol=symbol, type=type, price=price)
    db.add(db_alert)
    db.commit()
    db.refresh(db_alert)
    return db_alert

def get_pending_alerts(db: Session):
    return db.query(Alert).filter(Alert.is_processed == False).all()

def mark_alert_processed(db: Session, alert_id: int):
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if alert:
        alert.is_processed = True
        db.commit()
        
def mark_alerts_processed_by_symbol(db: Session, symbol: str):
    # This matches the legacy logic which sets "que" to false for a symbol
    db.query(Alert).filter(Alert.symbol == symbol, Alert.is_processed == False).update({"is_processed": True})
    db.commit()

# Orders
def create_order(db: Session, symbol: str, side: str, leverage: int, quantity_coin: float, quantity_quote: float, entry_price: float):
    db_order = Order(
        symbol=symbol,
        side=side,
        leverage=leverage,
        quantity_coin=quantity_coin,
        quantity_quote=quantity_quote,
        entry_price=entry_price
    )
    db.add(db_order)
    db.commit()
    return db_order

def get_open_orders(db: Session, symbol: str = None):
    query = db.query(Order).filter(Order.is_open == True)
    if symbol:
        query = query.filter(Order.symbol == symbol)
    return query.all()

def close_order(db: Session, symbol: str, side: str, exit_price: float, pnl: float):
    # Close oldest open order for symbol/side
    # Note: Logic might need adjustment based on FIFO/LIFO or specific order matching
    # Legacy code didn't strictly link open/close in DB, it just updated "open" field
    # We will match the legacy behavior: Find orders and close them
    orders = db.query(Order).filter(
        Order.symbol == symbol, 
        Order.side == side, 
        Order.is_open == True
    ).all()
    
    for order in orders:
        order.is_open = False
        order.exit_price = exit_price
        order.pnl = pnl
        
    db.commit()
