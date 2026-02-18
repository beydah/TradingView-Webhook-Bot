from app.core import logging as core_logging

# Initialize logging
core_logging.setup_logging()
logger = core_logging.logger

def F_Add_Logs(p_type: str, p_func: str, p_desc) -> bool:
    """
    Adapter function to log messages using standard logger.
    """
    try:
        msg = f"[{p_func}] {str(p_desc)}"
        level = p_type.lower()
        
        if level == "error":
            logger.error(msg)
        elif level == "warning":
            logger.warning(msg)
        elif level == "info":
            logger.info(msg)
        elif level == "transaction":
            logger.info(f"[TRANSACTION] {msg}")
        else:
            logger.debug(msg)
            
        return True
    except Exception:
        return False

def F_Get_Logs(p_date: str = None, p_type: str = None, p_limit: int = None) -> dict:
    """
    Deprecated: Logs are now in standard log files.
    Returning empty list to avoid breaking legacy calls immediately if any exists.
    """
    return {"logs": []}

def F_Del_Logs(p_type: str = None, p_limit: int = None) -> bool:
    return True

def F_Del_Logs_Old() -> bool:
    return True