from app.core.config import settings

def F_Get_Settings(p_key: str = None) -> dict:
    """
    Adapter function to get settings from the new Pydantic config.
    Maintains compatibility with the old dictionary-based access.
    """
    # Create the dictionary structure expected by legacy code
    config_dict = {
        "binance_api": settings.BINANCE_API_KEY,
        "binance_secret": settings.BINANCE_SECRET_KEY,
        "telegram_bot_token": settings.TELEGRAM_BOT_TOKEN,
        "telegram_user_id": settings.TELEGRAM_USER_ID,
        "webhook_ip": settings.WEBHOOK_IP,
        "webhook_port": str(settings.WEBHOOK_PORT),
        "webhook_domain": settings.WEBHOOK_DOMAIN,
        "alert_key": settings.ALERT_KEY,
        "alert_long_open": settings.ALERT_LONG_OPEN,
        "alert_long_close": settings.ALERT_LONG_CLOSE,
        "alert_short_open": settings.ALERT_SHORT_OPEN,
        "alert_short_close": settings.ALERT_SHORT_CLOSE,
        "order_balance": str(settings.ORDER_BALANCE_PERCENT),
        "order_leverage": str(settings.ORDER_LEVERAGE),
        "margin_type": settings.MARGIN_TYPE
    }

    if p_key:
        return {p_key: config_dict.get(p_key)}
    return config_dict

def F_Update_Settings(p_key: str, p_val: str) -> bool:
    """
    Deprecated: Settings are now immutable via .env
    """
    return False

def F_Add_Settings(p_key: str, p_val: str) -> bool:
    """
    Deprecated
    """
    return False

def F_Del_Settings(p_key: str) -> bool:
    """
    Deprecated
    """
    return False