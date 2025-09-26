# region ===== INFO ===================================================================================================

# Developer : Ilkay Beydah Saglam
# Website   : https://beydahsaglam.com
# Created   : 2025-08-21
# Version   : Python 3.10

# DESC:
#   This module is designed to interact with the Telegram bot.
#   The functions cover receiving, sending, editing, deleting messages, adding buttons, and callback operations.
#   It also includes validation of incoming messages and error handling.

# FEATURES:
#   - Receiving and parsing Telegram messages
#   - Managing callback and button interactions
#   - Sending, editing, and deleting messages
#   - Sending documents or files
#   - Sending error messages and user notifications
#   - Message request security validation

# endregion
# region ===== LIBRARY ================================================================================================

from c_service import sr_d_transaction as   SR_Transaction

from d_model import md_a_settings as    MD_Settings
from d_model import md_e_logs as        MD_Logs

import time as                                  LB_Time
import threading as                             LB_Thread
import requests as                              LB_Request
from telebot import TeleBot as                  LB_Telebot
from requests.adapters import HTTPAdapter as    LB_HTTP
from urllib3.util.retry import Retry as         LB_Try

# endregion
# region ===== VARIABLE ===============================================================================================

DELAY_RETRY: float  = 1.0
WAIT_TIME: int      = 10
MAX_RETRY: int      = 5
SETTINGS: dict      = MD_Settings.F_Get_Settings()
BOT_TOKEN: str      = SETTINGS.get('telegram_bot_token')
USER_ID: str        = SETTINGS.get('telegram_user_id')

Lock_Connect_Hook: bool = False

# endregion
# region ===== OBJECT =================================================================================================

Retry_Strategy = LB_Try(
    total               = MAX_RETRY,
    status_forcelist    = [429, 500, 502, 503, 504],
    allowed_methods     = ["HEAD", "GET", "OPTIONS", "POST"],
    backoff_factor      = DELAY_RETRY
)

O_Session = LB_Request.Session()
O_Adapter = LB_HTTP(max_retries=Retry_Strategy)
O_Session.mount("http://", O_Adapter)
O_Session.mount("https://", O_Adapter)

# endregion
# region ===== FUNCTION ===============================================================================================

def F_Handle_Update(p_updates):
    # DESC: Handles all incoming Telegram updates.
    try:
        for update in p_updates:
            if hasattr(update, 'from_user') and hasattr(update, 'chat') and hasattr(update, 'message_id'):
                msg     = update
                user_id = str(msg.from_user.id)
                if hasattr(msg, 'text') and msg.text:
                    text = msg.text
                    if text.strip().startswith('/ping'):
                        try:
                            O_Session.post(
                                url=f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                                json={"chat_id": msg.chat.id, "text": "pong", "parse_mode": "HTML"},
                                timeout=WAIT_TIME)
                        except Exception as e: MD_Logs.F_Add_Logs("ERROR", "F_Handle_Update_Ping", e)
                        continue

                    if user_id != USER_ID: continue
                    SR_Transaction.F_Transaction_Business(user_id, msg.from_user.first_name, text)

            elif hasattr(update, 'data') and hasattr(update, 'id') and hasattr(update, 'from_user'):
                cmd = update
                user_id = str(cmd.from_user.id)
                if user_id != USER_ID: continue
                data = cmd.data
                SR_Transaction.F_Transaction_Business(user_id, cmd.from_user.first_name, data)
                O_Session.post(
                    url=f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery",
                    json={"callback_query_id": cmd.id, "text": "Operation Completed"},
                    timeout=WAIT_TIME)
    except Exception as e: MD_Logs.F_Add_Logs("ERROR", "F_Handle_Update", e)

def F_Connect_Telegram() -> bool:
    try:
        global Lock_Connect_Hook
        if Lock_Connect_Hook: return
        Lock_Connect_Hook = True
        bot = LB_Telebot(BOT_TOKEN)
        try: bot.remove_webhook()
        except Exception: pass
        @bot.message_handler(func=lambda m: True)
        def _handle_message(m):
            try: F_Handle_Update([m])
            except Exception as e: MD_Logs.F_Add_Logs("ERROR", "_handle_message", e)

        @bot.callback_query_handler(func=lambda c: True)
        def _handle_callback(c):
            try: F_Handle_Update([c])
            except Exception as e: MD_Logs.F_Add_Logs("ERROR", "_handle_callback", e)

        bot.polling(non_stop=True, timeout=60, long_polling_timeout=60)
    except Exception as e:
        Lock_Connect_Hook = False
        MD_Logs.F_Add_Logs("ERROR", "F_Connect_Telegram", e)

def F_Send_Button(p_message: str, p_buttons: list) -> bool:
    # DESC: Sends a message with buttons. The buttons parameter contains callback data.
    try:
        flat_buttons = []
        for button_row in p_buttons:
            for button_data in button_row:
                if len(button_data) == 2: flat_buttons.append(button_data)

        keyboard = []
        for i in range(0, len(flat_buttons), 3):
            row = []
            for button_text, callback_data in flat_buttons[i:i+3]: 
                row.append({"text": button_text, "callback_data": callback_data})

            keyboard.append(row)

        response = O_Session.post(
            url     = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            json    = {
                "chat_id": USER_ID,
                "text": p_message,
                "reply_markup": {"inline_keyboard": keyboard},
                "parse_mode": "HTML"},
            timeout = WAIT_TIME)
        return response.status_code == 200
    except Exception as e: return not MD_Logs.F_Add_Logs("ERROR", "F_Send_Button", e)

def F_Send_Message(p_message: str) -> bool:
    # DESC: Sends a text message to the specified chat_id.
    try:
        response = O_Session.post(
            url     = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            json    = {"chat_id": USER_ID, "text": p_message, "parse_mode": "HTML"},
            timeout = WAIT_TIME)

        if response.status_code == 200: return True
        else: return False
    except Exception as e: return not MD_Logs.F_Add_Logs("ERROR", "F_Send_Message", e)
   
def F_Send_Document(p_file_path: str, p_caption: str = None) -> bool:
    # DESC: Sends the specified file as a document.
    try:
        with open(p_file_path, 'rb') as f:
            files = {"document": (p_file_path.split('/')[-1].split('\\')[-1], f)}
            data = {"chat_id": USER_ID}
            if p_caption:
                data["caption"] = p_caption
            response = O_Session.post(
                url=f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument",
                data=data,
                files=files,
                timeout=WAIT_TIME)
        return response.status_code == 200
    except Exception as e:
        return not MD_Logs.F_Add_Logs("ERROR", "F_Send_Document", e)
   
def F_Telegram_Business() -> bool:
    # DESC: Runs the bot continuously. In case of an error, it waits for 30 seconds and restarts.
    while True:
        try:
            global Lock_Connect_Hook
            if not Lock_Connect_Hook:
                webhook_thread = LB_Thread.Thread(target=F_Connect_Telegram, daemon=True)
                webhook_thread.start()
            
            LB_Time.sleep(WAIT_TIME)
        except Exception as e: 
            Lock_Connect_Hook = False
            MD_Logs.F_Add_Logs("ERROR", "F_Telegram_Business", e)

# endregion
