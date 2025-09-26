# region ===== INFO ===================================================================================================

# Developer : Ilkay Beydah Saglam
# Website   : https://beydahsaglam.com
# Created   : 2025-08-21
# Version   : Python 3.10

# DESC:
#   This script is designed to connect to the Binance Futures API,
#   retrieve account information, get symbol and market data,
#   and standardize order opening/closing functions.

# FEATURES:
#   - API connection management (API key, secret)
#   - Account balance and position information
#   - Symbol, candlestick, and market data
#   - Open orders and order history
#   - Order opening and closing operations (Long/Short)

# endregion
# region ===== LIBRARY ================================================================================================

from d_model import md_a_settings as        MD_Settings
from d_model import md_e_logs as            MD_Logs

from binance.um_futures import UMFutures as LB_Binance
import datetime as                          LB_Date
from decimal import Decimal as              LB_Decimal
from decimal import ROUND_DOWN as           LB_ROUND_DOWN

# endregion
# region ===== VARIABLE ===============================================================================================

SETTINGS: dict  = MD_Settings.F_Get_Settings()
API_KEY: str    = SETTINGS.get("binance_api")
API_SECRET: str = SETTINGS.get("binance_secret")
TEST: bool      = True
BASE_URL: str   = "https://testnet.binancefuture.com" if TEST else "https://fapi.binance.com"

# endregion
# region ===== OBJECT =================================================================================================

Binance: object = LB_Binance(key=API_KEY, secret=API_SECRET, base_url=BASE_URL)

# endregion
# region ===== FUNCTION ===============================================================================================

def F_Connect_Binance():
    # DESC: Used to test the API connection.
    try: return Binance
    except Exception as e: MD_Logs.F_Add_Logs("ERROR", "F_Connect_Binance", e)

def F_Get_Wallet_Info(p_asset: str = None) -> list:
    try:
        binance     = F_Connect_Binance()
        balances    = binance.balance(recvWindow=5000)
        positions   = binance.get_position_risk(recvWindow=5000)
        wallet_data = []
        for b in balances:
            asset = b['asset']
            if p_asset and asset != p_asset: continue
            # find the matching position (if any)
            pos = next((p for p in positions if str(p.get('symbol','')).startswith(asset)), {})
            # safe numeric conversions
            try: bal_val = float(b.get('balance', 0) or 0)
            except Exception: bal_val = 0.0
            try: pim_val = float(pos.get('positionInitialMargin', 0) or 0)
            except Exception: pim_val = 0.0
            # skip if completely empty
            if bal_val == 0 and pim_val == 0: continue
            wallet_data.append({
                'asset':                    asset,
                'balance':                  str(b.get('balance', '0')),
                'wait_balance':             str(pos.get('positionInitialMargin', '0')),
                'cross_un_pnl':             str(pos.get('unRealizedProfit', '0')),
                'cross_margin_borrowed':    str(pos.get('isolatedMargin', '0'))
            })
        return wallet_data
    except Exception as e:
        MD_Logs.F_Add_Logs("ERROR", "F_Get_Wallet_Info", str(f"Asset: {p_asset} - Error: {e}"))
        return []

def F_Get_Symbol_Info(p_symbol: str) -> dict:
    """
    DESC: Fetches symbol information
    Returns: base_asset, quote_asset, min_qty, max_qty, step_size, tick_size, min_leverage, max_leverage
    """
    try:
        binance     = F_Connect_Binance()
        info        = binance.exchange_info()
        symbol_info = next((s for s in info['symbols'] if s['symbol'] == p_symbol), None)
        if not symbol_info: return {}
        lot_filter          = next((f for f in symbol_info['filters'] if f['filterType'] == 'LOT_SIZE'), {})
        market_lot_filter   = next((f for f in symbol_info['filters'] if f['filterType'] == 'MARKET_LOT_SIZE'), {})
        price_filter        = next((f for f in symbol_info['filters'] if f['filterType'] == 'PRICE_FILTER'), {})
        min_qty             = lot_filter.get('minQty', None)
        max_qty             = lot_filter.get('maxQty', None)
        step_size           = lot_filter.get('stepSize', None)
        tick_size           = price_filter.get('tickSize', None)
        market_max_qty      = market_lot_filter.get('maxQty', None) or max_qty
        market_step_size    = market_lot_filter.get('stepSize', None) or step_size
        brackets        = binance.leverage_brackets()
        symbol_bracket  = next((b for b in brackets if b['symbol'] == p_symbol), None)
        if symbol_bracket and 'brackets' in symbol_bracket and len(symbol_bracket['brackets']) > 0:
            leverages       = [int(x['initialLeverage']) for x in symbol_bracket['brackets']]
            min_leverage    = str(min(leverages))
            max_leverage    = str(max(leverages))

        else:
            min_leverage = None
            max_leverage = None

        return {
            'base_asset':   symbol_info['baseAsset'],
            'quote_asset':  symbol_info['quoteAsset'],
            'min_qty':      min_qty,
            'max_qty':      max_qty,
            'step_size':    step_size,
            'tick_size':    tick_size,
            'min_leverage': min_leverage,
            'max_leverage': max_leverage,
            'market_max_qty':   market_max_qty,
            'market_step_size': market_step_size
        }
    except Exception as e:
        MD_Logs.F_Add_Logs("ERROR", "F_Get_Symbol_Info", str(f"Symbol: {p_symbol} - Error: {e}"))
        return {}

