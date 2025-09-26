# region ===== INFO ===================================================================================================

# Developer : Ilkay Beydah Saglam
# Website   : https://beydahsaglam.com
# Created   : 2025-08-21
# Version   : Python 3.10

# DESC:
#   This script provides a simple JSON-based log management system.
#   It stores error, warning, info, and transaction logs created throughout the application
#   in a single file, fetching or deleting them with filters when necessary.
#   This facilitates traceability and error management across the project.
#
# FEATURES:
#   - Automatic creation of the log file on the first run if it does not exist
#   - Add logs (error, alert, transaction, info, warning types)
#   - Fetch logs by filtering according to date, type, and limit parameters
#   - Delete logs of a specified type or limit
#   - Clean up log records older than 30 days
#   - Storage in JSON format (for easy readability and integration)

# endregion
# region ===== LIBRARY ================================================================================================

import json as      LB_JSON
import os as        LB_OS
import datetime as  LB_Date
import time as      LB_Time

# endregion
# region ===== VARIABLE ===============================================================================================

FILE_PATH: str = LB_OS.path.join(LB_OS.path.dirname(__file__), '..', 'e_database', 'db_e_logs.json')
WAIT_TIME: int = 10

# endregion
# region ===== OBJECT =================================================================================================

# endregion
# region ===== FUNCTION ===============================================================================================

def F_Create_Logs() -> dict:
    # DESC: If the log file does not exist, it creates it and returns the default values
    # RETURN: dict - Default log structure
    default: dict = {
        "logs": [
            {
                "datetime": LB_Date.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "type":     "transaction",
                "func":     "F_Create_Logs",
                "desc":     "Log system has been initialized with default values."
            }
        ]
    }

    try:
        if not LB_OS.path.exists(FILE_PATH):
            LB_OS.makedirs(LB_OS.path.dirname(FILE_PATH), exist_ok=True)
            with open(FILE_PATH, 'w', encoding='utf-8') as f: LB_JSON.dump(default, f, indent=4, ensure_ascii=False)
            return default

        with open(FILE_PATH, 'r', encoding='utf-8') as f: return LB_JSON.load(f)
    except Exception: return default

def F_Get_Logs(p_date: str = None, p_type: str = None, p_limit: int = None) -> dict:
    # DESC: Fetches logs with filtering
    # PARAMS:
    #   p_date: Date filter (in YYYY-MM-DD format)
    #   p_type: Log type filter (e.g., 'error', 'alert', 'transaction')
    #   p_limit: Maximum number of logs to return
    # RETURN: dict - Filtered log list
    try:
        F_Del_Logs_Old()
        logs_data: dict = F_Create_Logs()
        logs            = logs_data.get('logs', [])
        filtered_logs   = []
        for log in logs:
            log_date = log.get('datetime', '').split(' ')[0]  # Get only the date part
            if p_date and not log_date.startswith(p_date):                  continue
            if p_type and log.get('type', '').lower() != p_type.lower():    continue
            filtered_logs.append(log)
        
        filtered_logs.sort(key=lambda x: x.get('datetime', ''), reverse=True)
        if p_limit and p_limit > 0: filtered_logs = filtered_logs[:p_limit]
        return {"logs": filtered_logs}
    except Exception: return {"logs": []}

def F_Add_Logs(p_type: str, p_func: str, p_desc) -> bool:
    # DESC: Adds a new log
    # PARAMS:
    #   p_type: Log type (error, alert, transaction)
    #   p_func: Name of the function where the log was created
    #   p_desc: Log description
    # RETURN: bool - Was the operation successful?
    new_log = {
        "datetime": LB_Date.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "type":     p_type.lower(),
        "func":     p_func,
        "desc":     str(p_desc)
    }
    if p_type.lower() == "error": LB_Time.sleep(1)
    try:
        logs_data: dict = F_Create_Logs()
        logs            = logs_data.get('logs', [])
        logs.insert(0, new_log)
        with open(FILE_PATH, 'w', encoding='utf-8') as f: LB_JSON.dump({"logs": logs}, f, indent=4, ensure_ascii=False)
        return True
    except Exception: return False

def F_Del_Logs(p_type: str = None, p_limit: int = None) -> bool:
    # DESC: Deletes logs according to the specified criteria
    # PARAMS:
    #   p_type: Type of log to delete (if None, all types)
    #   p_limit: Number of logs to delete (if None, all matching)
    # RETURN: bool - Was the operation successful?
    try:
        logs_data: dict = F_Create_Logs()
        logs            = logs_data.get('logs', [])
        if not logs: return True
        if p_type is None and p_limit is None: logs_data['logs'] = []
        else:
            filtered_logs   = []
            deleted_logs    = []
            for log in logs:
                if (p_type and log.get('type', '').lower()      != p_type.lower()) or \
                   (p_limit is not None and len(deleted_logs)   >= p_limit):
                    filtered_logs.append(log)

                else: deleted_logs.append(log)

            logs_data['logs'] = filtered_logs
        with open(FILE_PATH, 'w', encoding='utf-8') as f: LB_JSON.dump(logs_data, f, indent=4, ensure_ascii=False)
        return True
    except Exception: return False

def F_Del_Logs_Old() -> bool:
    # DESC: Deletes logs older than 30 days
    # RETURN: bool - Was the operation successful?
    try:
        now             = LB_Date.datetime.now()
        threshold_date  = now - LB_Date.timedelta(days=30)
        logs_data: dict = F_Create_Logs()
        logs            = logs_data.get('logs', [])
        if not logs: return True
        filtered_logs = []
        deleted_count = 0
        for log in logs:
            try:
                log_date_str: str   = log.get('datetime', '')
                log_date            = LB_Date.datetime.strptime(log_date_str, "%Y-%m-%d %H:%M:%S")
                if log_date >= threshold_date: filtered_logs.append(log)
                else: deleted_count += 1
            except Exception: filtered_logs.append(log)
        
        if deleted_count > 0:
            logs_data['logs'] = filtered_logs
            with open(FILE_PATH, 'w', encoding='utf-8') as f: LB_JSON.dump(logs_data, f, indent=4, ensure_ascii=False)

        return True
    except Exception: return False

# endregion