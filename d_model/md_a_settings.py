# region ===== INFO ===================================================================================================

# Developer : Ilkay Beydah Saglam
# Website   : https://beydahsaglam.com
# Created   : 2025-08-21
# Version   : Python 3.10

# DESC:
#   This script manages the necessary settings for the application. 
#   It is designed to handle operations such as finding, creating, reading, 
#   and updating the settings file through a standard structure.
#
# FEATURES:
#   - Determining and accessing the settings file path
#   - Creating the settings file if it cannot be found
#   - Reading and fetching settings (optionally key-based)
#   - Adding new settings
#   - Updating existing settings

# endregion
# region ===== LIBRARY ================================================================================================

import json as  LB_JSON
import os as    LB_OS

# endregion
# region ===== VARIABLE ===============================================================================================

FILE_PATH: str = LB_OS.path.join(LB_OS.path.dirname(__file__), '..', 'e_database', 'db_a_settings.json')

# endregion
# region ===== OBJECT =================================================================================================

# endregion
# region ===== FUNCTION ===============================================================================================

def F_Create_Settings() -> dict:
    # DESC: If the settings file does not exist, it creates it and returns the default values
    # RETURN: dict - Default settings structure
    default: dict = {
        "settings": [
            {
                "binance_api": "YOUR_TEST_KEY_OR_BINANCE_KEY",
                "binance_secret": "YOUR_TEST_SECRET_OR_BINANCE_SECRET",
                "telegram_bot_token": "YOUR_TELEGRAM_BOT_TOKEN",
                "telegram_user_id": "YOUR_TELEGRAM_USER_ID",
                "webhook_ip": "127.0.0.1",
                "webhook_port": "5001",
                "webhook_domain": "YOUR_DOMAIN",
                "alert_key": "CREATE_BOT_KEY_EXAMPLE=bot24_3M1RMHM7",
                "alert_long_open": "{\"symbol\": \"{{ticker}}\", \"alert\": \"long_open\",  \"price\": \"{{close}}\", \"key\": \"CREATE_BOT_KEY_EXAMPLE=bot24_3M1RMHM7\"}",
                "alert_long_close": "{\"symbol\": \"{{ticker}}\", \"alert\": \"long_close\", \"price\": \"{{close}}\", \"key\": \"CREATE_BOT_KEY_EXAMPLE=bot24_3M1RMHM7\"}",
                "alert_short_open": "{\"symbol\": \"{{ticker}}\", \"alert\": \"short_open\", \"price\": \"{{close}}\", \"key\": \"CREATE_BOT_KEY_EXAMPLE=bot24_3M1RMHM7\"}",
                "alert_short_close": "{\"symbol\": \"{{ticker}}\", \"alert\": \"short_close\", \"price\": \"{{close}}\", \"key\": \"CREATE_BOT_KEY_EXAMPLE=bot24_3M1RMHM7\"}",
                "order_balance": "100",
                "order_leverage": "2",
                "margin_type": "isolated"
            }
        ]
    }

    try:
        if not LB_OS.path.exists(FILE_PATH):
            LB_OS.makedirs(LB_OS.path.dirname(FILE_PATH), exist_ok=True)
            with open(FILE_PATH, 'w', encoding='utf-8') as f:  LB_JSON.dump(default, f, indent=4, ensure_ascii=False)
            return default

        with open(FILE_PATH, 'r', encoding='utf-8') as f: return LB_JSON.load(f)
    except Exception: return default

def F_Get_Settings(p_key: str = None) -> dict:
    # DESC: Fetches the settings
    # PARAMS:
    #   p_key: The desired setting key (if None, all settings)
    # RETURN: dict - The desired setting or all settings
    try:
        settings_data: dict = F_Create_Settings()
        settings_list       = settings_data.get('settings', [])
        if not settings_list or not isinstance(settings_list, list) or not settings_list[0]: return {}
        current_settings = settings_list[0]
        if p_key: return {p_key: current_settings.get(p_key)} if p_key in current_settings else {}
        return current_settings
    except Exception: return {}

def F_Add_Settings(p_key: str, p_val: str) -> bool:
    # DESC: Adds a new setting
    # PARAMS:
    #   p_key: The key of the setting to be added
    #   p_val: The value of the setting to be added
    # RETURN: bool - Was the operation successful?
    try:
        settings_data: dict = F_Create_Settings()
        settings            = settings_data.get('settings', [{}])
        if not settings or not isinstance(settings[0], dict): settings = [{}]
        if p_key in settings[0]: return False
        settings[0][p_key] = p_val
        with open(FILE_PATH, 'w', encoding='utf-8') as f: 
            LB_JSON.dump({"settings": settings}, f, indent=4, ensure_ascii=False)

        return True
    except Exception: return False

def F_Update_Settings(p_key: str, p_val: str) -> bool:
    # DESC: Updates an existing setting
    # PARAMS:
    #   p_key: The key of the setting to be updated
    #   p_val: The new value for the setting
    # RETURN: bool - Was the operation successful?
    try:
        settings_data: dict = F_Create_Settings()
        settings            = settings_data.get('settings', [{}])
        if not settings or not isinstance(settings[0], dict) or p_key not in settings[0]: return False
        settings[0][p_key] = p_val
        with open(FILE_PATH, 'w', encoding='utf-8') as f: 
            LB_JSON.dump({"settings": settings}, f, indent=4, ensure_ascii=False)

        return True
    except Exception: return False

def F_Del_Settings(p_key: str) -> bool:
    # DESC: Deletes a setting
    # PARAMS:
    #   p_key: The key of the setting to be deleted
    # RETURN: bool - Was the operation successful?
    try:
        settings_data: dict = F_Create_Settings()
        settings            = settings_data.get('settings', [{}])
        if not settings or not isinstance(settings[0], dict) or p_key not in settings[0]: return False
        del settings[0][p_key]
        with open(FILE_PATH, 'w', encoding='utf-8') as f:
            LB_JSON.dump({"settings": settings}, f, indent=4, ensure_ascii=False)

        return True
    except Exception: return False

# endregion