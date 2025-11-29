"""
Test script to verify (1) pulling available buying power/cash and (2) executing a VOO trade via Alpaca.

Usage examples:
  python backend/tools/test_cash_sweep_voo.py --action info
  python backend/tools/test_cash_sweep_voo.py --action buy --qty 1 --after-hours --limit
  python backend/tools/test_cash_sweep_voo.py --action sell --qty 1 --after-hours --limit

Requirements:
  - Environment variables set for Alpaca API (ALPACA_API_KEY, ALPACA_SECRET_KEY, ALPACA_BASE_URL)
  - Optional: .env file in project root
"""
from __future__ import annotations
import os
import sys
import argparse
from datetime import date
from typing import Optional

# Load .env if present
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

# Import services from backend
CUR_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.normpath(os.path.join(CUR_DIR, '..'))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from services.alpaca_service import AlpacaService


def print_account_info(alpaca: AlpacaService):
    info = alpaca.get_account_info()
    if not info:
        print("[ERROR] Failed to retrieve account info. Check Alpaca credentials.")
        return False
    print("\n=== Account Info ===")
    print(f"Status         : {info.get('status')}")
    print(f"Currency       : {info.get('currency')}")
    print(f"Portfolio Value: {info.get('portfolio_value')}")
    print(f"Equity         : {info.get('equity')}")
    print(f"Cash           : {info.get('cash')}")
    print(f"Buying Power   : {info.get('buying_power')}")
    return True


def _fetch_price_stooq(symbol: str) -> Optional[float]:
    """Fetch last close using Stooq CSV without heavy deps. Maps US tickers to .us."""
    try:
        import requests
        sym = f"{symbol.lower()}.us"
        url = f"https://stooq.com/q/d/l/?s={sym}&i=d"
        resp = requests.get(url, timeout=10)
        if resp.status_code != 200 or 'Date,Open,High,Low,Close,Volume' not in resp.text:
            return None
        lines = resp.text.strip().splitlines()
        if len(lines) < 2:
            return None
        last = lines[-1].split(',')
        if len(last) >= 5:
            return float(last[4])
    except Exception:
        return None
    return None

def get_voo_price(symbol: str = 'VOO') -> Optional[float]:
    # First try lightweight Stooq fetch (no yfinance)
    price = _fetch_price_stooq(symbol)
    if price is not None:
        print(f"\n{symbol} current price (stooq): {price}")
        return price
    # As a fallback, attempt MarketDataService (may fail if yfinance incompatible)
    try:
        from services.market_data_service import MarketDataService
        market = MarketDataService()
        price = market.get_current_price(symbol)
        print(f"\n{symbol} current price (yfinance): {price}")
        return price
    except Exception as e:
        print(f"[ERROR] Could not fetch price for {symbol}: {e}")
        return None


