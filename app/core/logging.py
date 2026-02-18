import logging
import os
from logging.handlers import RotatingFileHandler
from datetime import datetime

# Ensure logs directory exists
LOG_DIR = os.path.join(os.getcwd(), 'logs')
os.makedirs(LOG_DIR, exist_ok=True)

def setup_logging():
    """
    Configures the logging system.
    """
    log_filename = datetime.now().strftime("%Y-%m-%d") + ".log"
    log_filepath = os.path.join(LOG_DIR, log_filename)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            RotatingFileHandler(log_filepath, maxBytes=5*1024*1024, backupCount=5, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    
    # Set levels for third-party libs
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("werkzeug").setLevel(logging.WARNING)

logger = logging.getLogger("TradingViewBot")
