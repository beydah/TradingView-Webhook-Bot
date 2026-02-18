import threading
import time
import os

from app.core.config import settings
# from app.core import state  # Avoid circular import at top level if possible, or use it for states
from app.core import state
from app.core.logging import logger
from app.services import binance_service
# telegram_service will be imported inside functions to avoid circularity if necessary, 
# but transaction service is usually called BY telegram service, so telegram service imports transaction.
# Transaction service imports telegram service to SEND messages.
# This IS circular: TG -> TX -> TG.
# Solution: Pass the sender function (callback) to transaction service? 
# Or use a localized import. Localized import is easier for Refactoring Phase 1.

from d_model import md_c_alerts as alerts_model  # Legacy model, acceptable for Phase 1
from d_model import md_e_logs as logs_model      # Legacy model (now adapter), good.

# Constants
MAX_USER_STATES = 1000
STATE_CLEANUP_INTERVAL = 3600
STATE_EXPIRY_HOURS = 24

# State Management Helpers
def set_user_state(user_id: str, state_val: str) -> bool:
    try:
        with state.user_states_lock:
            state.user_states[user_id] = {'state': state_val, 'timestamp': time.time()}
            # Cleanup check could be optimized, but keeping original logic structure
            # if time.time() - state.last_cleanup_time > STATE_CLEANUP_INTERVAL: ... 
            # (We need last_cleanup_time in state if we want this)
        return True
    except Exception as e:
        logger.error(f"[set_user_state] Error: {e}")
        return False

def get_user_state(user_id: str) -> str:
    try:
        with state.user_states_lock:
            state_data = state.user_states.get(user_id)
            if state_data:
                return state_data.get('state')
            return ""
    except Exception as e:
        logger.error(f"[get_user_state] Error: {e}")
        return ""

def clear_user_state(user_id: str) -> bool:
    try:
        with state.user_states_lock:
            state.user_states.pop(user_id, None)
        return True
    except Exception as e:
        logger.error(f"[clear_user_state] Error: {e}")
        return False

