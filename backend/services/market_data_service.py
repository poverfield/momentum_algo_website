from __future__ import annotations
"""
Market Data Service - Handles data fetching and technical analysis
"""
import os
import logging
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, date, timedelta
import requests
import time

logger = logging.getLogger(__name__)

class MarketDataService:
    def __init__(self):
        self.data_source = os.getenv('DATA_SOURCE', 'yfinance')
        self.market_timezone = os.getenv('MARKET_TIMEZONE', 'America/New_York')
        self.tickers_csv_path = os.getenv(
            'TICKERS_CSV_PATH',
            os.path.normpath(os.path.join(os.path.dirname(__file__), '..', 'data', 'tickers.csv'))
        )
        # Default historical lookback in calendar days (used when not explicitly provided)
        # 600 calendar days ~ 400 trading days, sufficient for 12-1 momentum (needs >=252 trading days)
        try:
            self.default_lookback_days = int(os.getenv('MARKET_LOOKBACK_DAYS', '600'))
        except Exception:
            self.default_lookback_days = 600
        
        # Cache for S&P 500 tickers (refresh daily)
        self._sp500_tickers = None
        self._sp500_last_updated = None
        
        logger.info(
            f"MarketDataService initialized | data_source={self.data_source} | "
            f"market_timezone={self.market_timezone} | tickers_csv_path={self.tickers_csv_path}"
        )
    
    def get_sp500_tickers(self):
        """
        Get S&P 500 (or chosen universe) ticker list from a local CSV file.
        Uses cached version if updated today, otherwise reloads from disk.
        """
        try:
            # Check if we need to refresh cache
            today = date.today()
            if (self._sp500_tickers is None or 
                self._sp500_last_updated is None or 
                self._sp500_last_updated < today):
                logger.info(
                    f"Loading ticker universe from CSV file... exists={os.path.exists(self.tickers_csv_path)}"
                )

                tickers = []
                try:
                    if os.path.exists(self.tickers_csv_path):
                        df = pd.read_csv(self.tickers_csv_path)
                        logger.info(
                            f"Tickers CSV loaded: rows={len(df)} | columns={list(df.columns)}"
                        )
                        # Accept either 'symbol' or 'Symbol' column
                        col = 'symbol' if 'symbol' in df.columns else ('Symbol' if 'Symbol' in df.columns else None)
                        if col:
                            tickers = df[col].dropna().astype(str).tolist()
                            logger.info(f"Raw tickers read: count={len(tickers)} | sample={tickers[:10]}")
                        else:
                            logger.warning("Tickers CSV missing 'symbol' column. Expected header 'symbol'.")
                    else:
                        logger.warning(f"Tickers CSV not found at {self.tickers_csv_path}")
                except Exception as e:
                    logger.exception(f"Failed to read tickers CSV: {e}")

                if not tickers:
                    # Fallback: Use a static list of major S&P 500 stocks
                    self._sp500_tickers = self._get_fallback_tickers()
                    self._sp500_last_updated = today
                    logger.info(f"Using fallback ticker list with {len(self._sp500_tickers)} stocks")
                else:
                    # Clean up tickers (replace dots for Yahoo Finance compatibility)
                    cleaned_tickers = []
                    for ticker in tickers:
                        cleaned_ticker = ticker.strip().upper().replace('.', '-')
                        if cleaned_ticker:
                            cleaned_tickers.append(cleaned_ticker)

                    # De-duplicate while preserving order
                    seen = set()
                    unique_clean = [t for t in cleaned_tickers if not (t in seen or seen.add(t))]

                    self._sp500_tickers = unique_clean
                    self._sp500_last_updated = today
                    logger.info(
                        f"Loaded {len(self._sp500_tickers)} tickers from CSV | sample={self._sp500_tickers[:10]}"
                    )
            
            return self._sp500_tickers
            
        except Exception as e:
            logger.exception(f"Error getting S&P 500 tickers: {e}")
            return self._get_fallback_tickers()
    
    def _get_fallback_tickers(self):
        """Fallback list of major S&P 500 stocks"""
        return [
            'AAPL', 'MSFT', 'AMZN', 'NVDA', 'GOOGL', 'TSLA', 'GOOG', 'META', 'UNH', 'XOM',
            'LLY', 'JNJ', 'JPM', 'V', 'PG', 'MA', 'HD', 'CVX', 'MRK', 'ABBV',
            'PEP', 'KO', 'AVGO', 'PFE', 'TMO', 'COST', 'WMT', 'BAC', 'CRM', 'ACN',
            'NFLX', 'LIN', 'AMD', 'CSCO', 'ABT', 'DHR', 'TXN', 'VZ', 'ADBE', 'NKE',
            'WFC', 'COP', 'BMY', 'RTX', 'QCOM', 'PM', 'T', 'UPS', 'SPGI', 'LOW'
        ]
    
    def get_daily_market_data(self, target_date, tickers, days_back: int = None):
        """
        Get daily OHLCV data for multiple tickers
        Returns DataFrame with tickers as columns and dates as index
        """
        try:
            logger.info(f"Fetching market data for {len(tickers)} tickers")
            
            # Calculate date range
            if days_back is None:
                days_back = self.default_lookback_days
            end_date = target_date + timedelta(days=1)  # Include target date
            start_date = target_date - timedelta(days=days_back)
            
            # Prepare a custom session with a common desktop user-agent to reduce blocks
            session = requests.Session()
            session.headers.update({
                'User-Agent': (
                    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                    'AppleWebKit/537.36 (KHTML, like Gecko) '
                    'Chrome/115.0 Safari/537.36'
                )
            })

            # Fetch data in batches to avoid API limits
            batch_size = 50
            all_data = {}
            
            for i in range(0, len(tickers), batch_size):
                batch_tickers = tickers[i:i + batch_size]
                logger.info(f"Fetching batch {i//batch_size + 1}/{(len(tickers)-1)//batch_size + 1}")
                
                try:
                    # Download data for this batch
                    batch_data = yf.download(
                        batch_tickers,
                        start=start_date,
                        end=end_date,
                        progress=False,
                        group_by='ticker',
                        threads=False,
                        auto_adjust=True
                    )
                    
                    # Process each ticker in the batch
                    for ticker in batch_tickers:
                        try:
                            if len(batch_tickers) == 1:
                                # Single ticker - data is not grouped
                                ticker_data = batch_data['Close']
                            else:
                                # Multiple tickers - data is grouped by ticker
                                ticker_data = batch_data[ticker]['Close']
                            
                            # Only include if we have sufficient data
                            if len(ticker_data.dropna()) >= 100:  # At least 100 days of data
                                all_data[ticker] = ticker_data
                            else:
                                logger.debug(f"Insufficient data in batch for {ticker} (len={len(ticker_data.dropna())})")
                            
                        except Exception as e:
                            logger.warning(f"Error processing {ticker}: {e}")
                            continue
                    
                    # Small delay to be respectful to the API
                    time.sleep(0.1)
                    
                except Exception as e:
                    logger.warning(f"Error fetching batch starting at index {i}: {e}")
                    continue

            # If batch approach yielded little/no data, try per-symbol fallback for a subset
            if not all_data:
                logger.warning("Batch download returned no data. Trying per-symbol fallback for first 50 tickers...")
                fallback_count = 0
                for symbol in tickers[:50]:
                    try:
                        t = yf.Ticker(symbol)
                        hist = t.history(period='400d', interval='1d', auto_adjust=False)
                        if not hist.empty and 'Close' in hist:
                            series = hist['Close']
                            if len(series.dropna()) >= 100:
                                all_data[symbol] = series
                                fallback_count += 1
                        else:
                            logger.debug(f"Fallback history empty for {symbol}")
                        time.sleep(0.05)
                    except Exception as e:
                        logger.warning(f"Fallback fetch failed for {symbol}: {e}")
                        continue
                logger.info(f"Per-symbol fallback added {fallback_count} series")

            # Final fallback: Try Stooq CSV per-symbol for first 100 tickers
            if not all_data:
                logger.warning("Per-symbol yfinance fallback returned no data. Trying Stooq CSV fallback for first 100 tickers...")
                stooq_count = 0
                for symbol in tickers[:100]:
                    try:
                        sym = symbol.lower()
                        url = f"https://stooq.com/q/d/l/?s={sym}&i=d"
                        csv = session.get(url, timeout=10)
                        if csv.status_code == 200 and csv.text and 'Date,Open,High,Low,Close,Volume' in csv.text:
                            df = pd.read_csv(pd.compat.StringIO(csv.text)) if hasattr(pd, 'compat') else pd.read_csv(__import__('io').StringIO(csv.text))
                            if not df.empty and 'Close' in df.columns:
                                df['Date'] = pd.to_datetime(df['Date'])
                                df.set_index('Date', inplace=True)
                                series = df['Close']
                                if len(series.dropna()) >= 100:
                                    all_data[symbol] = series
                                    stooq_count += 1
                        else:
                            logger.debug(f"Stooq response invalid for {symbol}: status={csv.status_code}")
                        time.sleep(0.05)
                    except Exception as e:
                        logger.warning(f"Stooq fetch failed for {symbol}: {e}")
                        continue
                logger.info(f"Stooq fallback added {stooq_count} series")

            if not all_data:
                logger.error("No market data retrieved")
                return pd.DataFrame()
            
            # Combine all data into single DataFrame
            market_data = pd.DataFrame(all_data)
            
            # Forward fill missing values (weekends, holidays)
            market_data = market_data.fillna(method='ffill')
            
            logger.info(f"Successfully retrieved data for {len(market_data.columns)} tickers, "
                       f"{len(market_data)} days")
            
            return market_data
            
        except Exception as e:
            logger.exception(f"Error getting daily market data: {e}")
            return pd.DataFrame()
    
    def get_current_price(self, symbol):
        """Get current/latest price for a symbol"""
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            
            # Try different price fields
            price = (info.get('regularMarketPrice') or 
                    info.get('currentPrice') or 
                    info.get('previousClose'))
            
            if price:
                return float(price)
            
            # Fallback: get latest close from history
            hist = ticker.history(period='1d')
            if not hist.empty:
                return float(hist['Close'].iloc[-1])
            
            return None
            
        except Exception as e:
            logger.exception(f"Error getting current price for {symbol}: {e}")
            return None
    
    def calculate_macd(self, price_data, fast: int = 12, slow: int = 26, signal: int = 9):
        """
        Calculate MACD indicator
        Returns DataFrame with MACD, signal line, and histogram
        """
        try:
            if len(price_data) < slow + signal:
                return None
            
            # Calculate exponential moving averages
            ema_fast = price_data.ewm(span=fast).mean()
            ema_slow = price_data.ewm(span=slow).mean()
            
            # MACD line
            macd_line = ema_fast - ema_slow
            
            # Signal line
            signal_line = macd_line.ewm(span=signal).mean()
            
            # Histogram
            histogram = macd_line - signal_line
            
            return pd.DataFrame({
                'macd': macd_line,
                'signal': signal_line,
                'histogram': histogram
            })
            
        except Exception as e:
            logger.exception(f"Error calculating MACD: {e}")
            return None
    
    def calculate_rsi(self, price_data, period: int = 14):
        """
        Calculate RSI indicator
        Returns DataFrame with RSI values
        """
        try:
            if len(price_data) < period + 1:
                return None
            
            # Calculate price changes
            delta = price_data.diff()
            
            # Separate gains and losses
            gains = delta.where(delta > 0, 0)
            losses = -delta.where(delta < 0, 0)
            
            # Calculate average gains and losses
            avg_gains = gains.rolling(window=period).mean()
            avg_losses = losses.rolling(window=period).mean()
            
            # Calculate RS and RSI
            rs = avg_gains / avg_losses
            rsi = 100 - (100 / (1 + rs))
            
            return pd.DataFrame({'rsi': rsi})
            
        except Exception as e:
            logger.exception(f"Error calculating RSI: {e}")
            return None
    
    def calculate_technical_indicators(self, price_data):
        """
        Calculate technical indicators for all symbols in price_data
        Returns dict with symbol -> indicators mapping
        """
        try:
            indicators = {}
            
            for symbol in price_data.columns:
                try:
                    symbol_data = price_data[symbol].dropna()
                    if len(symbol_data) < 50:  # Need minimum data
                        continue
                    
                    # Calculate MACD and RSI
                    macd_data = self.calculate_macd(symbol_data)
                    rsi_data = self.calculate_rsi(symbol_data)
                    
                    if macd_data is not None and rsi_data is not None:
                        indicators[symbol] = {
                            'macd': macd_data,
                            'rsi': rsi_data
                        }
                    
                except Exception as e:
                    logger.warning(f"Error calculating indicators for {symbol}: {e}")
                    continue
            
            logger.info(f"Calculated technical indicators for {len(indicators)} symbols")
            return indicators
            
        except Exception as e:
            logger.exception(f"Error calculating technical indicators: {e}")
            return {}
    
    def is_market_open(self) -> bool:
        """
        Check if the US stock market is currently open
        """
        try:
            # Get current time in market timezone
            import pytz
            market_tz = pytz.timezone(self.market_timezone)
            now = datetime.now(market_tz)
            
            # Check if it's a weekday
            if now.weekday() >= 5:  # Saturday = 5, Sunday = 6
                return False
            
            # Check if it's during market hours (9:30 AM - 4:00 PM ET)
            market_open = now.replace(hour=9, minute=30, second=0, microsecond=0)
            market_close = now.replace(hour=16, minute=0, second=0, microsecond=0)
            
            is_open = market_open <= now <= market_close
            
            # TODO: Add holiday checking
            # For now, just check basic hours
            
            return is_open
            
        except Exception as e:
            logger.exception(f"Error checking market hours: {e}")
            # Default to True during weekdays if we can't determine
            now = datetime.now()
            return now.weekday() < 5
    
    def get_market_calendar(self, start_date, end_date):
        """
        Get list of trading days between start_date and end_date
        """
        try:
            # Simple implementation - exclude weekends
            # TODO: Add proper holiday calendar
            trading_days = []
            current_date = start_date
            
            while current_date <= end_date:
                if current_date.weekday() < 5:  # Monday = 0, Friday = 4
                    trading_days.append(current_date)
                current_date += timedelta(days=1)
            
            return trading_days
            
        except Exception as e:
            logger.exception(f"Error getting market calendar: {e}")
            return []
    
    def validate_symbol(self, symbol: str) -> bool:
        """
        Validate if a symbol exists and has data
        """
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            
            # Check if we got valid info
            return 'symbol' in info or 'shortName' in info
            
        except Exception as e:
            logger.exception(f"Error validating symbol {symbol}: {e}")
            return False
