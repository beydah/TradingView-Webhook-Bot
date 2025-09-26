# region ===== INFO ===================================================================================================

# Website   : https://beydahsaglam.com
# Created   : 2025-08-21
# Version   : Python 3.10

# DESC:
#   This script provides alarm and alert management for the application.
#   It creates the alarm file if it cannot be found, reads existing alarms, adds new alarms,
#   and updates existing ones. This way, price-based or type-based notifications
#   for symbols are managed through a standard structure.
#
# FEATURES:
#   - Determining and accessing the path of the alarm file
#   - Creating the alarm file if it cannot be found
#   - Reading and fetching existing alarms
#   - Adding new alarms
#   - Updating existing alarms

# endregion
# region ===== LIBRARY ================================================================================================

import json as      LB_JSON
import datetime as  LB_Date
import os as        LB_OS

# endregion
# region ===== VARIABLE ===============================================================================================

FILE_PATH: str = LB_OS.path.join(LB_OS.path.dirname(__file__), '..', 'e_database', 'db_c_alerts.json')

# endregion
# region ===== OBJECT =================================================================================================

# endregion
# region ===== FUNCTION ===============================================================================================

def F_Create_Alerts() -> dict:
    # DESC: If the alarm file does not exist, it creates it and returns the default values.
    # RETURN: dict - Default alarm structure.
    default: dict = {"alerts": []}
    try:
        if not LB_OS.path.exists(FILE_PATH):
            LB_OS.makedirs(LB_OS.path.dirname(FILE_PATH), exist_ok=True)
            with open(FILE_PATH, 'w', encoding='utf-8') as f: LB_JSON.dump(default, f, indent=4, ensure_ascii=False)
            return default
        with open(FILE_PATH, 'r', encoding='utf-8') as f: return LB_JSON.load(f)
    except Exception: return default

def F_Get_Alerts(p_symbol: str = None, p_type: str = None, p_que: bool = None) -> dict:
    # DESC: Fetches alarms with filtering.
    # PARAMS:
    #   p_symbol: Symbol filter (e.g., 'BTCUSDT').
    #   p_type: Alarm type filter (e.g., 'price', 'volume').
    #   p_que: Fetch only active alarms.
    # RETURN: dict - Filtered alarm list.
    try:
        F_Del_Alerts_Old()
        alerts_data : dict  = F_Create_Alerts()
        alerts              = alerts_data.get('alerts', [])
        filtered_alerts     = []
        for alert in alerts:
            if p_symbol and alert.get('symbol', '').lower()             != p_symbol.lower():    continue
            if p_type and alert.get('type', '').lower()                 != p_type.lower():      continue
            if p_que is not None and str(alert.get('que', '')).lower()  != str(p_que).lower():  continue
            filtered_alerts.append(alert)
        
        return {"alerts": filtered_alerts}
    except Exception: return {"alerts": []}

def F_Add_Alerts(p_symbol: str, p_type: str, p_price: float) -> bool:
    # DESC: Adds a new alarm.
    # PARAMS:
    #   p_symbol: Symbol (e.g., 'BTCUSDT').
    #   p_type: Alarm type (e.g., 'price', 'volume').
    #   p_price: Alarm price.
    # RETURN: bool - Was the operation successful?
    try:
        alerts_data: dict   = F_Create_Alerts()
        alerts              = alerts_data.get('alerts', [])
        for alert in alerts:
            if (alert.get('symbol', '').lower()     == p_symbol.lower() and 
                alert.get('type', '').lower()       == p_type.lower() and 
                alert.get('que', 'true').lower()    == 'true'): return False
        
        new_alert = {
            "datetime": LB_Date.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "symbol":   p_symbol.lower(),
            "type":     p_type.lower(),
            "price":    str(p_price),
            "que":      'true'
        }
        
        alerts.append(new_alert)
        with open(FILE_PATH, 'w', encoding='utf-8') as f: LB_JSON.dump({"alerts": alerts}, f, indent=4, ensure_ascii=False)
        return True
    except Exception: return False

def F_Set_Alerts(p_symbol: str, p_type: str = None, p_que: bool = False) -> bool:
    # DESC: Updates the status of the alarms.
    # PARAMS:
    #   p_symbol: Symbol (e.g., 'BTCUSDT').
    #   p_type: Alarm type (optional, if not specified, it applies to all types).
    #   p_que: Activity status (True/False).
    # RETURN: bool - Was the operation successful?
    try:
        alerts_data: dict   = F_Create_Alerts()
        alerts              = alerts_data.get('alerts', [])
        updated: bool       = False
        for alert in alerts:
            if alert.get('symbol', '').lower() == p_symbol.lower():
                if p_type is None or alert.get('type', '').lower() == p_type.lower():
                    alert['que']    = str(p_que).lower()
                    updated         = True
        
        if updated:
            with open(FILE_PATH, 'w', encoding='utf-8') as f: 
                LB_JSON.dump({"alerts": alerts}, f, indent=4, ensure_ascii=False)
        
        return updated
    except Exception: return False

def F_Del_Alerts(p_symbol: str) -> bool:
    # DESC: Deletes all alerts for a given symbol.
    # PARAMS:
    #   p_symbol: Symbol to delete alerts for (e.g., 'BTCUSDT').
    # RETURN: bool - Was the operation successful?
    try:
        alerts_data: dict = F_Create_Alerts()
        alerts            = alerts_data.get('alerts', [])
        if not alerts: return True

        updated_alerts = [alert for alert in alerts if alert.get('symbol', '').lower() != p_symbol.lower()]

        if len(updated_alerts) < len(alerts):
            with open(FILE_PATH, 'w', encoding='utf-8') as f: 
                LB_JSON.dump({"alerts": updated_alerts}, f, indent=4, ensure_ascii=False)
            return True
        return False
    except Exception: return False

def F_Del_Alerts_Old() -> bool:
    # DESC: Deletes alarms older than 30 days.
    # RETURN: bool - Was the operation successful?
    try:
        alerts_data: dict = F_Create_Alerts()
        alerts            = alerts_data.get('alerts', [])
        if not alerts: return True
            
        thirty_days_ago = LB_Date.datetime.now() - LB_Date.timedelta(days=30)
        updated_alerts  = []
        
        for alert in alerts:
            date = alert.get('datetime')
            if not date: continue
                
            try:
                alert_date = LB_Date.datetime.strptime(date, "%Y-%m-%d %H:%M:%S")
                if alert_date >= thirty_days_ago: updated_alerts.append(alert)
            except ValueError: continue
        
        if len(updated_alerts) < len(alerts):
            with open(FILE_PATH, 'w', encoding='utf-8') as f: 
                LB_JSON.dump({"alerts": updated_alerts}, f, indent=4, ensure_ascii=False)
                
            return True
        return False
    except Exception: return False

# endregion