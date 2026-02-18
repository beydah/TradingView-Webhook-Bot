import threading
import time
import sys
import os
import uvicorn
from fastapi import FastAPI
from contextlib import asynccontextmanager

# Ensure app module is in path
sys.path.append(os.getcwd())

from app.core import logging
from app.core.config import settings
from app.services import telegram_service
from app.api import webhook
from app.core import state

# Initialize Logging
logging.setup_logging()
logger = logging.logger

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("=======================================")
    logger.info("= Bot Starting...                     =")
    logger.info("=======================================")
    state.bot_running = True
    
    # Start Telegram Service Thread
    telegram_thread = threading.Thread(target=telegram_service.run_telegram_service, daemon=True)
    telegram_thread.start()
    logger.info("[Main] Telegram Service Started")
    
    yield
    
    # Shutdown
    logger.info("[Main] Stopping...")
    state.bot_running = False

# FastAPI App
app = FastAPI(
    title="TradingView Webhook Bot",
    version="2.0.0",
    lifespan=lifespan
)

# Include Routers
app.include_router(webhook.router)

def main():
    # Use uvicorn to run the app
    # Host 0.0.0.0 is better for Docker/remote access
    import uvicorn
    uvicorn.run(app, host=settings.WEBHOOK_IP, port=settings.WEBHOOK_PORT)

if __name__ == "__main__":
    main()
