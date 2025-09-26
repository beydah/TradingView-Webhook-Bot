# region ===== INFO ===================================================================================================

# Developer : Ilkay Beydah Saglam
# Website   : https://beydahsaglam.com
# Created   : 2025-08-21
# Version   : Python 3.10

# DESC:
#   This script is designed to connect with TradingView, receive signals,
#   and standardize position opening/closing signals.

# FEATURES:
#   - Opening and closing orders (Long & Short)
#   - Automatic signal processing with TradingView webhook handler
#   - Notification system (e.g., via Telegram)
#   - Secure request validation and fallback mechanism

# endregion
# region ===== LIBRARY ================================================================================================

from c_service import sr_a_trade as     SR_Trade

from d_model import md_a_settings as    MD_Settings
from d_model import md_c_alerts as      MD_Alerts
from d_model import md_e_logs as        MD_Logs

import time as                          LB_Time
import threading as                     LB_Thread
from flask import Flask as              LB_Flask

from flask import request as            LB_Request
from flask import jsonify as            LB_Jsonify
from waitress import create_server as   LB_CreateServer

# endregion
# region ===== VARIABLE ===============================================================================================

SETTINGS: dict  = MD_Settings.F_Get_Settings()
TYPES: list     = ["long_open", "long_close", "short_open", "short_close"]
REQUIRES: list  = ["symbol", "alert", "price", "key"]
WAIT_TIME: int  = 10

Lock_Push_Order: bool   = False
Lock_Connect_Hook: bool = False
Bot_Status: bool        = False
Bot_Stop: bool          = False
Server_Thread           = None
Server_Instance         = None
Stop_Tradingview        = LB_Thread.Event()

# endregion
# region ===== OBJECT =================================================================================================

# endregion
# region ===== FUNCTION ===============================================================================================

def F_Webhook_Handler():
    try:
        data = LB_Request.get_json(force=True, silent=True)
        if data is None: data = LB_Request.args.to_dict()
        parsed = F_Webhook_Parse(data)
        if not parsed: return F_Webhook_Fallback({"status": "error", "message": "Failed to parse payload"}), 400
        for key in REQUIRES:
            if key not in parsed: return F_Webhook_Fallback({"status": "error", "message": f"Missing field: {key}"}), 400

        if not F_Validate_Key(parsed['key']): 
            return F_Webhook_Fallback({"status": "error", "message": "Invalid API key"}), 403

        if not F_Validate_Type(parsed['alert']):
            return F_Webhook_Fallback({"status": "error", "message": "Invalid order alert type"}), 400

        success                     = F_Add_Que(parsed['symbol'], parsed['alert'], parsed['price'])
        if success: message: str    = f"{parsed['symbol']} {parsed['alert']} order added to queue"
        else: message: str          = f"{parsed['symbol']} {parsed['alert']} failed to add order to queue"
        response                    = {"status": "success" if success else "error", "message": message}
        if success and not Lock_Push_Order: LB_Thread.Thread(target=F_Push_Order).start()
        return F_Webhook_Fallback(response), 200 if success else 500
    except Exception as e:
        MD_Logs.F_Add_Logs("ERROR", "F_Webhook_Handler", e)
        return F_Webhook_Fallback({"status": "error", "message": "Internal server error"}), 500

def F_Webhook_Parse(p_data) -> dict:
    # DESC: Parses the webhook JSON data and converts it into a usable format.
    try:
        if not p_data: return {}
        p_data = {k.strip('"\''): v.strip('"\'') if isinstance(v, str) else v for k, v in p_data.items()}
        for key in REQUIRES: 
            if key not in p_data: return {}
        
        parsed = {
            'symbol':   p_data['symbol'].lower().strip(),
            'alert':    p_data['alert'].lower().strip(),
            'price':    float(p_data['price']),
            'key':      p_data['key'].strip()
        }
        
        if parsed['price'] <= 0: return {}
        return parsed
    except Exception as e:
        MD_Logs.F_Add_Logs("ERROR", "F_Webhook_Parse", e)
        return {}

def F_Webhook_Fallback(p_payload) -> dict:
    # DESC: Provides a standard formatted response to incoming signals and logs them.
    try:
        if not isinstance(p_payload, dict): p_payload = {"status": "error", "message": "Invalid payload format"}
        response = {"status": p_payload.get("status", "unknown"), "message": p_payload.get("message", "")}
        return response
    except Exception as e:
        MD_Logs.F_Add_Logs("ERROR", "F_Webhook_Fallback", e)
        return {"status": "error", "message": "Internal server error while processing response"}

def F_Validate_Key(p_key: str) -> bool: 
    # DESC: Checks the incoming key.
    try: return p_key == SETTINGS.get("alert_key")
    except Exception as e: return not MD_Logs.F_Add_Logs("ERROR", "F_Validate_Key", e)

def F_Validate_Type(p_type: str) -> bool:
    # DESC: Checks the transaction type.
    try: return isinstance(p_type, str) and not p_type.isdigit() and p_type.lower().strip() in TYPES
    except Exception as e: return not MD_Logs.F_Add_Logs("ERROR", "F_Validate_Type", e)

