# region ===== INFO ===================================================================================================

# Developer : Ilkay Beydah Saglam
# Website   : https://beydahsaglam.com
# Created   : 2025-08-21
# Version   : Python 3.10

# DESC:
#   This script is designed to manage user transactions via Telegram and interact
#   with the Binance Futures API. Commands from the user are processed to update
#   parameters such as balance, leverage, order type, and stop settings,
#   and the transaction flow is managed.

# FEATURES:
#   - Capturing and processing Telegram user commands
#   - User state management (set/get/clear state)
#   - Adjustments for balance, leverage, and margin type (isolated/cross)
#   - Stop loss enable/disable control
#   - Managing pending user states
#   - Directing commands to business logic
#   - Transaction business flow management

# endregion
# region ===== LIBRARY ================================================================================================

from c_service import sr_b_tradingview as   SR_TradingView
from c_service import sr_c_binance as       SR_Binance
from c_service import sr_e_telegram as      SR_Telegram

from d_model import md_a_settings as    MD_Settings
from d_model import md_c_alerts as      MD_Alerts
from d_model import md_e_logs as        MD_Logs

import os as            LB_OS
import time as          LB_Time
import threading as     LB_Thread

# region ===== VARIABLE ===============================================================================================

MAX_USER_STATES: int        = 1000
STATE_CLEANUP_INTERVAL: int = 3600
STATE_EXPIRY_HOURS: int     = 24

# endregion
# region ===== OBJECT =================================================================================================

User_States         = {}
User_States_Lock    = LB_Thread.Lock()
Last_Cleanup_Time   = LB_Time.time()

# endregion
# region ===== FUNCTION ===============================================================================================

def F_Set_User_State(p_id: str, p_state: str) -> bool:
    # DESC: Safely sets the user state
    try:
        with User_States_Lock:
            User_States[p_id] = {'state': p_state, 'timestamp': LB_Time.time()}
            if LB_Time.time() - Last_Cleanup_Time > STATE_CLEANUP_INTERVAL: F_Cleanup_User_States()
        return True
    except Exception as e: return not MD_Logs.F_Add_Logs("ERROR", "F_Set_User_State", e)

def F_Get_User_State(p_id: str) -> str:
    # DESC: Safely gets the user state
    try:
        with User_States_Lock:
            state_data = User_States.get(p_id)
            if state_data: return state_data.get('state')
            return ""
    except Exception as e: 
        MD_Logs.F_Add_Logs("ERROR", "F_Get_User_State", e)
        return ""

def F_Clear_User_State(p_id: str) -> bool:
    # DESC: Safely clears the user state
    try:
        with User_States_Lock: User_States.pop(p_id, None)
        return True
    except Exception as e: return not MD_Logs.F_Add_Logs("ERROR", "F_Clear_User_State", e)

def F_Cleanup_User_States() -> bool:
    # DESC: Cleans up old user states (e.g., deletes expired states)
    try:
        global Last_Cleanup_Time
        current_time = LB_Time.time()
        with User_States_Lock:
            if len(User_States) > MAX_USER_STATES:
                sorted_states = sorted(User_States.items(), key=lambda x: x[1].get('timestamp', 0))
                states_to_remove = int(len(sorted_states) * 0.2)
                for i in range(states_to_remove):
                    if sorted_states[i]: User_States.pop(sorted_states[i][0], None)
            
            expiry_time = current_time - (STATE_EXPIRY_HOURS * 3600)
            expired_states = []
            for user_id, state_data in User_States.items():
                if state_data.get('timestamp', 0) < expiry_time: expired_states.append(user_id)
            
            for user_id in expired_states: User_States.pop(user_id, None)
            Last_Cleanup_Time = current_time
        return True
    except Exception as e: return not MD_Logs.F_Add_Logs("ERROR", "F_Cleanup_User_States", e)

def F_Set_Balance(p_balance: str) -> bool:
    # DESC: Sets the balance percentage the user will use for trading (min: 1, max: 100)
    try:
        val = int(str(p_balance).strip())
        if val < 1 or val > 100: return False
        return MD_Settings.F_Set_Settings("order_balance", str(val))
    except Exception as e: return not MD_Logs.F_Add_Logs("ERROR", "F_Set_Balance", e)

def F_Set_Leverage(p_leverage: str) -> bool:
    # DESC: Sets the leverage ratio the user will use for trading (min: 1, max: 125)
    try:
        val = int(str(p_leverage).strip())
        if val < 1 or val > 125: return False
        return MD_Settings.F_Set_Settings("order_leverage", str(val))
    except Exception as e: return not MD_Logs.F_Add_Logs("ERROR", "F_Set_Leverage", e)

