import time
import requests
import threading
from telebot import TeleBot
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from app.core.config import settings
from app.core.logging import logger
from app.core import state

# Constants
DELAY_RETRY = 1.0
WAIT_TIME = 10
MAX_RETRY = 5

class TelegramService:
    _session = None
    _bot = None
    
    @classmethod
    def get_session(cls):
        if cls._session is None:
            retry_strategy = Retry(
                total=MAX_RETRY,
                status_forcelist=[429, 500, 502, 503, 504],
                allowed_methods=["HEAD", "GET", "OPTIONS", "POST"],
                backoff_factor=DELAY_RETRY
            )
            adapter = HTTPAdapter(max_retries=retry_strategy)
            cls._session = requests.Session()
            cls._session.mount("http://", adapter)
            cls._session.mount("https://", adapter)
        return cls._session

def handle_update(updates):
    from app.services import transaction_service
    try:
        for update in updates:
            if hasattr(update, 'from_user') and hasattr(update, 'chat'):
                msg = update
                user_id = str(msg.from_user.id)
                
                # Check text messages
                if hasattr(msg, 'text') and msg.text:
                    text = msg.text.strip()
                    
                    if text.startswith('/ping'):
                        try:
                            TelegramService.get_session().post(
                                url=f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage",
                                json={"chat_id": msg.chat.id, "text": "pong", "parse_mode": "HTML"},
                                timeout=WAIT_TIME
                            )
                        except Exception as e:
                            logger.error(f"[handle_update] Ping Error: {e}")
                        continue

                    if user_id != settings.TELEGRAM_USER_ID:
                        logger.warning(f"Unauthorized access attempt from {user_id}")
                        continue
                        
                    transaction_service.process_transaction(user_id, msg.from_user.first_name, text)

            # Check callback queries (buttons)
            elif hasattr(update, 'data') and hasattr(update, 'id') and hasattr(update, 'from_user'):
                cmd = update
                user_id = str(cmd.from_user.id)
                
                if user_id != settings.TELEGRAM_USER_ID:
                    continue
                    
                data = cmd.data
                transaction_service.process_transaction(user_id, cmd.from_user.first_name, data)
                
                # Acknowledge callback to stop loading animation
                try:
                    TelegramService.get_session().post(
                        url=f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/answerCallbackQuery",
                        json={"callback_query_id": cmd.id, "text": "Done"},
                        timeout=WAIT_TIME
                    )
                except Exception:
                    pass

    except Exception as e:
        logger.error(f"[handle_update] Error: {e}")

_connect_lock = False

def start_telegram_bot():
    global _connect_lock
    if _connect_lock:
        return
        
    try:
        _connect_lock = True
        logger.info("Starting Telegram Bot...")
        bot = TeleBot(settings.TELEGRAM_BOT_TOKEN)
        
        try:
            bot.remove_webhook()
        except Exception:
            pass

        @bot.message_handler(func=lambda m: True)
        def _handle_message(m):
            handle_update([m])

        @bot.callback_query_handler(func=lambda c: True)
        def _handle_callback(c):
            handle_update([c])
            
        bot.polling(non_stop=True, timeout=60, long_polling_timeout=60)
        
    except Exception as e:
        _connect_lock = False
        logger.error(f"[start_telegram_bot] Error: {e}")
        time.sleep(WAIT_TIME)

def send_buttons(message: str, buttons: list) -> bool:
    try:
        flat_buttons = []
        for button_row in buttons:
            for button_data in button_row:
                if len(button_data) == 2:
                    flat_buttons.append(button_data)

        keyboard = []
        # Group by 3
        for i in range(0, len(flat_buttons), 3):
            row = []
            for text, callback_data in flat_buttons[i:i+3]:
                row.append({"text": text, "callback_data": callback_data})
            keyboard.append(row)

        response = TelegramService.get_session().post(
            url=f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage",
            json={
                "chat_id": settings.TELEGRAM_USER_ID,
                "text": message,
                "reply_markup": {"inline_keyboard": keyboard},
                "parse_mode": "HTML"
            },
            timeout=WAIT_TIME
        )
        return response.status_code == 200
    except Exception as e:
        logger.error(f"[send_buttons] Error: {e}")
        return False

def send_message(message: str) -> bool:
    try:
        response = TelegramService.get_session().post(
            url=f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage",
            json={
                "chat_id": settings.TELEGRAM_USER_ID,
                "text": message,
                "parse_mode": "HTML"
            },
            timeout=WAIT_TIME
        )
        return response.status_code == 200
    except Exception as e:
        logger.error(f"[send_message] Error: {e}")
        return False

def run_telegram_service():
    """
    Main loop for Telegram service.
    """
    while True:
        try:
            start_telegram_bot()
            time.sleep(WAIT_TIME)
        except Exception as e:
             logger.error(f"[run_telegram_service] Crash: {e}")
             time.sleep(WAIT_TIME)
