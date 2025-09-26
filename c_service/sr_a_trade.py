# region ===== INFO ===================================================================================================

# Developer : Ilkay Beydah Saglam
# Website   : https://beydahsaglam.com
# Created   : 2025-08-21
# Version   : Python 3.10

# DESC:
#   This script is designed to connect to the Binance Futures API to make the
#   order submission process reliable and standardized. Before an order is opened,
#   necessary quantity, leverage, margin, and risk calculations are performed;
#   all Binance restrictions (min/max quantity, leverage, notional, tick/step size) are verified.

# FEATURES:
#   - API connection management (API key & secret)
#   - Account and balance information
#   - Minimum/maximum quantity and leverage limits
#   - Virtual trade quantity and leverage calculations
#   - Long/Short order opening and closing functions
#   - Pre-trade validation and risk management
#   - Trade business flow (automated trading logic)

# endregion
# region ===== LIBRARY ================================================================================================

from c_service import sr_c_binance as   SR_Binance
from d_model import md_a_settings as    MD_Settings
from d_model import md_e_logs as        MD_Logs
from decimal import Decimal as          LB_Decimal
from decimal import ROUND_DOWN as       LB_ROUND_DOWN

# endregion
# region ===== VARIABLE ===============================================================================================

# endregion
# region ===== OBJECT =================================================================================================

# endregion
# region ===== FUNCTION ===============================================================================================

