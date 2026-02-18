import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # Binance
    BINANCE_API_KEY: str
    BINANCE_SECRET_KEY: str
    
    # Telegram
    TELEGRAM_BOT_TOKEN: str
    TELEGRAM_USER_ID: str

    # Webhook Server
    WEBHOOK_IP: str = "127.0.0.1"
    WEBHOOK_PORT: int = 5001
    WEBHOOK_DOMAIN: str = "localhost"

    # Security
    ALERT_KEY: str

    # Trading Defaults
    ORDER_BALANCE_PERCENT: int = 100
    ORDER_LEVERAGE: int = 2
    MARGIN_TYPE: str = "isolated"

    # Alert payloads (optional, can be defaults)
    ALERT_LONG_OPEN: str = '{"symbol": "{{ticker}}", "alert": "long_open", "price": "{{close}}", "key": "YOUR_KEY"}'
    ALERT_LONG_CLOSE: str = '{"symbol": "{{ticker}}", "alert": "long_close", "price": "{{close}}", "key": "YOUR_KEY"}'
    ALERT_SHORT_OPEN: str = '{"symbol": "{{ticker}}", "alert": "short_open", "price": "{{close}}", "key": "YOUR_KEY"}'
    ALERT_SHORT_CLOSE: str = '{"symbol": "{{ticker}}", "alert": "short_close", "price": "{{close}}", "key": "YOUR_KEY"}'

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

settings = Settings()