def get_max_affordable_shares(symbol: str = 'VOO', prefer_buying_power: bool = True,
                              alpaca: Optional[AlpacaService] = None) -> Optional[int]:
    """
    Return the maximum whole-share quantity of `symbol` affordable using current
    buying power (preferred) or cash if buying power is unavailable.
    """
    try:
        alp = alpaca or AlpacaService()
        info = alp.get_account_info()
        if not info:
            print("[ERROR] Unable to load Alpaca account info")
            return None
        amt = None
        if prefer_buying_power:
            amt = info.get('buying_power')
        if amt is None:
            amt = info.get('cash')
        if amt is None:
            print("[ERROR] Neither buying_power nor cash available from account info")
            return None
        price = get_voo_price(symbol)
        if price is None or price <= 0:
            print(f"[ERROR] Could not retrieve a valid price for {symbol}")
            return None
        shares = int(float(amt) // float(price))
        return max(0, shares)
    except Exception as e:
        print(f"[ERROR] Failed to compute affordable shares: {e}")
        return None


def place_buy(alpaca: AlpacaService, symbol: str, qty: int, price: Optional[float],
              after_hours: bool, use_limit: bool) -> dict:
    original_ext = getattr(alpaca, 'extended_hours', False)
    try:
        if after_hours:
            setattr(alpaca, 'extended_hours', True)
        order_type = 'limit' if (use_limit or after_hours) else 'market'
        limit_price = None
        if order_type == 'limit':
            if not price:
                raise ValueError("Price required for limit order")
            # Small buffer above current price
            limit_price = round(max(price * 1.005, price + 0.50), 2)
        print(f"\nPlacing BUY order: {qty} {symbol} | type={order_type} | limit_price={limit_price} | extended_hours={getattr(alpaca,'extended_hours', False)}")
        return alpaca.place_buy_order(symbol, qty, order_type=order_type, limit_price=limit_price)
    finally:
        setattr(alpaca, 'extended_hours', original_ext)


def place_sell(alpaca: AlpacaService, symbol: str, qty: int, price: Optional[float],
               after_hours: bool, use_limit: bool) -> dict:
    original_ext = getattr(alpaca, 'extended_hours', False)
    try:
        if after_hours:
            setattr(alpaca, 'extended_hours', True)
        order_type = 'limit' if (use_limit or after_hours) else 'market'
        limit_price = None
        if order_type == 'limit':
            if not price:
                raise ValueError("Price required for limit order")
            # Small buffer under current price
            limit_price = round(min(price * 0.995, price - 0.50), 2)
        print(f"\nPlacing SELL order: {qty} {symbol} | type={order_type} | limit_price={limit_price} | extended_hours={getattr(alpaca,'extended_hours', False)}")
        return alpaca.place_sell_order(symbol, qty, order_type=order_type, limit_price=limit_price)
    finally:
        setattr(alpaca, 'extended_hours', original_ext)


def main():
    parser = argparse.ArgumentParser(description='Test cash/buying power and VOO trade execution')
    parser.add_argument('--action', choices=['info', 'buy', 'sell', 'affordable'], default='info', help='What to do: info (print balances), buy, sell, or affordable (max shares)')
    parser.add_argument('--qty', type=int, default=1, help='Quantity for buy/sell (whole shares)')
    parser.add_argument('--symbol', type=str, default='VOO', help='Ticker to trade (default VOO)')
    parser.add_argument('--after-hours', action='store_true', help='Enable extended-hours for the order')
    parser.add_argument('--limit', action='store_true', help='Use limit order with small buffer')
    parser.add_argument('--limit-price', type=float, default=None, help='Explicit limit price to use (overrides lookup)')
    args = parser.parse_args()

    print("[TEST] Starting VOO cash sweep test script...")
    alpaca = AlpacaService()

    ok = print_account_info(alpaca)
    if not ok:
        sys.exit(1)

    symbol = args.symbol.upper()
    print(f"[TEST] Action={args.action} | Symbol={symbol} | Qty={args.qty} | AfterHours={args.after_hours} | Limit={args.limit} | LimitPrice={args.limit_price}")
    price: Optional[float] = None
    if args.action in ('buy', 'sell'):
        price = args.limit_price if args.limit_price is not None else get_voo_price(symbol)

    if args.action == 'affordable':
        shares = get_max_affordable_shares(symbol, prefer_buying_power=True, alpaca=alpaca)
        print(f"\nMax affordable whole shares of {symbol} using buying power: {shares}")
        return

    if args.action == 'info':
        print("\nNo trade placed. Use --action buy/sell to test orders.")
        return

    # Determine safe quantity based on available cash/position
    if args.action == 'buy':
        info = alpaca.get_account_info()
        cash = float(info.get('cash') or 0)
        if (args.limit or args.after_hours) and (price is None or price <= 0):
            print("[ERROR] Cannot place buy: missing/invalid price and limit/after-hours requested. Provide --limit-price.")
            sys.exit(1)
        if price is not None and price > 0:
            max_affordable = int(cash // price)
        else:
            # For market orders without limit/after-hours, just use requested qty
            max_affordable = args.qty
        qty = max(0, min(args.qty, max_affordable))
        if qty <= 0:
            print(f"[ERROR] Insufficient cash to buy {args.qty} shares at price {price}")
            sys.exit(1)
        result = place_buy(alpaca, symbol, qty, price, after_hours=args.after_hours, use_limit=args.limit)
        print("\nOrder result:")
        print(result)
        return

    if args.action == 'sell':
        # Try to fetch current position
        pos = None
        try:
            pos = alpaca.get_position(symbol)
        except Exception:
            pos = None
        held = int(pos.get('quantity') or 0) if pos else 0
        if held <= 0:
            print(f"[ERROR] No position in {symbol} to sell.")
            sys.exit(1)
        qty = max(0, min(args.qty, held))
        if qty <= 0:
            print(f"[ERROR] Sell quantity invalid: requested={args.qty}, held={held}")
            sys.exit(1)
        if (args.limit or args.after_hours) and (price is None or price <= 0):
            sys.exit(1)
        result = place_sell(alpaca, symbol, qty, price, after_hours=args.after_hours, use_limit=args.limit)
        print("\nOrder result:")
        print(result)
        return

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        import traceback
        print("[ERROR] Unhandled exception in test script:")
        traceback.print_exc()
        sys.exit(1)