def F_Set_Type(p_margin_type: str) -> bool:
    # DESC: Sets the user's margin type (ISOLATED or CROSSED)
    try:
        val = str(p_margin_type).strip().lower()
        if val in ["isolated", "isole", "izole"]: val = "isolated"
        elif val in ["cross", "crossed", "cros"]: val = "crossed"
        else: return False
        return MD_Settings.F_Set_Settings("margin_type", val)
    except Exception as e: return not MD_Logs.F_Add_Logs("ERROR", "F_Set_Type", e)

def F_Set_Keys(p_api_secret: str) -> bool:
    # DESC: Updates the user's Binance API Key and Secret Key information
    try:
        api_key, api_secret = p_api_secret.split("\n")
        MD_Settings.F_Set_Settings("binance_api", api_key)
        MD_Settings.F_Set_Settings("binance_secret", api_secret)
        return True
    except Exception as e: return not MD_Logs.F_Add_Logs("ERROR", "F_Set_Keys", e)

def F_Handle_Command(p_id: str, p_name: str, p_cmd: str) -> dict:
    # DESC: Processes user commands from Telegram and prepares the appropriate response
    try:
        msg: str        = f"I didn't understand what you said, {p_name}."
        buttons: list   = [[("Menu", "/menu")]]
        settings: dict  = MD_Settings.F_Get_Settings()
        cancel_note: str = ""
        try:
            pending_state = F_Get_User_State(p_id)
            if pending_state and str(p_cmd).strip().lower().startswith('/exit'):
                F_Clear_User_State(p_id)
                return {"user_id": p_id, "user_name": p_name, "command": p_cmd, "message": "Operation cancelled.", "buttons": buttons}
                
            if pending_state and str(p_cmd).strip().startswith('/'):
                F_Clear_User_State(p_id)
                cancel_note = "Operation cancelled.\n\n"

            if pending_state and not str(p_cmd).strip().startswith('/'):
                text = str(p_cmd).strip()
                if pending_state == "await_setbalance":
                    ok = F_Set_Balance(text)
                    F_Clear_User_State(p_id)
                    return {"user_id": p_id, "user_name": p_name, "command": p_cmd, "message": ("Balance percentage updated." if ok else "Invalid balance percentage. (1-100)")}
                
                elif pending_state == "await_setleverage":
                    ok = F_Set_Leverage(text)
                    F_Clear_User_State(p_id)
                    return {"user_id": p_id, "user_name": p_name, "command": p_cmd, "message": ("Leverage updated." if ok else "Invalid leverage. (1-125)")}
                
                elif pending_state == "await_settype":
                    ok = F_Set_Type(text)
                    F_Clear_User_State(p_id)
                    return {"user_id": p_id, "user_name": p_name, "command": p_cmd, "message": ("Margin type updated." if ok else "Invalid margin type. (isolated/crossed)")}
                
                elif pending_state == "await_setapi":
                    ok = F_Set_Keys(text)
                    F_Clear_User_State(p_id)
                    return {"user_id": p_id, "user_name": p_name, "command": p_cmd, "message": ("API keys updated." if ok else "Incorrect API/Secret format. Please send in the format 'API_KEY\nSECRET_KEY'.")}
                
                elif pending_state == "await_getmarket":
                    symbol = text.upper()
                    try:
                        info = SR_Binance.F_Get_Market_Info(symbol)
                        F_Clear_User_State(p_id)
                        if not info:
                            return {"user_id": p_id, "user_name": p_name, "command": p_cmd, "message": f"Market information not found for {symbol}."}
                        
                        m = (
                            f"Symbol: {symbol}\n"
                            f"Last Price: {info.get('price','0')}\n"
                            f"Best Bid: {info.get('bid','0')} | Best Ask: {info.get('ask','0')}"
                        )
                        
                        return {"user_id": p_id, "user_name": p_name, "command": p_cmd, "message": m, "buttons": []}
                    except Exception as e:
                        F_Clear_User_State(p_id)
                        MD_Logs.F_Add_Logs("ERROR", "F_Handle_Command_GetMarket_State", e)
                        return {"user_id": p_id, "user_name": p_name, "command": p_cmd, "message": "An error occurred while reading market information.", "buttons": []}
                else: F_Clear_User_State(p_id)
        except Exception: pass

        try:
            cmd_key = (p_cmd.split() or [""])[0]
            match cmd_key:
                case "/start":  msg = f"Hello {p_name}! I hope you are well."
                case "/help":   msg = "For help, developer information: @beydahsaglam\nhttps://beydahsaglam.com/contact"
                case "/menu": 
                    msg = "You can perform the following operations with me.\nMenu 1"
                    buttons = [[
                        ("Start Bot", "/botstart"), ("Stop Bot", "/botstop"), ("Bot Status", "/botstatus"),
                        ("Set Balance", "/setbalance"), ("Set Leverage", "/setleverage"), ("Set Margin Type", "/settype"),
                        ("Get Alerts", "/getalert"), ("Get Positions", "/getpos"), ("Get Wallet", "/getwallet"),
                        ("Other Operations", "/menu2")
                        ]]

                case "/menu2": 
                    msg = "You can perform the following operations with me.\nMenu 2"
                    buttons = [[
                        ("Webhook", "/gethook"), ("Messages", "/getalertmessage"), ("Settings", "/getsettings"),
                        ("Set API", "/setapi"), ("Get Market", "/getmarket"), ("Get Logs", "/getlog"),
                        ("Go Back", "/menu")
                        ]]

                case "/botstatus": msg = "Bot is running." if SR_TradingView.Bot_Status else "Bot is not running."
                case "/botstart": 
                    if SR_TradingView.Bot_Status: msg = "Bot is already running."
                    else: 
                        msg = "Bot started."
                        SR_TradingView.Bot_Stop = False
                        bot = LB_Thread.Thread(target=SR_TradingView.F_Tradingview_Business, daemon=True)
                        bot.start()
                        
                case "/botstop": 
                    if not SR_TradingView.Bot_Status: msg = "Bot is already stopped."
                    else: 
                        msg = "Bot stopped."
                        SR_TradingView.Bot_Stop = True

                case "/setbalance":
                    old_val = settings.get('order_balance')
                    F_Set_User_State(p_id, "await_setbalance")
                    return {"user_id": p_id, "user_name": p_name, "command": p_cmd, "message": f"Enter New Balance Percentage (%{old_val})\nExit: /exit", "buttons": []}
                
                case "/setleverage":
                    old_val = settings.get('order_leverage')
                    F_Set_User_State(p_id, "await_setleverage")
                    return {"user_id": p_id, "user_name": p_name, "command": p_cmd, "message": f"Enter New Leverage ({old_val}x)\nExit: /exit", "buttons": []}
                
                case "/settype":
                    old_val = settings.get('margin_type')
                    F_Set_User_State(p_id, "await_settype")
                    return {"user_id": p_id, "user_name": p_name, "command": p_cmd, "message": f"Enter New Margin Type (current: {old_val}) [isolated/crossed]\nExit: /exit", "buttons": []}

                case "/getalert":
                    try:
                        alerts = MD_Alerts.F_Get_Alerts().get('alerts', [])
                        if not alerts: msg = "No active alerts found."
                        else:
                            multi_msgs = []
                            multi_msgs.append("Alerts:")
                            for a in alerts:
                                dt = a.get('datetime', '')
                                sym = str(a.get('symbol', '')).upper()
                                typ = a.get('type', '')
                                price = a.get('price', '0')
                                que = a.get('que', '')
                                multi_msgs.append(f"{dt} | {sym} {typ} | Price: {price} | Que: {que}")
                            multi_msgs.append("All alerts have been listed.")
                            return {"user_id": p_id, "user_name": p_name, "command": p_cmd, "buttons": buttons, "multi": multi_msgs}
                    except Exception as e:
                        MD_Logs.F_Add_Logs("ERROR", "F_Handle_Command_Get_Alerts", e)
                        msg = "An error occurred while reading alerts."

                case "/getpos":
                    try:
                        positions = SR_Binance.F_Get_Orders()
                        if not positions: msg = "No open positions found."
                        else:
                            multi_msgs = []
                            multi_msgs.append("Open Positions:")
                            for p in positions:
                                sym = p.get('symbol', '')
                                side = p.get('side', '')
                                qty = p.get('quantity', 0)
                                entry = p.get('entry_price', '0')
                                pnl = p.get('unrealized_pnl', '0')
                                multi_msgs.append(f"{sym} {side} | Entry: {entry} | QTY: {qty} | PNL: {float(pnl):.2f}")
                            multi_msgs.append("All open positions have been listed.")
                            return {"user_id": p_id, "user_name": p_name, "command": p_cmd, "buttons": buttons, "multi": multi_msgs}
                    except Exception as e:
                        MD_Logs.F_Add_Logs("ERROR", "F_Handle_Command_Get_Positions", e)
                        msg = "An error occurred while reading positions."

                case "/getwallet":
                    try:
                        balances = SR_Binance.F_Get_Wallet_Info()
                        if not balances: msg = "Could not retrieve wallet information."
                        else:
                            multi_msgs = []
                            multi_msgs.append("Wallet:")
                            for b in balances:
                                asset = b.get('asset', '')
                                bal = b.get('balance', '0')
                                wait_bal = b.get('wait_balance') or b.get('locked') or '0'
                                multi_msgs.append(f"{asset}: {bal} (Locked: {float(wait_bal):.2f} USD)")
                            multi_msgs.append("All Futures Wallet has been sent")
                            return {"user_id": p_id, "user_name": p_name, "command": p_cmd, "buttons": buttons, "multi": multi_msgs}
                    except Exception as e:
                        MD_Logs.F_Add_Logs("ERROR", "F_Handle_Command_Get_Wallet", e)
                        msg = "An error occurred while reading the wallet."

                case "/gethook": msg = f"Webhook:\nhttps://{settings.get('webhook_domain')}/webhook"
                case "/getalertmessage": 
                    msg = "Alert Texts:\n"
                    msg += f"Long Open:\n{settings.get('alert_long_open')}\n\n"
                    msg += f"Long Close:\n{settings.get('alert_long_close')}\n\n"
                    msg += f"Short Open:\n{settings.get('alert_short_open')}\n\n"
                    msg += f"Short Close:\n{settings.get('alert_short_close')}\n"
                    
                case "/getsettings": 
                    msg = "Settings:\n"
                    msg += f"Balance: %{settings.get('order_balance')}\n"
                    msg += f"Leverage: {settings.get('order_leverage')}x\n"
                    msg += f"Margin Type: {settings.get('margin_type')}\n"

                case "/setapi":
                    F_Set_User_State(p_id, "await_setapi")
                    return {"user_id": p_id, "user_name": p_name, "command": p_cmd, "message": "Please send your API and SECRET information:\nAPI_KEY\nSECRET_KEY\nExit: /exit", "buttons": []}
                
                case "/getmarket":
                    F_Set_User_State(p_id, "await_getmarket")
                    return {"user_id": p_id, "user_name": p_name, "command": p_cmd, "message": "Enter symbol for market information (e.g., BTCUSDT)\nExit: /exit", "buttons": []}
                
                case "/getlog":
                    try:
                        logs = MD_Logs.F_Get_Logs(p_limit=100).get('logs', [])
                        db_dir = LB_OS.path.join(LB_OS.path.dirname(__file__), '..', 'e_database')
                        LB_OS.makedirs(db_dir, exist_ok=True)
                        file_path = LB_OS.path.normpath(LB_OS.path.join(db_dir, 'log.txt'))
                        with open(file_path, 'w', encoding='utf-8') as f:
                            for l in logs:
                                f.write(f"{l.get('datetime','')} [{l.get('type','').upper()}] {l.get('func','')}: {l.get('desc','')}\n")
                        return {
                            "user_id": p_id, 
                            "user_name": p_name, 
                            "command": p_cmd, 
                            "message": f"The last 100 logs are in the file, {p_name}.",
                            "buttons": buttons,
                            "document": file_path
                            }
                    except Exception as e:
                        MD_Logs.F_Add_Logs("ERROR", "F_Handle_Command_Get_Log", e)
                        msg = "An error occurred while preparing the logs."

                case _: pass

            if msg != f"I didn't understand what you said, {p_name}.": 
                final_msg = (cancel_note + msg) if cancel_note else msg
                return {"user_id": p_id, "user_name": p_name, "command": p_cmd, "message": final_msg, "buttons": buttons}

        except Exception: pass
        return {"user_id": p_id, "user_name": p_name, "command": p_cmd, "message": msg, "buttons": buttons}
    except Exception as e:
        MD_Logs.F_Add_Logs("ERROR", "F_Handle_Command", e)
        return {}

