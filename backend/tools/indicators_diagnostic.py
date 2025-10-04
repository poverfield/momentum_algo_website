"""
Indicators Diagnostic

Quick script to verify MACD/RSI filter behavior over recent data.
- Loads tickers from the configured CSV (or uses a provided list)
- Pulls ~600 calendar days of daily closes
- Computes MACD + RSI using MarketDataService
- Prints how many pass MACD, how many pass RSI, and overlap
"""
import os
import sys
from datetime import date

# Ensure backend package imports work when run directly
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.market_data_service import MarketDataService


def run(symbols=None, top_n=30, sample_n=50, days_back=600):
    md = MarketDataService()

    # Load universe
    tickers = symbols or md.get_sp500_tickers()
    if not tickers:
        print("No tickers available")
        return

    # Use a manageable subset for speed
    subset = tickers[:sample_n]
    print(f"Using {len(subset)} symbols for diagnostics: {subset[:10]}{'...' if len(subset) > 10 else ''}")

    # Fetch data
    market_data = md.get_daily_market_data(date.today(), subset, days_back=days_back)
    if market_data.empty:
        print("No market data retrieved. Try increasing days_back or check network.")
        return

    print(f"Data shape: days={market_data.shape[0]}, symbols={market_data.shape[1]}")

    # Compute MACD + RSI and count
    passed_macd = []
    passed_rsi = []
    passed_both = []

    for symbol in market_data.columns:
        s = market_data[symbol].dropna()
        macd_df = md.calculate_macd(s)
        rsi_df = md.calculate_rsi(s)
        if macd_df is None or rsi_df is None:
            continue

        # Simple bullish checks (same as TradingAlgorithm)
        try:
            macd_bullish = False
            if len(macd_df) >= 2:
                current_macd = macd_df['macd'].iloc[-1]
                prev_macd = macd_df['macd'].iloc[-2]
                macd_bullish = (current_macd > 0 and prev_macd <= 0) or (current_macd > prev_macd and current_macd > 0)

            rsi_bullish = False
            if len(rsi_df) >= 2:
                current_rsi = rsi_df['rsi'].iloc[-1]
                prev_rsi = rsi_df['rsi'].iloc[-2]
                rsi_bullish = (current_rsi > 50 and prev_rsi <= 50) or (current_rsi > 30 and prev_rsi <= 30)

            if macd_bullish:
                passed_macd.append(symbol)
            if rsi_bullish:
                passed_rsi.append(symbol)
            if macd_bullish and rsi_bullish:
                passed_both.append(symbol)
        except Exception as e:
            print(f"Error evaluating {symbol}: {e}")
            continue

    print("Diagnostics summary:")
    print(f"  MACD_ok: {len(passed_macd)} -> {passed_macd[:10]}")
    print(f"  RSI_ok : {len(passed_rsi)} -> {passed_rsi[:10]}")
    print(f"  Both_ok: {len(passed_both)} -> {passed_both[:10]}")


if __name__ == "__main__":
    # Optional: allow specifying a few tickers via env var DIAG_TICKERS="AAPL,MSFT,NVDA"
    tickers_env = os.getenv("DIAG_TICKERS")
    symbols = [t.strip().upper() for t in tickers_env.split(',')] if tickers_env else None
    run(symbols=symbols, top_n=30, sample_n=int(os.getenv("DIAG_SAMPLE_N", "50")), days_back=int(os.getenv("DIAG_DAYS_BACK", "600")))
