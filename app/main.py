import threading
import time
import sys
import os

# Ensure app module is in path
sys.path.append(os.getcwd())

from app.core import logging
from app.core.config import settings
from app.services import telegram_service
from app.services import tradingview_service
from app.core import state

# Initialize Logging
logging.setup_logging()
logger = logging.logger

def main():
    logger.info("=======================================")
    logger.info("= Bot Starting...                     =")
    logger.info("=======================================")

    try:
        # Start Telegram Service Thread
        telegram_thread = threading.Thread(target=telegram_service.run_telegram_service, daemon=True)
        telegram_thread.start()
        logger.info("[Main] Telegram Service Started")

        # Start TradingView Service (and Webhook Server) Thread (via its loop manager)
        # Note: tradingview_service.start_bot_thread() starts the webhook server thread.
        # run_tradingview_service() monitors it.
        # Original logic had TWO threads started in main: one for Telegram, one for TradingView.
        # TradingView logic started its own threads internally too.
        
        # We start the TradingView monitor loop in a thread
        tv_thread = threading.Thread(target=tradingview_service.run_tradingview_service, daemon=True)
        tv_thread.start()
        logger.info("[Main] TradingView Service Started")
        
        # Keep main thread alive
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        logger.info("[Main] Stopping...")
        state.bot_running = False
        sys.exit(0)
    except Exception as e:
        logger.error(f"[Main] Critical Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
