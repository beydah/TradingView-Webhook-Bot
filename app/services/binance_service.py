import datetime
from decimal import Decimal, ROUND_DOWN
from binance.um_futures import UMFutures
from app.core.config import settings
from app.core.logging import logger

# Constants
BASE_URL = "https://testnet.binancefuture.com" if "test" in settings.BINANCE_API_KEY.lower() else "https://fapi.binance.com"

class BinanceService:
    _instance = None

    @classmethod
    def get_client(cls):
        if cls._instance is None:
            cls._instance = UMFutures(
                key=settings.BINANCE_API_KEY, 
                secret=settings.BINANCE_SECRET_KEY, 
                base_url=BASE_URL
            )
        return cls._instance

def get_wallet_info(asset_filter: str = None) -> list:
    try:
        client = BinanceService.get_client()
        balances = client.balance(recvWindow=5000)
        positions = client.get_position_risk(recvWindow=5000)
        wallet_data = []

        for b in balances:
            asset = b['asset']
            if asset_filter and asset != asset_filter:
                continue

            # find the matching position (if any)
            # optimized: pre-indexing positions would be faster but this is fine for N<100
            pos = next((p for p in positions if str(p.get('symbol', '')).startswith(asset)), {})
            
            try:
                bal_val = float(b.get('balance', 0) or 0)
            except ValueError:
                bal_val = 0.0
            
            try:
                pim_val = float(pos.get('positionInitialMargin', 0) or 0)
            except ValueError:
                pim_val = 0.0

            if bal_val == 0 and pim_val == 0:
                continue

            wallet_data.append({
                'asset': asset,
                'balance': str(b.get('balance', '0')),
                'wait_balance': str(pos.get('positionInitialMargin', '0')),
                'cross_un_pnl': str(pos.get('unRealizedProfit', '0')),
                'cross_margin_borrowed': str(pos.get('isolatedMargin', '0'))
            })
        return wallet_data
    except Exception as e:
        logger.error(f"[get_wallet_info] Asset: {asset_filter} - Error: {e}")
        return []

def get_symbol_info(symbol: str) -> dict:
    """
    Fetches symbol information
    Returns: base_asset, quote_asset, min_qty, max_qty, step_size, tick_size, min_leverage, max_leverage
    """
    try:
        client = BinanceService.get_client()
        info = client.exchange_info()
        symbol_info = next((s for s in info['symbols'] if s['symbol'] == symbol), None)
        
        if not symbol_info:
            return {}

        # Safe filter extraction
        filters = {f['filterType']: f for f in symbol_info['filters']}
        lot_filter = filters.get('LOT_SIZE', {})
        market_lot_filter = filters.get('MARKET_LOT_SIZE', {})
        price_filter = filters.get('PRICE_FILTER', {})

        min_qty = lot_filter.get('minQty')
        max_qty = lot_filter.get('maxQty')
        step_size = lot_filter.get('stepSize')
        tick_size = price_filter.get('tickSize')
        
        market_max_qty = market_lot_filter.get('maxQty') or max_qty
        market_step_size = market_lot_filter.get('stepSize') or step_size

        # Leverage brackets
        min_leverage = None
        max_leverage = None
        
        try:
            brackets = client.leverage_brackets(symbol=symbol)
            if brackets and 'brackets' in brackets[0]:
                 # brackets returns a list, usually specific symbol query returns a list with 1 item if symbol arg is passed?
                 # SDK says: If symbol is not sent, all symbols will be returned. 
                 # We passed symbol=symbol to leverage_brackets? No, the original code didn't pass symbol, it fetched ALL.
                 # Optimization: Pass symbol to API if possible. The SDK supports `symbol` param.
                 # But let's stick to original logic structure for safety, or improve it.
                 # Original: binance.leverage_brackets() -> iterates to find symbol.
                 # Improved: client.leverage_brackets(symbol=symbol)
                 
                 # NOTE: binance-connector-python `leverage_brackets` supports `symbol`.
                 symbol_bracket = brackets[0] # Since we filter by symbol in call
                 leverages = [int(x['initialLeverage']) for x in symbol_bracket['brackets']]
                 min_leverage = str(min(leverages))
                 max_leverage = str(max(leverages))
        except Exception:
            # Fallback or error in getting brackets
            pass

        return {
            'base_asset': symbol_info['baseAsset'],
            'quote_asset': symbol_info['quoteAsset'],
            'min_qty': min_qty,
            'max_qty': max_qty,
            'step_size': step_size,
            'tick_size': tick_size,
            'min_leverage': min_leverage,
            'max_leverage': max_leverage,
            'market_max_qty': market_max_qty,
            'market_step_size': market_step_size
        }
    except Exception as e:
        logger.error(f"[get_symbol_info] Symbol: {symbol} - Error: {e}")
        return {}