def F_Get_Market_Info(p_symbol: str) -> dict:
    # DESC: Fetches the symbol's instant price and order book data
    # Returns: dict {
    #     'price': str,         # last price
    #     'bid': str,           # best bid price
    #     'ask': str,           # best ask price
    #     'order_book': {       # depth (top 5 levels)
    #         'bids': list,     # [(price, qty), ...]
    #         'asks': list      # [(price, qty), ...]}}
    try:
        binance = F_Connect_Binance()
        ticker  = binance.ticker_price(symbol=p_symbol)
        price   = ticker.get('price', '0')
        depth   = binance.depth(symbol=p_symbol, limit=5)
        bids    = [(b[0], b[1]) for b in depth.get('bids', [])]
        asks    = [(a[0], a[1]) for a in depth.get('asks', [])]
        return {
            'price':        price,
            'bid':          bids[0][0] if bids else '0',
            'ask':          asks[0][0] if asks else '0',
            'order_book':   {'bids': bids,'asks': asks}
        }
    except Exception as e:
        MD_Logs.F_Add_Logs("ERROR", "F_Get_Market_Info", str(f"Symbol: {p_symbol} - Error: {e}"))
        return {}

def F_Get_Klines(p_symbol: str, p_period: str = '1m', p_limit: int = 100) -> list:
    # DESC: Fetches symbol candlestick data. returns list [[open, high, low, close, volume], ...]
    try:
        binance     = F_Connect_Binance()
        raw_klines  = binance.klines(symbol=p_symbol, interval=p_period, limit=p_limit)
        klines      = [[k[1], k[2], k[3], k[4], k[5]] for k in raw_klines]
        return klines
    except Exception as e:
        MD_Logs.F_Add_Logs("ERROR", "F_Get_Klines", str(f"Symbol: {p_symbol} - Error: {e}"))
        return []

def F_Get_Orders(p_symbol: str = None) -> list:
    # DESC: Fetches open positions. (Symbol - Side - Entry Price - Qty - Leverage - PnL)
    try:
        binance     = F_Connect_Binance()
        positions   = binance.get_position_risk(recvWindow=5000)
        result      = []
        for p in positions:
            if p_symbol and p['symbol'] != p_symbol: continue
            side = "LONG" if float(p['positionAmt']) > 0 else "SHORT" if float(p['positionAmt']) < 0 else None
            if side is None: continue
            result.append({
                'symbol':           p['symbol'],
                'side':             side,
                'entry_price':      p['entryPrice'],
                'quantity':         abs(float(p['positionAmt'])),
                'unrealized_pnl':   p['unRealizedProfit']
            })

        return result
    except Exception as e:
        MD_Logs.F_Add_Logs("ERROR", "F_Get_Orders", str(f"Symbol: {p_symbol} - Error: {e}"))
        return []

def F_Get_Orders_History(p_symbol: str, limit: int = 5) -> list:
    # DESC: Fetches position history. Return format:
    # datetime, symbol, side, leverage, quantity_coin, quantity_quote, entry_price, exit_price, pnl_percent
    try:
        binance = F_Connect_Binance()
        result = []
        trades = binance.get_account_trades(symbol=p_symbol, recvWindow=5000)
        trades = trades[-limit:]
        for t in trades:
            side: str           = "LONG" if t['side'] == "BUY" else "SHORT"
            qty_quote: float    = float(t['qty']) * float(t['price'])
            pnl_percent: float  = (float(t.get('realizedPnl', 0)) / qty_quote * 100) if qty_quote != 0 else 0
            position_info       = next((p for p in binance.get_position_risk(recvWindow=5000) if p['symbol'] == p_symbol), {})
            leverage: str       = position_info.get('leverage', '1')
            result.append({
                "datetime":         LB_Date.datetime.fromtimestamp(t['time'] / 1000).strftime("%Y-%m-%d %H:%M:%S"),
                "symbol":           p_symbol,
                "side":             side,
                "leverage":         leverage,
                "quantity_coin":    t['qty'],
                "quantity_quote":   f"{qty_quote:.2f}",
                "exit_price":       t['price'],
                "pnl_percent":      f"{pnl_percent:.2f}"
            })

        return result
    except Exception as e:
        MD_Logs.F_Add_Logs("ERROR", "F_Get_Orders_History", str(f"Symbol: {p_symbol} - Error: {e}"))
        return []