def F_Add_Que(p_symbol: str, p_type: str, p_price: float) -> bool: 
    # DESC: Adds a new alert.
    try: return MD_Alerts.F_Add_Alerts(p_symbol, p_type, p_price)
    except Exception as e: return not MD_Logs.F_Add_Logs("ERROR", "F_Add_Que", e)

def F_Set_Que(p_symbol: str) -> bool: 
    # DESC: Updates the activity status.
    try: return MD_Alerts.F_Set_Alerts(p_symbol)
    except Exception as e: return not MD_Logs.F_Add_Logs("ERROR", "F_Set_Que", e)

def F_Push_Order() -> bool:
    # DESC: Opens or closes trades from the queue. Processes records filtered with p_que=True from Alerts.json.
    try:
        global Lock_Push_Order
        if Lock_Push_Order: return False
        Lock_Push_Order = True
        LB_Time.sleep(WAIT_TIME)
        que: dict = MD_Alerts.F_Get_Alerts(p_que=True)
        if not que or not que.get('alerts'):  
            Lock_Push_Order = False
            return False

        symbols = list({alert.get('symbol') for alert in que['alerts'] if alert.get('symbol')})
        for symbol in symbols:
            long_pos: int   = 0
            short_pos: int  = 0
            symbol_alerts = [a for a in que['alerts'] if a.get('symbol') == symbol]
            for alert in symbol_alerts:
                alert_type = alert.get('type', '')
                if alert_type   == "long_open":     long_pos    += 1
                elif alert_type == "short_open":    short_pos   += 1
                elif alert_type == "long_close":    long_pos    -= 1
                elif alert_type == "short_close":   short_pos   -= 1
    
            if long_pos != short_pos:
                if long_pos     > 0: SR_Trade.F_Trade_Business(symbol, "long_open")
                elif short_pos  > 0: SR_Trade.F_Trade_Business(symbol, "short_open")
                elif long_pos   < 0: SR_Trade.F_Trade_Business(symbol, "long_close")
                elif short_pos  < 0: SR_Trade.F_Trade_Business(symbol, "short_close")
            
            F_Set_Que(symbol)

        Lock_Push_Order = False
        return True
    except Exception as e: 
        Lock_Push_Order = False
        return not MD_Logs.F_Add_Logs("ERROR", "F_Push_Order", e)

def F_Connect_Webhook() -> bool:
    # DESC: Opens the webhook connection and starts the Flask application.
    global Lock_Connect_Hook, O_Hook, Bot_Stop, Server_Thread, Server_Instance
    try:
        O_Hook = LB_Flask(__name__)

        @O_Hook.route('/webhook', methods=['GET', 'POST'])
        def webhook(): return F_Webhook_Handler()

        @O_Hook.route('/health', methods=['GET'])
        def health_check(): return LB_Jsonify({"status": "ok", "service": "binance-bot-webhook"})
            
        @O_Hook.errorhandler(404)
        def not_found(error): return F_Webhook_Fallback({"status": "error", "message": "Endpoint not found"}), 404
            
        @O_Hook.errorhandler(500)
        def server_error(error): return F_Webhook_Fallback({"status": "error", "message": "Internal server error"}), 500
        
        ip      = SETTINGS.get('webhook_ip',       '127.0.0.1"')
        port    = int(SETTINGS.get('webhook_port', '5001'))
        Lock_Connect_Hook = True
        def run_server():
            try:
                global Server_Instance
                Server_Instance = LB_CreateServer(O_Hook, host=ip, port=port, threads=4)
                Server_Instance.run()
            except ImportError: O_Hook.run(host=ip, port=port, debug=False, use_reloader=False)
        
        if Bot_Stop:
            try:
                if Server_Instance: Server_Instance.close()
                if Server_Thread and Server_Thread.is_alive(): Server_Thread.join(timeout=1)
            except Exception: pass
            Lock_Connect_Hook = False
            return True

        Server_Thread = LB_Thread.Thread(target=run_server, daemon=True)
        Server_Thread.start()
        return True
    except Exception as e:
        Lock_Connect_Hook = False
        return not MD_Logs.F_Add_Logs("ERROR", "F_Connect_Webhook", e)

def F_Tradingview_Business() -> bool:
    # DESC: Controls the TradingView workflow
    global Bot_Status, Lock_Connect_Hook, Bot_Stop, Server_Thread, Server_Instance
    try:
        Stop_Tradingview.clear()
        Server_Instance = None
        Server_Thread = None
    except Exception: pass

    Bot_Status = True
    while not Stop_Tradingview.is_set():
        try:
            if not Lock_Connect_Hook:
                webhook_thread = LB_Thread.Thread(target=F_Connect_Webhook,daemon=True)
                webhook_thread.start()
            
            if Bot_Stop:
                try:
                    if Server_Instance:
                        Server_Instance.close()
                        Server_Instance = None
                    if Server_Thread and Server_Thread.is_alive(): Server_Thread.join(timeout=1)
                except Exception: pass

                Stop_Tradingview.set()
                Lock_Connect_Hook = False
                Bot_Status = False
                return True

            LB_Time.sleep(WAIT_TIME)
        except Exception as e: 
            Lock_Connect_Hook = False
            MD_Logs.F_Add_Logs("ERROR", "F_Tradingview_Business", e)
    Bot_Status = False
    Bot_Stop = False

# endregion
