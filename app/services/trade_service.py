from decimal import Decimal, ROUND_DOWN
from app.services import binance_service
from app.core.config import settings
from app.core.logging import logger

def calc_virtual_quantity(symbol: str, quantity: float) -> str:
    """
    Calculates the quantity for an order (rounds according to min/max and stepSize)
    """
    try:
        symbol_info = binance_service.get_symbol_info(symbol)
        if not symbol_info:
            logger.error(f"[calc_virtual_quantity] Symbol info not found: {symbol}")
            return ""

        min_qty_s = symbol_info.get('min_qty') or '0'
        max_qty_s = symbol_info.get('max_qty') or '0'
        step_s = symbol_info.get('step_size') or '1'
        
        q_input = Decimal(str(quantity))
        min_qty = Decimal(str(min_qty_s))
        max_qty = Decimal(str(max_qty_s)) if max_qty_s not in (None, '0') else None
        step_size = Decimal(str(step_s))

        max_eff = max_qty
        if max_qty is not None and step_size > 0:
            max_eff = (max_qty // step_size) * step_size
            
        q = q_input
        if max_eff is not None and q > max_eff:
            q = max_eff
            
        if q < min_qty:
            q = min_qty
            
        if step_size > 0:
            exp = step_size.normalize()
            q = q.quantize(exp, rounding=ROUND_DOWN)

        # Re-check limits after rounding
        if max_eff is not None and q > max_eff:
            q = max_eff
        if q < min_qty:
            q = min_qty
            
        if q <= 0:
            logger.error(f"[calc_virtual_quantity] Calculated non-positive qty for {symbol}. input={quantity}")
            return ""

        return format(q.normalize(), 'f')
    except Exception as e:
        logger.error(f"[calc_virtual_quantity] Error: {e}")
        return ""

def calc_virtual_leverage(symbol: str, leverage: int) -> str:
    try:
        symbol_info = binance_service.get_symbol_info(symbol)
        min_lev_s = symbol_info.get('min_leverage')
        max_lev_s = symbol_info.get('max_leverage')
        
        if not min_lev_s or not max_lev_s:
            return str(leverage)
            
        min_lev = int(float(min_lev_s))
        max_lev = int(float(max_lev_s))
        
        if min_lev > leverage:
            return str(min_lev)
        elif max_lev < leverage:
            return str(max_lev)
            
        return str(leverage)
    except Exception as e:
        logger.error(f"[calc_virtual_leverage] Error: {e}")
        return str(leverage)

from app.core import crud
from app.core.database import SessionLocal

# Wrapper functions for consistency
def open_order(symbol: str, side: str, quantity: str, leverage: str) -> bool:
    try:
        # 1. Execute on Binance
        result = binance_service.open_order(symbol, side, quantity, leverage)
        
        # 2. Record in DB if successful
        if result:
            db = SessionLocal()
            try:
                # Need to fetch details for accurate recording, but for now using inputs
                # Ideally binance_service returns the order object or details
                # For this refactor phase, we approximate or fetch from binance_service if it returned dict
                # binance_service.open_order returns bool currently.
                # We will record the *intent* as open. 
                # TODO: Update binance_service to return Order info.
                
                # Fetch current price for entry estimation
                m_info = binance_service.get_market_info(symbol)
                entry_price = float(m_info.get('price', 0)) if m_info else 0.0
                
                qty_float = float(quantity)
                
                crud.create_order(
                    db=db,
                    symbol=symbol,
                    side=side,
                    leverage=int(float(leverage)),
                    quantity_coin=qty_float,
                    quantity_quote=qty_float * entry_price, # approx
                    entry_price=entry_price
                )
            except Exception as dbe:
                logger.error(f"[open_order] DB Error: {dbe}")
            finally:
                db.close()
                
        return result
    except Exception as e:
         logger.error(f"[open_order] Error: {e}")
         return False

def close_order(symbol: str, side: str) -> bool:
    try:
        # 1. Execute on Binance
        result = binance_service.close_order(symbol, side)
        
        # 2. Update DB
        if result:
            db = SessionLocal()
            try:
                # Fetch price for exit
                m_info = binance_service.get_market_info(symbol)
                exit_price = float(m_info.get('price', 0)) if m_info else 0.0
                
                # Calculate PnL? 
                # binance_service doesn't return PnL. 
                # We can't easily calculate exact PnL without order ID matching.
                # We will just mark as closed with exit price.
                crud.close_order(db, symbol, side, exit_price, pnl=0.0)
            except Exception as dbe:
                 logger.error(f"[close_order] DB Error: {dbe}")
            finally:
                db.close()

        return result
    except Exception as e:
        logger.error(f"[close_order] Error: {e}")
        return False

def execute_trade_logic(symbol: str, side: str) -> bool:
    """
    Runs the automatic trading logic for the order.
    side: "long_open", "short_open", "long_close", "short_close"
    """
    try:
        symbol = symbol.upper()
        if symbol.endswith(".P"):
            symbol = symbol[:-2]
            
        symbol_info = binance_service.get_symbol_info(symbol)
        quote_asset = symbol_info.get("quote_asset")
        market_info = binance_service.get_market_info(symbol)
        price = float(market_info.get("price")) if market_info else 0.0
        
        wallet_list = binance_service.get_wallet_info(quote_asset)
        quote_quantity = float(wallet_list[0]["balance"]) if wallet_list else 0.0
        
        balance_percent_cfg = settings.ORDER_BALANCE_PERCENT

        if quote_quantity < 10 or price <= 0:
            logger.warning(f"[execute_trade_logic] Insufficient balance or price. {symbol} bal={quote_quantity} price={price}")
            return False

        percent = max(min(balance_percent_cfg, 100), 1)
        virtual_leverage = calc_virtual_leverage(symbol, settings.ORDER_LEVERAGE)
        
        try:
            lev_num = float(virtual_leverage)
            if lev_num <= 0: lev_num = 1.0
        except ValueError:
            lev_num = 1.0

        # Close opposite position first if opening
        if side == "long_open":
            close_order(symbol, "SHORT")
        elif side == "short_open":
            close_order(symbol, "LONG")
            
        # Calculate amount to use
        use_amount = quote_quantity * (percent / 100.0)
        desired_base_qty = (use_amount * lev_num) / price

        # Constraints
        min_qty = Decimal(str(symbol_info.get('min_qty') or '0'))
        step_s = symbol_info.get('market_step_size') or symbol_info.get('step_size') or '1'
        step_size = Decimal(str(step_s))
        
        per_max_s = symbol_info.get('market_max_qty') or symbol_info.get('max_qty')
        per_max = Decimal(str(per_max_s)) if per_max_s not in (None, '0') else None

        def floor_to_step(x: Decimal) -> Decimal:
            if step_size <= 0: return x
            exp = step_size.normalize()
            return x.quantize(exp, rounding=ROUND_DOWN)

        total_qty_dec = Decimal(str(desired_base_qty))
        if total_qty_dec < min_qty:
            total_qty_dec = min_qty
            
        total_qty_dec = floor_to_step(total_qty_dec)
        
        if total_qty_dec < min_qty:
            logger.warning(f"[execute_trade_logic] Total qty below min after step adjust. {symbol} qty={total_qty_dec}")
            return False

        chunk_size = floor_to_step(per_max) if (per_max is not None and per_max > 0) else total_qty_dec
        
        if chunk_size <= 0:
            logger.error(f"[execute_trade_logic] Invalid chunk size for {symbol}")
            return False

        remain = total_qty_dec
        any_ok = False
        part_idx = 1
        
        while remain > 0:
            cur = min(remain, chunk_size)
            cur = floor_to_step(cur)
            
            if cur < min_qty:
                break
                
            cur_str = format(cur.normalize(), 'f')
            logger.info(f"[execute_trade_logic] CHUNK {part_idx} {symbol} side={side} qty={cur_str}/{format(total_qty_dec.normalize(),'f')} lev={virtual_leverage}")
            
            ok = False
            if side == "long_open":
                ok = open_order(symbol, "LONG", cur_str, virtual_leverage)
            elif side == "short_open":
                ok = open_order(symbol, "SHORT", cur_str, virtual_leverage)
            elif side == "long_close":
                ok = close_order(symbol, "LONG")
            elif side == "short_close":
                ok = close_order(symbol, "SHORT")
            
            executed_qty = cur
            if not ok:
                # Retry strategy
                retry = floor_to_step(cur - step_size)
                if retry >= min_qty:
                    retry_str = format(retry.normalize(), 'f')
                    logger.warning(f"[execute_trade_logic] RETRY CHUNK {part_idx} {symbol} side={side} qty={retry_str}")
                    
                    if side == "long_open": ok = open_order(symbol, "LONG", retry_str, virtual_leverage)
                    elif side == "short_open": ok = open_order(symbol, "SHORT", retry_str, virtual_leverage)
                    elif side == "long_close": ok = close_order(symbol, "LONG")
                    elif side == "short_close": ok = close_order(symbol, "SHORT")
                    
                    if ok: executed_qty = retry

            if ok:
                any_ok = True
                remain = floor_to_step(remain - executed_qty)
                part_idx += 1
            else:
                logger.error(f"[execute_trade_logic] Chunk failed for {symbol} side={side} qty={cur_str}")
                break

        return any_ok
    except Exception as e:
        logger.error(f"[execute_trade_logic] Error: {e}")
        return False
