import time
import threading
from flask import Flask, request, jsonify
from waitress import serve

from app.core.config import settings
from app.core.logging import logger
from app.core import state
from app.services import trade_service
from d_model import md_c_alerts as alerts_model

# Constants
import time
import threading

from app.core.config import settings
from app.core.logging import logger
from app.core import state
from app.services import trade_service
from app.core.database import SessionLocal
from app.core import crud

# Constants
TYPES = ["long_open", "long_close", "short_open", "short_close"]
WAIT_TIME = 10

# Global Locks/State for this service
_push_order_lock = threading.Lock()

def validate_type(alert_type: str) -> bool:
    return isinstance(alert_type, str) and not alert_type.isdigit() and alert_type.lower().strip() in TYPES

def add_to_queue(symbol: str, alert_type: str, price: float) -> bool:
    db = SessionLocal()
    try:
        crud.create_alert(db, symbol, alert_type, price)
        return True
    except Exception as e:
        logger.error(f"[add_to_queue] Error: {e}")
        return False
    finally:
        db.close()

def process_order_queue():
    """
    Opens or closes trades from the queue using SQLite.
    """
    if _push_order_lock.locked():
        return

    with _push_order_lock:
        db = SessionLocal()
        try:
            time.sleep(WAIT_TIME)
            alerts = crud.get_pending_alerts(db)
            if not alerts:
                return

            # Unique symbols
            symbols = list({a.symbol for a in alerts})
            
            for symbol in symbols:
                long_pos = 0
                short_pos = 0
                
                symbol_alerts = [a for a in alerts if a.symbol == symbol]
                
                for alert in symbol_alerts:
                    if alert.type == "long_open": long_pos += 1
                    elif alert.type == "short_open": short_pos += 1
                    elif alert.type == "long_close": long_pos -= 1
                    elif alert.type == "short_close": short_pos -= 1
        
                if long_pos != short_pos:
                    if long_pos > 0: trade_service.execute_trade_logic(symbol, "long_open")
                    elif short_pos > 0: trade_service.execute_trade_logic(symbol, "short_open")
                    elif long_pos < 0: trade_service.execute_trade_logic(symbol, "long_close")
                    elif short_pos < 0: trade_service.execute_trade_logic(symbol, "short_close")
                
                crud.mark_alerts_processed_by_symbol(db, symbol)
                
        except Exception as e:
            logger.error(f"[process_order_queue] Error: {e}")
        finally:
            db.close()

def trigger_queue_processing():
    threading.Thread(target=process_order_queue).start()

def run_tradingview_service():
    """
    Background tasks for TradingView service.
    Currently used to keep the service 'alive' or monitor things.
    FastAPI handles the web server part now.
    """
    while True:
        try:
            # We don't need to manage Flask thread anymore.
            # But the 'Bot_Stop' logic was here.
            # If we want to support start/stop from Telegram, we should check it here.
            # But FastAPI is running separately. 
            # We can't easily 'stop' FastAPI from here without killing the process.
            # The 'bot_running' flag mainly controlled the LOOP in legacy code.
            
            time.sleep(WAIT_TIME)
        except Exception as e:
            logger.error(f"[run_tradingview_service] Error: {e}")
            time.sleep(WAIT_TIME)