def F_Calc_Virtual_Quantity(p_symbol: str, p_quantity: float) -> str:
    # DESC: Calculates the quantity for an order (rounds according to min/max and stepSize)
    try:
        symbol_info: dict = SR_Binance.F_Get_Symbol_Info(p_symbol)
        if not symbol_info:
            MD_Logs.F_Add_Logs("error", "F_Calc_Virtual_Quantity", f"Symbol info not found: {p_symbol}")
            return ""

        min_qty_s = symbol_info.get('min_qty') or '0'
        max_qty_s = symbol_info.get('max_qty') or '0'
        step_s    = symbol_info.get('step_size') or '1'
        q_input   = LB_Decimal(str(p_quantity))
        min_qty   = LB_Decimal(str(min_qty_s))
        max_qty   = LB_Decimal(str(max_qty_s)) if max_qty_s not in (None, '0') else None
        step_size = LB_Decimal(str(step_s))
        if max_qty is not None and step_size > 0: max_eff = (max_qty // step_size) * step_size
        else: max_eff = max_qty
        q = q_input
        if max_eff is not None and q > max_eff: q = max_eff
        if q < min_qty: q = min_qty
        if step_size > 0:
            exp = step_size.normalize()
            q = (q.quantize(exp, rounding=LB_ROUND_DOWN))

        if max_eff is not None and q > max_eff: q = max_eff
        if q < min_qty: q = min_qty
        if q <= 0:
            MD_Logs.F_Add_Logs("error", "F_Calc_Virtual_Quantity", f"Calculated non-positive qty for {p_symbol}. input={p_quantity}")
            return ""

        q_str = format(q.normalize(), 'f')  # string without scientific notation
        return q_str
    except Exception as e:
        return not MD_Logs.F_Add_Logs("ERROR", "F_Calc_Virtual_Quantity", e)

def F_Calc_Virtual_Leverage(p_symbol: str, p_leverage: int) -> str:
    # DESC: Calculates leverage for the order
    try:
        symbol_info: dict = SR_Binance.F_Get_Symbol_Info(p_symbol)
        min_lev_s = symbol_info.get('min_leverage')
        max_lev_s = symbol_info.get('max_leverage')
        if not min_lev_s or not max_lev_s: return str(p_leverage)
        min_lev = int(float(min_lev_s))
        max_lev = int(float(max_lev_s))
        if min_lev > p_leverage: return str(min_lev)
        elif max_lev < p_leverage: return str(max_lev)
        return str(p_leverage)
    except Exception as e: return not MD_Logs.F_Add_Logs("ERROR", "F_Calc_Virtual_Leverage", e)

def F_Open_Order(p_symbol: str, p_side: str, p_quantity: str, p_leverage: str) -> None:
    # DESC: Opens an order
    try: return SR_Binance.F_Open_Order(p_symbol, p_side, p_quantity, p_leverage)
    except Exception as e: return not MD_Logs.F_Add_Logs("ERROR", "F_Open_Order", e)

def F_Close_Order(p_symbol: str, p_side: str) -> bool:
    # DESC: Closes an order
    try: return SR_Binance.F_Close_Order(p_symbol, p_side)
    except Exception as e: return not MD_Logs.F_Add_Logs("ERROR", "F_Close_Order", e)

def F_Trade_Business(p_symbol: str, p_side: str) -> bool:
    # DESC: Runs the automatic trading logic for the order
    try:
        p_symbol = p_symbol.upper()
        if p_symbol.endswith(".P"): p_symbol = p_symbol[:-2]
        settings: dict        = MD_Settings.F_Get_Settings()
        symbol_info: dict     = SR_Binance.F_Get_Symbol_Info(p_symbol)
        quote_asset: str      = symbol_info.get("quote_asset")
        market_info: dict     = SR_Binance.F_Get_Market_Info(p_symbol)
        price: float          = float(market_info.get("price")) if market_info else 0.0
        wallet_list           = SR_Binance.F_Get_Wallet_Info(quote_asset)
        quote_quantity: float = float(wallet_list[0]["balance"]) if wallet_list else 0.0
        try: balance_percent_cfg = int(settings.get("order_balance"))
        except Exception: balance_percent_cfg = 100
        if quote_quantity < 10 or price <= 0: 
            MD_Logs.F_Add_Logs("warning", "F_Trade_Business", f"Insufficient balance or price. {p_symbol} bal={quote_quantity} price={price}")
            return False

        percent = max(min(balance_percent_cfg, 100), 1)
        virtual_leverage: str = F_Calc_Virtual_Leverage(p_symbol, int(settings.get("order_leverage")))
        try:
            lev_num = float(virtual_leverage)
            if lev_num <= 0: lev_num = 1.0
        except Exception: lev_num = 1.0
        if p_side == "long_open": F_Close_Order(p_symbol, "SHORT")
        elif p_side == "short_open": F_Close_Order(p_symbol, "LONG")
        use_amount = quote_quantity * (percent / 100.0)
        desired_base_qty = (use_amount * lev_num) / price
        min_qty   = LB_Decimal(str(symbol_info.get('min_qty') or '0'))
        step_size = LB_Decimal(str(symbol_info.get('market_step_size') or symbol_info.get('step_size') or '1'))
        per_max_s = symbol_info.get('market_max_qty') or symbol_info.get('max_qty')
        per_max   = LB_Decimal(str(per_max_s)) if per_max_s not in (None, '0') else None
        def floor_to_step(x: LB_Decimal) -> LB_Decimal:
            if step_size <= 0: return x
            exp = step_size.normalize()
            return x.quantize(exp, rounding=LB_ROUND_DOWN)

        total_qty_dec = LB_Decimal(str(desired_base_qty))
        if total_qty_dec < min_qty: total_qty_dec = min_qty
        total_qty_dec = floor_to_step(total_qty_dec)
        if total_qty_dec < min_qty:
            MD_Logs.F_Add_Logs("warning", "F_Trade_Business", f"Total qty below min after step adjust. {p_symbol} qty={total_qty_dec}")
            return False

        if per_max is not None and per_max > 0: chunk_size = floor_to_step(per_max)
        else: chunk_size = total_qty_dec
        if chunk_size <= 0:
            MD_Logs.F_Add_Logs("error", "F_Trade_Business", f"Invalid chunk size for {p_symbol} step={step_size} per_max={per_max_s}")
            return False

        remain = total_qty_dec
        any_ok = False
        part_idx = 1
        while remain > 0:
            cur = remain if remain <= chunk_size else chunk_size
            cur = floor_to_step(cur)
            if cur < min_qty: break
            cur_str = format(cur.normalize(), 'f')
            MD_Logs.F_Add_Logs("info", "F_Trade_Business", f"CHUNK {part_idx} {p_symbol} side={p_side} qty={cur_str}/{format(total_qty_dec.normalize(),'f')} lev={virtual_leverage}")
            if p_side == "long_open": ok = F_Open_Order(p_symbol, "LONG", cur_str, virtual_leverage)
            elif p_side == "short_open": ok = F_Open_Order(p_symbol, "SHORT", cur_str, virtual_leverage)
            elif p_side == "long_close": ok = F_Close_Order(p_symbol, "LONG")
            elif p_side == "short_close": ok = F_Close_Order(p_symbol, "SHORT")
            else: ok = False
            executed_qty = cur
            if not ok:
                retry = floor_to_step(cur - step_size)
                if retry >= min_qty:
                    retry_str = format(retry.normalize(), 'f')
                    MD_Logs.F_Add_Logs("warning", "F_Trade_Business", f"RETRY CHUNK {part_idx} {p_symbol} side={p_side} qty={retry_str}")
                    if p_side == "long_open": ok = F_Open_Order(p_symbol, "LONG", retry_str, virtual_leverage)
                    elif p_side == "short_open": ok = F_Open_Order(p_symbol, "SHORT", retry_str, virtual_leverage)
                    elif p_side == "long_close": ok = F_Close_Order(p_symbol, "LONG")
                    elif p_side == "short_close": ok = F_Close_Order(p_symbol, "SHORT")
                    if ok: executed_qty = retry

            if ok:
                any_ok = True
                remain = floor_to_step(remain - executed_qty)
                part_idx += 1

            else:
                MD_Logs.F_Add_Logs("error", "F_Trade_Business", f"Chunk failed for {p_symbol} side={p_side} qty={cur_str}")
                break

        return any_ok
    except Exception as e: return not MD_Logs.F_Add_Logs("ERROR", "F_Trade_Business", e)

# endregion