# Command Logic
def handle_command(user_id: str, user_name: str, cmd: str) -> dict:
    try:
        msg = f"I didn't understand what you said, {user_name}."
        buttons = [[("Menu", "/menu")]]
        
        # Pending State Handling
        try:
            pending_state = get_user_state(user_id)
            cmd_text = str(cmd).strip()
            
            if pending_state:
                if cmd_text.lower().startswith('/exit'):
                    clear_user_state(user_id)
                    return {"message": "Operation cancelled.", "buttons": buttons}
                
                if cmd_text.startswith('/'):
                    clear_user_state(user_id)
                    # Fallthrough to normal command handling
                    pass
                else:
                    # Input processing for pending states
                    if pending_state == "await_setbalance":
                        # Legacy logic tried to update settings. 
                        # For now, we return a message saying it's read-only in .env
                        clear_user_state(user_id)
                        return {"message": "Settings are now managed via .env file. Please update the file and restart."}
                    
                    elif pending_state == "await_setleverage":
                        clear_user_state(user_id)
                        return {"message": "Settings are now managed via .env file. Please update the file and restart."}
                    
                    elif pending_state == "await_settype":
                        clear_user_state(user_id)
                        return {"message": "Settings are now managed via .env file. Please update the file and restart."}
                    
                    elif pending_state == "await_setapi":
                        clear_user_state(user_id)
                        return {"message": "API Keys are now managed via .env file for security."}
                    
                    elif pending_state == "await_getmarket":
                        symbol = cmd_text.upper()
                        clear_user_state(user_id)
                        info = binance_service.get_market_info(symbol)
                        if not info:
                            return {"message": f"Market information not found for {symbol}."}
                        
                        m = (
                            f"Symbol: {symbol}\n"
                            f"Price: {info.get('price','0')}\n"
                            f"Bid: {info.get('bid','0')} | Ask: {info.get('ask','0')}"
                        )
                        return {"message": m, "buttons": []}
                    else:
                        clear_user_state(user_id)

        except Exception as e:
            logger.error(f"[handle_command] State Error: {e}")
            pass

        # Standard Commands
        cmd_key = (cmd.split() or [""])[0]
        
        if cmd_key == "/start":
            msg = f"Hello {user_name}! System is ready."
            
        elif cmd_key == "/help":
            msg = "For help, contact developer."
            
        elif cmd_key == "/menu":
            msg = "Main Menu"
            buttons = [[
                ("Start Bot", "/botstart"), ("Stop Bot", "/botstop"), ("Bot Status", "/botstatus"),
                ("Get Alerts", "/getalert"), ("Get Positions", "/getpos"), ("Get Wallet", "/getwallet"),
                ("More", "/menu2")
            ]]
            
        elif cmd_key == "/menu2":
             msg = "Secondary Menu"
             buttons = [[
                ("Webhook", "/gethook"), ("Messages", "/getalertmessage"), ("Settings", "/getsettings"),
                ("Get Market", "/getmarket"), ("Get Logs", "/getlog"),
                ("Back", "/menu")
            ]]
            
        elif cmd_key == "/botstatus":
            msg = "Bot is running." if state.bot_running else "Bot is stopped."
            
        elif cmd_key == "/botstart":
            if state.bot_running:
                msg = "Bot is already running."
            else:
                msg = "Bot starting..."
                # Import here to avoid circular dependency
                from app.services.tradingview_service import start_bot_thread
                start_bot_thread() # This sets state.bot_running = True
                
        elif cmd_key == "/botstop":
            if not state.bot_running:
                msg = "Bot is already stopped."
            else:
                msg = "Bot stopping..."
                from app.services.tradingview_service import stop_bot_thread
                stop_bot_thread()

        elif cmd_key == "/setbalance":
            old_val = settings.ORDER_BALANCE_PERCENT
            set_user_state(user_id, "await_setbalance")
            return {"message": f"Enter New Balance Percentage (Current: {old_val}%)\nExit: /exit", "buttons": []}
        
        elif cmd_key == "/setleverage":
            old_val = settings.ORDER_LEVERAGE
            set_user_state(user_id, "await_setleverage")
            return {"message": f"Enter New Leverage (Current: {old_val}x)\nExit: /exit", "buttons": []}
            
        elif cmd_key == "/settype":
            old_val = settings.MARGIN_TYPE
            set_user_state(user_id, "await_settype")
            return {"message": f"Enter New Margin Type (Current: {old_val})\nExit: /exit", "buttons": []}

        elif cmd_key == "/getalert":
            try:
                db = SessionLocal()
                try:
                    alerts = crud.get_pending_alerts(db) # or get all? legacy was all active? "que" defaults to false? 
                    # Legacy: F_Get_Alerts().get('alerts') -> returns all in file.
                    # We might want to filter recent ones or just pending?
                    # Let's show last 10 for now or pending.
                    # "No active alerts found" implies pending?
                    # But the legacy code listed all...
                    # Let's fetch last 20 alerts
                    raw_alerts = db.query(crud.Alert).order_by(crud.Alert.datetime.desc()).limit(20).all()
                    
                    if not raw_alerts:
                        msg = "No alerts found."
                    else:
                        multi_msgs = ["Alerts (Last 20):"]
                        for a in raw_alerts:
                            status = "Waiting" if not a.is_processed else "Processed"
                            multi_msgs.append(f"{a.datetime.strftime('%Y-%m-%d %H:%M')} | {a.symbol} {a.type} | {a.price} | {status}")
                        return {"buttons": buttons, "multi": multi_msgs}
                finally:
                    db.close()
            except Exception:
                msg = "Error reading alerts."

        elif cmd_key == "/getpos":
            # Note: Binance Service gets ACTUAL positions from API.
            # DB serves as a log/history.
            # The command /getpos usually wants REAL positions.
            # So we KEEP binance_service.get_orders() which calls API.
            # But the legacy code used SR_Binance.F_Get_Orders() which is API.
            # So NO CHANGE needed for /getpos if it calls binance_service.
            
            # Wait, let's verify if binance_service calls API or DB.
            # checked binance_service: it calls client.futures_position_information(). Correct.
            pass # No change needed.
            
            positions = binance_service.get_orders()
            if not positions:
                msg = "No open positions."
            else:
                multi_msgs = ["Open Positions:"]
                for p in positions:
                    multi_msgs.append(f"{p['symbol']} {p['side']} | Entry: {p['entry_price']} | Qty: {p['quantity']} | PnL: {float(p['unrealized_pnl']):.2f}")
                return {"buttons": buttons, "multi": multi_msgs}

        elif cmd_key == "/getwallet":
            balances = binance_service.get_wallet_info()
            if not balances:
                msg = "Wallet info unavailable."
            else:
                multi_msgs = ["Wallet:"]
                for b in balances:
                    multi_msgs.append(f"{b['asset']}: {b['balance']} (Locked: {float(b['wait_balance']):.2f})")
                return {"buttons": buttons, "multi": multi_msgs}

        elif cmd_key == "/gethook":
            msg = f"Webhook:\nhttps://{settings.WEBHOOK_DOMAIN}/webhook"
            
        elif cmd_key == "/getalertmessage":
            msg = (f"Long Open: {settings.ALERT_LONG_OPEN}\n"
                   f"Long Close: {settings.ALERT_LONG_CLOSE}\n"
                   f"Short Open: {settings.ALERT_SHORT_OPEN}\n"
                   f"Short Close: {settings.ALERT_SHORT_CLOSE}")

        elif cmd_key == "/getsettings":
            msg = (f"Balance: {settings.ORDER_BALANCE_PERCENT}%\n"
                   f"Leverage: {settings.ORDER_LEVERAGE}x\n"
                   f"Margin: {settings.MARGIN_TYPE}")

        elif cmd_key == "/setapi":
             set_user_state(user_id, "await_setapi")
             return {"message": "Please send API Key... (actually managed by .env, but flow kept for consistency)", "buttons": []}

        elif cmd_key == "/getmarket":
             set_user_state(user_id, "await_getmarket")
             return {"message": "Enter symbol (e.g. BTCUSDT):", "buttons": []}
             
        elif cmd_key == "/getlog":
            try:
                # We need to create a text file with logs to send to user
                db = SessionLocal()
                try:
                    logs = crud.get_logs(db, limit=100)
                    
                    db_dir = os.path.join(os.getcwd(), 'data') # Changed from e_database to data
                    os.makedirs(db_dir, exist_ok=True)
                    file_path = os.path.join(db_dir, 'log_export.txt')
                    
                    with open(file_path, 'w', encoding='utf-8') as f:
                         for l in logs:
                            f.write(f"{l.datetime.strftime('%Y-%m-%d %H:%M:%S')} [{l.type.upper()}] {l.func}: {l.desc}\n")
                            
                    return {
                        "message": f"Here are the last 100 logs, {user_name}.",
                        "buttons": buttons,
                        "document": file_path
                    }
                finally:
                    db.close()
            except Exception as e:
                logger.error(f"[handle_command] Get Log Error: {e}")
                msg = "An error occurred while preparing the logs."

        return {"message": msg, "buttons": buttons}

    except Exception as e:
        logger.error(f"[handle_command] Error: {e}")
        return {}

def process_transaction(user_id: str, user_name: str, cmd: str) -> bool:
    """
    Main entry point for telegram updates.
    """
    try:
        from app.services import telegram_service 
        response = handle_command(user_id, user_name, cmd)
        if not response:
            return False
            
        message = response.get("message", "")
        buttons = response.get("buttons")
        multi = response.get("multi")
        
        if multi:
            for m in multi:
                telegram_service.send_message(m)
        elif message:
            if buttons:
                telegram_service.send_buttons(message, buttons)
            else:
                telegram_service.send_message(message)
                
        return True
    except Exception as e:
        logger.error(f"[process_transaction] Error: {e}")
        return False
