# region ===== INFO ===================================================================================================

# Developer : Ilkay Beydah Saglam
# Website   : https://beydahsaglam.com
# Created   : 2025-08-21
# Version   : Python 3.10

# DESC:
#   This module manages orders for exchange transactions.
#   Orders are stored in a JSON file and support CRUD (Create, Read, Update, Delete) operations.

# FEATURES:
#   - Add, update, and delete orders
#   - Filter and query orders
#   - Open/closed order management
#   - Automatic cleaning of old orders

# endregion
# region ===== LIBRARY ================================================================================================

import json as      LB_JSON
import os as        LB_OS
import datetime as  LB_Date

# endregion
# region ===== VARIABLE ===============================================================================================

FILE_PATH: str = LB_OS.path.join(LB_OS.path.dirname(__file__), '..', 'e_database', 'db_d_orders.json')

# endregion
# region ===== OBJECT =================================================================================================

# endregion
# region ===== FUNCTION ===============================================================================================

def F_Create_Orders() -> dict:
    # DESC: If the order file does not exist, it creates it and returns the default values
    # RETURN: dict - Default order structure
    default: dict = {"orders": []}
    try:
        if not LB_OS.path.exists(FILE_PATH):
            LB_OS.makedirs(LB_OS.path.dirname(FILE_PATH), exist_ok=True)
            with open(FILE_PATH, 'w', encoding='utf-8') as f: LB_JSON.dump(default, f, indent=4, ensure_ascii=False)
            return default
        with open(FILE_PATH, 'r', encoding='utf-8') as f: return LB_JSON.load(f)
    except Exception: return default

def F_Get_Order(p_symbol: str = None, p_side: str = None, p_open: bool = None) -> dict:
    # DESC: Fetches orders with filtering
    # PARAMS:
    #   p_symbol: Symbol filter (e.g., 'BTCUSDT')
    #   p_side: Transaction side filter (e.g., 'long', 'short')
    #   p_open: Fetch only open/closed orders
    # RETURN: dict - Filtered order list
    try:
        F_Del_Orders_Old()
        orders_data: dict   = F_Create_Orders()
        orders              = orders_data.get('orders', [])
        filtered_orders     = []
        for order in orders:
            if p_symbol is not None and order.get('symbol', '').lower() != p_symbol.lower():    continue
            if p_side is not None and order.get('side', '').lower()     != p_side.lower():      continue
            if p_open is not None and order.get('open', '')             != str(p_open).lower(): continue
            filtered_orders.append(order)
        
        return {"orders": filtered_orders}
    except Exception: return {"orders": []}

def F_Add_Order(p_order: dict) -> bool:
    # DESC: Adds a new order
    # PARAMS:
    #   p_order: Dictionary containing the order information to be added
    # RETURN: bool - Was the operation successful?
    try:
        orders_data: dict   = F_Create_Orders()
        orders_list         = orders_data.get('orders', [])
        for order in orders_list:
            if (order.get('symbol') == p_order['symbol'] and 
                order.get('side')   == p_order['side'] and 
                bool(order.get('open', ''))): return False
        
        formatted_order = {
            "datetime":         LB_Date.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "open":             "true",
            "symbol":           p_order.get('symbol', '').lower(),
            "side":             p_order.get('side', '').lower(),
            "leverage":         str(p_order.get('leverage', '')),
            "quantity_coin":    str(p_order.get('quantity_coin', '')),
            "quantity_quote":   str(p_order.get('quantity_quote', '')),
            "entry_price":      str(p_order.get('entry_price', '')),
            "exit_price":       "",
            "pnl":              ""
        }
        orders_list.append(formatted_order)
        with open(FILE_PATH, 'w', encoding='utf-8') as f: LB_JSON.dump(orders_data, f, indent=4, ensure_ascii=False)
        return True
    except Exception: return False

def F_Update_Order(p_symbol: str, p_side: str, p_update: dict) -> bool:
    # DESC: Updates an existing order
    # PARAMS:
    #   p_symbol: Symbol of the order to be updated
    #   p_side: Transaction side of the order to be updated
    #   p_update: Dictionary containing the update information
    # RETURN: bool - Was the operation successful?
    try:
        F_Del_Orders_Old()
        orders_data: dict   = F_Create_Orders()
        orders              = orders_data.get('orders', [])
        updated             = False
        for order in orders:
            if (order.get('symbol', '').lower() == p_symbol.lower() and 
                order.get('side', '').lower()   == p_side.lower() and 
                order.get('open')              == 'true'):
                order.update(p_update)
                updated = True
                break
        if updated:
            with open(FILE_PATH, 'w', encoding='utf-8') as f: LB_JSON.dump(orders_data, f, indent=4, ensure_ascii=False)
        return updated
    except Exception: return False

def F_Del_Orders_Old() -> bool:
    # DESC: Deletes closed orders older than 30 days
    # RETURN: bool - Was the operation successful?
    try:
        orders_data: dict   = F_Create_Orders()
        orders              = orders_data.get('orders', [])
        if not orders: return True
        thirty_days_ago = LB_Date.datetime.now() - LB_Date.timedelta(days=30)
        updated_orders  = []
        for order in orders:
            date: str = order.get('datetime')
            if not date or order.get('open') == 'true':
                updated_orders.append(order)
                continue
            try:
                order_date = LB_Date.datetime.strptime(date, "%Y-%m-%d %H:%M:%S")
                if order_date >= thirty_days_ago: updated_orders.append(order)
            except ValueError: 
                updated_orders.append(order)
                continue
        
        if len(updated_orders) < len(orders):
            orders_data['orders'] = updated_orders
            with open(FILE_PATH, 'w', encoding='utf-8') as f: 
                LB_JSON.dump(orders_data, f, indent=4, ensure_ascii=False)
            return True
        return False
    except Exception: return False

# endregion