def F_Open_Order(p_symbol: str, p_side: str, p_quantity: str, p_leverage: str) -> bool:
    # DESC: Opens a position for the symbol (LONG / SHORT)
    try:
        binance = F_Connect_Binance()
        settings            = MD_Settings.F_Get_Settings()
        margin_type: str    = settings.get("margin_type").upper()
        try: 
            binance.change_margin_type(symbol=p_symbol, marginType=margin_type, recvWindow=5000)
            binance.change_leverage(symbol=p_symbol, leverage=p_leverage, recvWindow=5000)
        except: pass
        side: str = "BUY" if p_side == "LONG" else "SELL"
        binance.new_order(symbol = p_symbol, side = side, type = "MARKET", quantity = p_quantity, recvWindow=5000)
        return True
    except Exception as e: return not MD_Logs.F_Add_Logs("ERROR", "F_Open_Order", str(f"Symbol: {p_symbol} - Error: {e}"))

def F_Close_Order(p_symbol: str, p_side: str) -> bool:
    # DESC: Closes the open position for the symbol (LONG / SHORT). Closes in chunks according to per-order limits.
    try:
        binance     = F_Connect_Binance()
        positions   = binance.get_position_risk(recvWindow=5000)
        pos         = next((p for p in positions if p['symbol'] == p_symbol), None)
        if not pos or float(pos.get('positionAmt', 0)) == 0: return False
        close_side: str = "SELL" if p_side == "LONG" else "BUY"
        info            = F_Get_Symbol_Info(p_symbol)
        step_s          = info.get('market_step_size') or info.get('step_size') or '1'
        min_qty_s       = info.get('min_qty') or '0'
        per_max_s       = info.get('market_max_qty') or info.get('max_qty')
        step_size       = LB_Decimal(str(step_s))
        min_qty         = LB_Decimal(str(min_qty_s))
        per_max         = LB_Decimal(str(per_max_s)) if per_max_s not in (None, '0') else None

        def floor_to_step(x: LB_Decimal) -> LB_Decimal:
            if step_size <= 0: return x
            exp = step_size.normalize()
            return x.quantize(exp, rounding=LB_ROUND_DOWN)

        remain = LB_Decimal(str(abs(float(pos['positionAmt']))))
        remain = floor_to_step(remain)
        if remain <= 0: return False
        if per_max is not None and per_max > 0: chunk_size = floor_to_step(per_max)
        else: chunk_size = remain
        if chunk_size <= 0:
            MD_Logs.F_Add_Logs("error", "F_Close_Order", f"Invalid chunk size for {p_symbol} step={step_s} per_max={per_max_s}")
            return False

        any_ok = False
        part_idx = 1
        while remain > 0:
            cur = remain if remain <= chunk_size else chunk_size
            cur = floor_to_step(cur)
            if cur < min_qty: break
            cur_str = format(cur.normalize(), 'f')
            try:
                binance.new_order(symbol=p_symbol, side=close_side, type="MARKET", quantity=cur_str, reduceOnly=True, recvWindow=5000)
                any_ok = True
                remain = floor_to_step(remain - cur)
                part_idx += 1
                continue
            except Exception as e:
                retry = floor_to_step(cur - step_size)
                if retry >= min_qty:
                    retry_str = format(retry.normalize(), 'f')
                    try:
                        binance.new_order(symbol=p_symbol, side=close_side, type="MARKET", quantity=retry_str, reduceOnly=True, recvWindow=5000)
                        any_ok = True
                        remain = floor_to_step(remain - retry)
                        part_idx += 1
                        continue
                    except Exception as e2:
                        MD_Logs.F_Add_Logs("error", "F_Close_Order", str(f"Symbol: {p_symbol} - Retry chunk failed. Error: {e2}"))
                        break
                MD_Logs.F_Add_Logs("error", "F_Close_Order", str(f"Symbol: {p_symbol} - Chunk failed. Error: {e}"))
                break

        return any_ok
    except Exception as e: return not MD_Logs.F_Add_Logs("ERROR", "F_Close_Order", str(f"Symbol: {p_symbol} - Error: {e}"))

def F_Stop_Order(p_symbol: str, p_side: str, p_price: str) -> bool:
    # DESC: Adds a stop-loss to the open position at market price
    # p_side = "LONG" / "SHORT" (position direction)
    try:
        binance = F_Connect_Binance()
        side = "SELL" if p_side == "LONG" else "BUY"
        binance.new_order(symbol = p_symbol, side = side, type = "STOP_MARKET", stopPrice = p_price, closePosition = True, recvWindow=5000)
        return True
    except Exception as e: return not MD_Logs.F_Add_Logs("ERROR", "F_Stop_Order", str(f"Symbol: {p_symbol} - Error: {e}"))

# endregion