def get_market_info(symbol: str) -> dict:
    try:
        client = BinanceService.get_client()
        # ticker_price might not return bid/ask, but original code used ticker_price for price 
        # and depth for bid/ask.
        ticker = client.ticker_price(symbol=symbol)
        price = ticker.get('price', '0')
        
        depth = client.depth(symbol=symbol, limit=5)
        bids = [(b[0], b[1]) for b in depth.get('bids', [])]
        asks = [(a[0], a[1]) for a in depth.get('asks', [])]
        
        return {
            'price': price,
            'bid': bids[0][0] if bids else '0',
            'ask': asks[0][0] if asks else '0',
            'order_book': {'bids': bids, 'asks': asks}
        }
    except Exception as e:
        logger.error(f"[get_market_info] Symbol: {symbol} - Error: {e}")
        return {}

def get_klines(symbol: str, period: str = '1m', limit: int = 100) -> list:
    try:
        client = BinanceService.get_client()
        raw_klines = client.klines(symbol=symbol, interval=period, limit=limit)
        # [Open Time, Open, High, Low, Close, Volume, ...]
        # Returning: [Open, High, Low, Close, Volume]
        return [[k[1], k[2], k[3], k[4], k[5]] for k in raw_klines]
    except Exception as e:
        logger.error(f"[get_klines] Symbol: {symbol} - Error: {e}")
        return []

def get_orders(symbol: str = None) -> list:
    try:
        client = BinanceService.get_client()
        positions = client.get_position_risk(recvWindow=5000)
        result = []
        for p in positions:
            if symbol and p['symbol'] != symbol:
                continue
            
            amt = float(p['positionAmt'])
            if amt > 0:
                side = "LONG"
            elif amt < 0:
                side = "SHORT"
            else:
                continue

            result.append({
                'symbol': p['symbol'],
                'side': side,
                'entry_price': p['entryPrice'],
                'quantity': abs(amt),
                'unrealized_pnl': p['unRealizedProfit']
            })
        return result
    except Exception as e:
        logger.error(f"[get_orders] Symbol: {symbol} - Error: {e}")
        return []

def get_orders_history(symbol: str, limit: int = 5) -> list:
    try:
        client = BinanceService.get_client()
        trades = client.get_account_trades(symbol=symbol, recvWindow=5000)
        trades = trades[-limit:]
        result = []
        
        # Optimization: Fetch position risk only once if possible, but here it's per trade logic? 
        # Actually leverage is from current position, might not match historical trade.
        # Original logic fetches position risk for every trade... that's N API calls.
        # Lets just fetch it once.
        positions = client.get_position_risk(recvWindow=5000)
        position_info = next((p for p in positions if p['symbol'] == symbol), {})
        leverage = str(position_info.get('leverage', '1'))

        for t in trades:
            side = "LONG" if t['side'] == "BUY" else "SHORT"
            qty_quote = float(t['qty']) * float(t['price'])
            
            pnl_percent = 0
            if qty_quote != 0:
                pnl_percent = (float(t.get('realizedPnl', 0)) / qty_quote * 100)

            result.append({
                "datetime": datetime.datetime.fromtimestamp(t['time'] / 1000).strftime("%Y-%m-%d %H:%M:%S"),
                "symbol": symbol,
                "side": side,
                "leverage": leverage,
                "quantity_coin": t['qty'],
                "quantity_quote": f"{qty_quote:.2f}",
                "exit_price": t['price'],
                "pnl_percent": f"{pnl_percent:.2f}"
            })
        return result
    except Exception as e:
        logger.error(f"[get_orders_history] Symbol: {symbol} - Error: {e}")
        return []

