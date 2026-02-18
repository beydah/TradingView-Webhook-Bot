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
TYPES = ["long_open", "long_close", "short_open", "short_close"]
REQUIRES = ["symbol", "alert", "price", "key"]
WAIT_TIME = 10

# Global Locks/State for this service
_push_order_lock = threading.Lock()
_server_thread = None
_server_instance = None # Waitress doesn't return instance easily to stop, but we can manage thread.

def validate_key(key: str) -> bool:
    return key == settings.ALERT_KEY

def validate_type(alert_type: str) -> bool:
    return isinstance(alert_type, str) and not alert_type.isdigit() and alert_type.lower().strip() in TYPES

def add_to_queue(symbol: str, alert_type: str, price: float) -> bool:
    return alerts_model.F_Add_Alerts(symbol, alert_type, price)

def set_queue_processed(symbol: str) -> bool:
    return alerts_model.F_Set_Alerts(symbol)

def process_order_queue():
    """
    Opens or closes trades from the queue.
    """
    if _push_order_lock.locked():
        return

    with _push_order_lock:
        try:
            time.sleep(WAIT_TIME)
            que = alerts_model.F_Get_Alerts(p_que=True)
            if not que or not que.get('alerts'):
                return

            # Unique symbols
            symbols = list({alert.get('symbol') for alert in que['alerts'] if alert.get('symbol')})
            
            for symbol in symbols:
                long_pos = 0
                short_pos = 0
                
                symbol_alerts = [a for a in que['alerts'] if a.get('symbol') == symbol]
                
                for alert in symbol_alerts:
                    alert_type = alert.get('type', '')
                    if alert_type == "long_open": long_pos += 1
                    elif alert_type == "short_open": short_pos += 1
                    elif alert_type == "long_close": long_pos -= 1
                    elif alert_type == "short_close": short_pos -= 1
        
                if long_pos != short_pos:
                    if long_pos > 0: trade_service.execute_trade_logic(symbol, "long_open")
                    elif short_pos > 0: trade_service.execute_trade_logic(symbol, "short_open")
                    elif long_pos < 0: trade_service.execute_trade_logic(symbol, "long_close")
                    elif short_pos < 0: trade_service.execute_trade_logic(symbol, "short_close")
                
                set_queue_processed(symbol)
                
        except Exception as e:
            logger.error(f"[process_order_queue] Error: {e}")

# Webhook Handler
app = Flask(__name__)

@app.route('/webhook', methods=['GET', 'POST'])
def webhook():
    try:
        data = request.get_json(force=True, silent=True)
        if data is None:
            data = request.args.to_dict()
            
        # Parse
        if not data: return jsonify({"status": "error", "message": "Empty payload"}), 400
        
        # Normalize
        p_data = {k.strip('"\''): v.strip('"\'') if isinstance(v, str) else v for k, v in data.items()}
        
        for key in REQUIRES:
            if key not in p_data:
                return jsonify({"status": "error", "message": f"Missing field: {key}"}), 400
                
        parsed = {
            'symbol': p_data['symbol'].lower().strip(),
            'alert': p_data['alert'].lower().strip(),
            'price': float(p_data['price']),
            'key': p_data['key'].strip()
        }
        
        if parsed['price'] <= 0:
            return jsonify({"status": "error", "message": "Invalid price"}), 400

        # Validate
        if not validate_key(parsed['key']):
            return jsonify({"status": "error", "message": "Invalid API key"}), 403

        if not validate_type(parsed['alert']):
            return jsonify({"status": "error", "message": "Invalid alert type"}), 400

        # Add to Queue
        success = add_to_queue(parsed['symbol'], parsed['alert'], parsed['price'])
        message = f"{parsed['symbol']} {parsed['alert']} added" if success else "Failed to add"
        
        if success:
             # Trigger queue processing in background thread
             threading.Thread(target=process_order_queue).start()
             
        return jsonify({"status": "success" if success else "error", "message": message}), 200 if success else 500

    except Exception as e:
        logger.error(f"[webhook] Error: {e}")
        return jsonify({"status": "error", "message": "Internal error"}), 500

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "ok", "service": "binance-bot-webhook"})

def run_server():
    try:
        # Waitress serve is blocking
        serve(app, host=settings.WEBHOOK_IP, port=settings.WEBHOOK_PORT, threads=4)
    except Exception as e:
        logger.error(f"[run_server] Error: {e}")

def start_bot_thread():
    if state.bot_running:
        return

    logger.info("Starting Webhook Server & Bot Loop...")
    state.bot_running = True
    state.bot_stop_event.clear()
    
    # Start Webhook Server in a separate thread because `serve` blocks
    global _server_thread
    _server_thread = threading.Thread(target=run_server, daemon=True)
    _server_thread.start()

def stop_bot_thread():
    if not state.bot_running:
        return
        
    logger.info("Stopping Bot...")
    state.bot_running = False
    state.bot_stop_event.set()
    # Waitress doesn't have a clean stop method exposed easily in this usage pattern
    # But since it's a daemon thread, it will die when main process invokes exit, 
    # OR we just ignore it.
    # For now, we just set the flag.

def run_tradingview_service():
    """
    Main loop for background tasks if any.
    The webhook server handles incoming immediately.
    The queue processing is triggered by webhook.
    So a loop might not be strictly necessary if everything is event driven, 
    but original code had a loop checking `Lock_Connect_Hook`.
    
    Original logic:
    while not Stop_Tradingview.is_set():
       ensure server is running
       sleep
       
    We handled server start in `start_bot_thread`.
    If we want to ensure it stays alive or restart it, we can check `_server_thread.is_alive()`.
    """
    while True:
        try:
            if state.bot_running:
                if _server_thread is None or not _server_thread.is_alive():
                     logger.warning("Webhook server thread died, restarting...")
                     start_bot_thread()
            
            time.sleep(WAIT_TIME)
        except Exception as e:
            logger.error(f"[run_tradingview_service] Error: {e}")
            time.sleep(WAIT_TIME)