def F_Transaction_Business(p_id: str, p_name: str, p_cmd: str) -> bool:
    # DESC: Manages the transaction flow (ensures relevant functions run after a command)
    try:
        response = F_Handle_Command(p_id, p_name, p_cmd)
        if not response: return False
                
        if response.get("multi"):
            multi_list = list(response.get("multi") or [])
            if len(multi_list) > 1:
                for m in multi_list[:-1]:
                    SR_Telegram.F_Send_Message(str(m))
            if multi_list:
                last_text = str(multi_list[-1])
                main_msg = str(response.get("message") or "")
                combined_msg = (last_text if not main_msg else f"{last_text}\n\n{main_msg}")
                if response.get("buttons"):
                    SR_Telegram.F_Send_Button(combined_msg, response["buttons"])
                else:
                    SR_Telegram.F_Send_Message(combined_msg)

        elif response.get("document"):
            doc_path = response["document"]
            if SR_Telegram.F_Send_Document(doc_path, response["message"]):
                try:
                    if LB_OS.path.exists(doc_path): LB_OS.remove(doc_path)
                except Exception as e: MD_Logs.F_Add_Logs("ERROR", "F_Transaction_Business_Delete_Log", e)

        elif response.get("buttons"): SR_Telegram.F_Send_Button(response["message"], response["buttons"])
        else: SR_Telegram.F_Send_Message(response["message"])
        return True
    except Exception as e: return not MD_Logs.F_Add_Logs("ERROR", "F_Transaction_Business", e)

# endregion