def open_order(symbol: str, side: str, quantity: str, leverage: str) -> bool:
    """
    p_side: "LONG" or "SHORT"
    """
    try:
        client = BinanceService.get_client()
        # Ensure margin type and leverage (ignoring errors as per original)
        try:
            client.change_margin_type(symbol=symbol, marginType=settings.MARGIN_TYPE.upper(), recvWindow=5000)
        except Exception:
            pass
            
        try:
             client.change_leverage(symbol=symbol, leverage=leverage, recvWindow=5000)
        except Exception:
            pass

        order_side = "BUY" if side == "LONG" else "SELL"
        client.new_order(symbol=symbol, side=order_side, type="MARKET", quantity=quantity, recvWindow=5000)
        return True
    except Exception as e:
        logger.error(f"[open_order] Symbol: {symbol} - Error: {e}")
        return False

def close_order(symbol: str, side: str) -> bool:
    try:
        client = BinanceService.get_client()
        positions = client.get_position_risk(recvWindow=5000)
        pos = next((p for p in positions if p['symbol'] == symbol), None)
        
        if not pos or float(pos.get('positionAmt', 0)) == 0:
            return False

        close_side = "SELL" if side == "LONG" else "BUY"
        
        info = get_symbol_info(symbol)
        step_s = info.get('market_step_size') or info.get('step_size') or '1'
        min_qty_s = info.get('min_qty') or '0'
        per_max_s = info.get('market_max_qty') or info.get('max_qty')
        
        step_size = Decimal(str(step_s))
        min_qty = Decimal(str(min_qty_s))
        per_max = Decimal(str(per_max_s)) if per_max_s not in (None, '0') else None

        def floor_to_step(x: Decimal) -> Decimal:
            if step_size <= 0: return x
            exp = step_size.normalize()
            return x.quantize(exp, rounding=ROUND_DOWN)

        remain = Decimal(str(abs(float(pos['positionAmt']))))
        remain = floor_to_step(remain)
        
        if remain <= 0:
            return False

        chunk_size = floor_to_step(per_max) if (per_max is not None and per_max > 0) else remain
        
        if chunk_size <= 0:
            logger.error(f"[close_order] Invalid chunk size for {symbol}")
            return False

        any_ok = False
        
        while remain > 0:
            cur = min(remain, chunk_size)
            cur = floor_to_step(cur)
            
            if cur < min_qty:
                break
                
            cur_str = format(cur.normalize(), 'f')
            
            try:
                client.new_order(symbol=symbol, side=close_side, type="MARKET", quantity=cur_str, reduceOnly=True, recvWindow=5000)
                any_ok = True
                remain = floor_to_step(remain - cur)
                continue
            except Exception as e:
                # Retry with smaller step
                retry = floor_to_step(cur - step_size)
                if retry >= min_qty:
                    retry_str = format(retry.normalize(), 'f')
                    try:
                        client.new_order(symbol=symbol, side=close_side, type="MARKET", quantity=retry_str, reduceOnly=True, recvWindow=5000)
                        any_ok = True
                        remain = floor_to_step(remain - retry)
                        continue
                    except Exception as e2:
                        logger.error(f"[close_order] Retry failed for {symbol}: {e2}")
                        break
                
                logger.error(f"[close_order] Failed for {symbol}: {e}")
                break

        return any_ok
    except Exception as e:
        logger.error(f"[close_order] Symbol: {symbol} - Error: {e}")
        return False

def stop_order(symbol: str, side: str, price: str) -> bool:
    try:
        client = BinanceService.get_client()
        order_side = "SELL" if side == "LONG" else "BUY"
        client.new_order(symbol=symbol, side=order_side, type="STOP_MARKET", stopPrice=price, closePosition=True, recvWindow=5000)
        return True
    except Exception as e:
        logger.error(f"[stop_order] Symbol: {symbol} - Error: {e}")
        return False
