import logging
import os
from logging.handlers import RotatingFileHandler
import sys
import threading

# Ensure logs directory exists
LOG_DIR = os.path.join(os.getcwd(), 'logs')
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, 'bot.log')

# Custom Handler for SQLite
# We import crud/db lazily or inside emit to avoid circular imports during setup?
# Usually logging setup happens early. DB setup happens early too.
# But `logging.py` is in `app/core`. `database.py` is in `app/core`.
# Checks circular dependency: logging -> database -> config. Safe.
# logging -> crud -> models -> database. Safe.

class DBHandler(logging.Handler):
    def emit(self, record):
        # Run in a separate thread to avoid blocking main execution? 
        # Or just write synchronously. SQLite is fast enough for low volume logs.
        # But if lock is held, it might block.
        # For safety/performance, maybe simple print if DB fails.
        try:
            from app.core.database import SessionLocal
            from app.core import crud
            
            # Map log level to "type"
            log_type = record.levelname.lower()
            
            # Use funcName or name
            func_name = record.funcName
            if func_name == '<module>':
                func_name = record.name
                
            msg = self.format(record)
            
            # We don't want to crash if DB write fails
            try:
                db = SessionLocal()
                crud.create_log(db, log_type, func_name, msg)
                db.close()
            except Exception:
                pass # Fail silently for logging
                
        except Exception:
            self.handleError(record)

logger = logging.getLogger("TradingViewBot")
logger.setLevel(logging.INFO)

def setup_logging():
    """
    Configures the logging system.
    """
    # File Handler
    file_handler = RotatingFileHandler(LOG_FILE, maxBytes=5*1024*1024, backupCount=5, encoding='utf-8')
    file_handler.setLevel(logging.INFO)
    file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(file_formatter)

    # Console Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(console_formatter)
    
    # DB Handler (Only for Warnings/Errors? or Info too?)
    # Legacy logged everything? MD_Logs.F_Add_Logs was called manually.
    # We'll log INFO+ to DB to match legacy "audit trail" likely.
    # But standard logging can be chatty.
    # Let's log WARNING and above to DB, plus specific INFOs if needed?
    # User /getlog shows "logs". Legacy manually added "ERROR" and "INFO".
    # We will log INFO+.
    db_handler = DBHandler()
    db_handler.setLevel(logging.INFO) 
    # We don't need formatter for DB, as we store separate fields, but emit uses format() for 'desc'
    # So we set a simple message formatter
    db_formatter = logging.Formatter('%(message)s')
    db_handler.setFormatter(db_formatter)

    if not logger.handlers:
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        logger.addHandler(db_handler)
    
    # Set levels for third-party libs
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("werkzeug").setLevel(logging.WARNING)
