from __future__ import annotations
"""
Core Trading Algorithm Service - Production version of TradingBacktest class
Implements the 3-factor momentum-based trading strategy
"""
import os
import logging
import pandas as pd
import numpy as np
import requests
from datetime import datetime, date, timedelta
from typing import List, Dict, Optional, Tuple
import time

logger = logging.getLogger(__name__)

class TradingAlgorithm:
    def __init__(self, alpaca_service, db_service, market_data_service):
        self.alpaca = alpaca_service
        self.db = db_service
        self.market_data = market_data_service
        
        # Algorithm parameters from environment
        self.max_positions = int(os.getenv('MAX_POSITIONS', 15))
        self.stop_loss = float(os.getenv('STOP_LOSS_PERCENT', 0.07))
        self.initial_capital = float(os.getenv('INITIAL_CAPITAL', 50000))
        self.trading_enabled = os.getenv('TRADING_ENABLED', 'false').lower() == 'true'
        # Allow running the algorithm outside regular market hours
        self.allow_after_hours = os.getenv('ALLOW_AFTER_HOURS', 'false').lower() == 'true'
        # Relax technical filters for demo/testing: allow MACD OR RSI instead of both
        self.relaxed_filters = os.getenv('RELAXED_FILTERS', 'false').lower() == 'true'
        # Cash sweep configuration
        self.cash_etf = os.getenv('CASH_ETF_TICKER', 'VOO')
        # Default 5% buffer as requested
        self.cash_buffer_pct = float(os.getenv('CASH_BUFFER_PCT', 0.05))
        # Allow sweeps to use extended hours with limit orders
        self.cash_sweep_after_hours = os.getenv('CASH_SWEEP_AFTER_HOURS', 'true').lower() == 'true'
        # Hard safety: the strategy does not short. Keep this true.
        self.no_shorts = True
        
        logger.info(f"TradingAlgorithm initialized - Max positions: {self.max_positions}, "
                   f"Stop loss: {self.stop_loss*100}%, Trading enabled: {self.trading_enabled}")
    
    def run_daily_algorithm(self) -> Dict:
        """
        Main entry point for daily algorithm execution
        Returns summary of algorithm run
        """
        start_time = time.time()
        run_date = date.today()
        
        try:
            logger.info(f"Starting daily algorithm run for {run_date}")
            # Sync DB positions with live Alpaca positions before making decisions
            try:
                self.sync_positions_from_alpaca(run_date)
            except Exception as sync_e:
                logger.warning(f"Pre-run position sync failed: {sync_e}")
            # Optional audit: detect any short positions and warn
            try:
                live_positions = self.alpaca.get_positions() or []
                short_syms = [p['symbol'] for p in live_positions if str(p.get('side', '')).lower() == 'short']
                if short_syms:
                    logger.error(f"Short positions detected but strategy forbids shorts: {short_syms}")
            except Exception as audit_e:
                logger.warning(f"Short audit skipped due to error: {audit_e}")
            
            # Check if market is open (unless after-hours execution is allowed)
            if not self.market_data.is_market_open() and not self.allow_after_hours:
                logger.info("Market is closed, skipping algorithm run (set ALLOW_AFTER_HOURS=true to override)")
                return {'status': 'market_closed', 'message': 'Market is not open'}
            
            # Step 1: Generate top-30 set and buy signals
            buy_signals, top30_rows = self.generate_daily_signals(run_date)
            logger.info(f"Generated {len(buy_signals)} buy signals (within top-30 universe)")
            
            # Step 2: Check sell signals for existing positions
            sell_signals = self.check_sell_signals(run_date)
            logger.info(f"Generated {len(sell_signals)} sell signals")
            
            # Step 3: Execute trades if trading is enabled
            trades_executed = 0
            if self.trading_enabled:
                # Execute sell orders first
                for sell_signal in sell_signals:
                    if self.execute_sell_order(sell_signal):
                        trades_executed += 1
                
                # Pre-sell minimal VOO only if needed to fund upcoming buys
                try:
                    self.plan_and_sell_voo_for_buys(run_date, buy_signals)
                except Exception as plan_e:
                    logger.warning(f"VOO funding plan step skipped due to error: {plan_e}")

                # Execute buy orders
                for buy_signal in buy_signals:
                    if self.execute_buy_order(buy_signal):
                        trades_executed += 1
            else:
                logger.info("Trading disabled - signals generated but no trades executed")
            
            # Step 4: Log signals to database
            # Persist ONLY the full top-30 momentum set (for UI). Do not write sell signals to this table.
            rows_to_log = (top30_rows or [])
            if rows_to_log:
                self.db.log_daily_signals(rows_to_log)
            
            # Step 5: Log algorithm run
            execution_time = int(time.time() - start_time)
            top_momentum_stocks = [row['symbol'] for row in top30_rows[:30]]
            
            self.db.log_algorithm_run(
                run_date=run_date,
                status='success',
                signals_generated=len(rows_to_log),
                trades_executed=trades_executed,
                execution_time=execution_time,
                top_momentum_stocks=top_momentum_stocks
            )
            
            # Step 6: Cash sweep into VOO after other trades (after-hours allowed)
            try:
                if self.trading_enabled:
                    self.invest_excess_cash_in_cash_etf(run_date)
            except Exception as sweep_e:
                logger.warning(f"Cash sweep step failed: {sweep_e}")
            
            logger.info(f"Algorithm run completed successfully in {execution_time}s - "
                       f"{len(rows_to_log)} signals, {trades_executed} trades")
            
            return {
                'status': 'success',
                'signals_generated': len(rows_to_log),
                'trades_executed': trades_executed,
                'execution_time': execution_time,
                'buy_signals': len(buy_signals),
                'sell_signals': len(sell_signals)
            }
            
        except Exception as e:
            execution_time = int(time.time() - start_time)
            error_msg = str(e)
            logger.error(f"Algorithm run failed: {error_msg}")
            
            # Log failed run
            self.db.log_algorithm_run(
                run_date=run_date,
                status='error',
                error_message=error_msg,
                execution_time=execution_time
            )
            
            return {
                'status': 'error',
                'error': error_msg,
                'execution_time': execution_time
            }
        

    def generate_daily_signals(self, signal_date: date) -> Tuple[List[Dict], List[Dict]]:
        """
        Generate buy signals based on momentum + technical analysis
        Returns tuple: (buy_signals_sorted, top30_rows_for_logging)
        """
        try:
            logger.info("Generating daily buy signals...")
            
            # Step 1: Get S&P 500 tickers
            sp500_tickers = self.market_data.get_sp500_tickers()
            logger.info(f"Analyzing {len(sp500_tickers)} S&P 500 stocks")
            
            # Step 2: Get market data for all tickers
            market_data = self.market_data.get_daily_market_data(signal_date, sp500_tickers)
            if market_data.empty:
                logger.warning("No market data available")
                return []
            
            # Step 3: Calculate momentum rankings (12-1 strategy)
            momentum_scores = self.calculate_momentum_12_1(market_data)
            
            # Step 4: Get top 30 momentum stocks
            top_momentum = momentum_scores.head(30)
            logger.info(f"Top 30 momentum stocks identified")
            
            # Step 5: Apply technical filters (MACD + RSI)
            signals: List[Dict] = []  # qualifying buy signals
            top30_rows: List[Dict] = []  # full top-30 for logging/UI
            passed_macd = []
            passed_rsi = []
            passed_both = []
            for symbol in top_momentum.index:
                try:
                    # Get technical indicators for this stock
                    macd_data = self.market_data.calculate_macd(market_data[symbol])
                    rsi_data = self.market_data.calculate_rsi(market_data[symbol])
                    
                    if macd_data is None or rsi_data is None:
                        # Still record a minimal top30 row if indicators missing
                        momentum_rank = list(top_momentum.index).index(symbol) + 1
                        momentum_value = top_momentum[symbol]
                        top30_rows.append({
                            'signal_date': signal_date,
                            'symbol': symbol,
                            'signal_strength': 0.0,
                            'momentum_rank': momentum_rank,
                            'momentum_value': round(float(momentum_value), 6),
                            'macd_value': None,
                            'rsi_value': None,
                            'is_top_momentum': True,
                            'macd_bullish': False,
                            'rsi_bullish': False,
                            'action_taken': None
                        })
                        continue
                    
                    # Check MACD bullish condition
                    macd_bullish = self.check_macd_bullish(macd_data)
                    
                    # Check RSI signal
                    rsi_bullish = self.check_rsi_bullish(rsi_data)
                    
                    # Calculate signal strength if filters pass
                    filters_ok = (macd_bullish and rsi_bullish) or (self.relaxed_filters and (macd_bullish or rsi_bullish))
                    momentum_rank = list(top_momentum.index).index(symbol) + 1
                    momentum_value = top_momentum[symbol]

                    # Compute a consistent signal_strength for logging/UI
                    momentum_strength = (31 - momentum_rank) / 30  # Higher rank = higher strength
                    macd_strength = min(abs(macd_data['histogram'].iloc[-1]) / 2, 1)  # Normalize MACD histogram
                    rsi_strength = min(max((rsi_data['rsi'].iloc[-1] - 50) / 50, 0), 1)  # clamp 0..1
                    signal_strength = (momentum_strength * 0.4 + macd_strength * 0.3 + rsi_strength * 0.3)

                    # Record full top30 row regardless of filter pass
                    top30_rows.append({
                        'signal_date': signal_date,
                        'symbol': symbol,
                        'signal_strength': round(float(signal_strength), 4),
                        'momentum_rank': momentum_rank,
                        'momentum_value': round(float(momentum_value), 6),
                        'macd_value': round(float(macd_data['macd'].iloc[-1]), 6),
                        'rsi_value': round(float(rsi_data['rsi'].iloc[-1]), 2),
                        'is_top_momentum': True,
                        'macd_bullish': macd_bullish,
                        'rsi_bullish': rsi_bullish,
                        'action_taken': None
                    })

                    if filters_ok:
                        passed_both.append(symbol)
                        signals.append({
                            'signal_date': signal_date,
                            'symbol': symbol,
                            'signal_strength': round(float(signal_strength), 4),
                            'momentum_rank': momentum_rank,
                            'momentum_value': round(float(momentum_value), 6),
                            'macd_value': round(float(macd_data['macd'].iloc[-1]), 6),
                            'rsi_value': round(float(rsi_data['rsi'].iloc[-1]), 2),
                            'is_top_momentum': True,
                            'macd_bullish': macd_bullish,
                            'rsi_bullish': rsi_bullish,
                            'action_taken': None  # Will be set during execution
                        })
                    else:
                        if macd_bullish:
                            passed_macd.append(symbol)
                        if rsi_bullish:
                            passed_rsi.append(symbol)
                        
                except Exception as e:
                    logger.warning(f"Error processing {symbol}: {e}")
                    continue
            
            # Sort by signal strength (highest first)
            signals.sort(key=lambda x: x['signal_strength'], reverse=True)
            
            # Diagnostics: how many passed each stage
            mode = 'RELAXED' if self.relaxed_filters else 'STRICT'
            logger.info(
                f"Diagnostics ({mode}) - Top30: {len(top_momentum)} | MACD_ok: {len(passed_macd)} | "
                f"RSI_ok: {len(passed_rsi)} | Pass_ok: {len(passed_both)} | Signals: {len(signals)}"
            )
            if passed_both:
                logger.info(f"Sample both_ok: {passed_both[:5]}")
            elif passed_macd or passed_rsi:
                logger.info(f"Sample macd_ok: {passed_macd[:5]} | rsi_ok: {passed_rsi[:5]}")

            logger.info(f"Generated {len(signals)} qualified buy signals")
            # Ensure top30_rows maintains the original momentum order (already iterated in order)
            return signals, top30_rows
            
        except Exception as e:
            logger.error(f"Error generating daily signals: {e}")
            return [], []

    def check_sell_signals(self, signal_date: date) -> List[Dict]:
        """
        Check existing positions for sell signals
        Returns list of sell signals
        """
        try:
            logger.info("Checking sell signals for existing positions...")
            
            current_positions = self.db.get_current_positions()
            if not current_positions:
                logger.info("No current positions to check")
                return []
            
            sell_signals = []
            
            # Get current market data for positions
            position_symbols = [pos['symbol'] for pos in current_positions]
            market_data = self.market_data.get_daily_market_data(signal_date, position_symbols)
            
            # Get current momentum rankings
            sp500_tickers = self.market_data.get_sp500_tickers()
            all_market_data = self.market_data.get_daily_market_data(signal_date, sp500_tickers)
            momentum_scores = self.calculate_momentum_12_1(all_market_data)
            top_30_symbols = set(momentum_scores.head(30).index)
            
            for position in current_positions:
                symbol = position['symbol']
                entry_price = position['entry_price']
                quantity = position['quantity']
                
                # Do not emit sell signals for the cash ETF; we only sell it when funding buys
                if symbol == self.cash_etf:
                    continue

                try:
                    # Get current price
                    current_price = self.market_data.get_current_price(symbol)
                    if current_price is None:
                        logger.warning(f"Could not get current price for {symbol}")
                        continue
                    
                    # Check stop loss (7% loss). If a broker stop order already exists, skip emitting a software stop.
                    loss_pct = (entry_price - current_price) / entry_price
                    if loss_pct >= self.stop_loss:
                        try:
                            has_broker_stop = self.alpaca.has_open_stop_order(symbol)
                        except Exception:
                            has_broker_stop = False
                        if not has_broker_stop:
                            sell_signals.append({
                                'signal_date': signal_date,
                                'symbol': symbol,
                                'signal_strength': 1.0,  # Stop loss is highest priority
                                'reason': 'stop_loss',
                                'current_price': current_price,
                                'entry_price': entry_price,
                                'quantity': quantity,
                                'loss_pct': round(loss_pct * 100, 2),
                                'action_taken': None
                            })
                            logger.info(f"Stop loss triggered for {symbol}: {loss_pct*100:.1f}% loss")
                            continue
                        else:
                            logger.info(f"Skip software stop for {symbol}; broker stop already open.")
                    
                    # Check if stock dropped out of top 30 momentum
                    if symbol not in top_30_symbols:
                        # Get current momentum rank
                        current_rank = list(momentum_scores.index).index(symbol) + 1 if symbol in momentum_scores.index else 999
                        
                        sell_signals.append({
                            'signal_date': signal_date,
                            'symbol': symbol,
                            'signal_strength': 0.8,  # High priority but below stop loss
                            'reason': 'momentum_exit',
                            'current_price': current_price,
                            'entry_price': entry_price,
                            'quantity': quantity,
                            'current_momentum_rank': current_rank,
                            'action_taken': None
                        })
                        logger.info(f"Momentum exit for {symbol}: dropped to rank {current_rank}")
                    
                except Exception as e:
                    logger.warning(f"Error checking sell signal for {symbol}: {e}")
                    continue
            
            # Sort by signal strength (highest priority first)
            sell_signals.sort(key=lambda x: x['signal_strength'], reverse=True)
            
            logger.info(f"Generated {len(sell_signals)} sell signals")
            return sell_signals
            
        except Exception as e:
            logger.error(f"Error checking sell signals: {e}")
            return []
    
    def calculate_momentum_12_1(self, market_data: pd.DataFrame) -> pd.Series:
        """
        Calculate 12-1 month momentum for all stocks
        Returns Series with momentum scores sorted descending
        """
        try:
            momentum_scores = {}
            
            for symbol in market_data.columns:
                try:
                    prices = market_data[symbol].dropna()
                    if len(prices) < 252:  # Need at least 1 year of data
                        continue
                    
                    # Calculate 12-month and 1-month returns
                    current_price = prices.iloc[-1]
                    price_12m_ago = prices.iloc[-252] if len(prices) >= 252 else prices.iloc[0]
                    price_1m_ago = prices.iloc[-21] if len(prices) >= 21 else prices.iloc[-1]
                    
                    return_12m = (current_price - price_12m_ago) / price_12m_ago
                    return_1m = (current_price - price_1m_ago) / price_1m_ago
                    
                    # 12-1 momentum score
                    momentum_12_1 = return_12m - return_1m
                    momentum_scores[symbol] = momentum_12_1
                    
                except Exception as e:
                    logger.warning(f"Error calculating momentum for {symbol}: {e}")
                    continue
            
            # Convert to Series and sort
            momentum_series = pd.Series(momentum_scores)
            momentum_series = momentum_series.sort_values(ascending=False)
            
            logger.info(f"Calculated momentum for {len(momentum_series)} stocks")
            return momentum_series
            
        except Exception as e:
            logger.error(f"Error calculating momentum scores: {e}")
            return pd.Series()
    
    def check_macd_bullish(self, macd_data: pd.DataFrame) -> bool:
        """Check if MACD shows bullish signal"""
        try:
            if len(macd_data) < 2:
                return False
            
            # changes from claude b/c this is referencing the macd line, when we want to histogram line
            # current_macd = macd_data['macd'].iloc[-1] 
            # prev_macd = macd_data['macd'].iloc[-2]

            current_macd = macd_data['histogram'].iloc[-1]
            prev_macd = macd_data['histogram'].iloc[-2]
            
            # Bullish conditions:
            # 1. MACD crosses above zero
            # 2. MACD is positive and increasing
            bullish_crossover = current_macd > 0 and prev_macd <= 0
            bullish_momentum = current_macd > prev_macd and current_macd > 0
            
            return bullish_crossover or bullish_momentum
            
        except Exception as e:
            logger.warning(f"Error checking MACD bullish: {e}")
            return False
    
    def check_rsi_bullish(self, rsi_data: pd.DataFrame) -> bool:
        """Check if RSI shows bullish signal"""
        try:
            if len(rsi_data) < 2:
                return False
            
            current_rsi = rsi_data['rsi'].iloc[-1]
            prev_rsi = rsi_data['rsi'].iloc[-2]
            
            # Bullish conditions:
            # 1. RSI crosses above 50 (bullish momentum)
            # 2. RSI bounces from oversold (above 30)
            bullish_momentum = current_rsi > 50 and prev_rsi <= 50
            oversold_bounce = current_rsi > 30 and prev_rsi <= 30
            
            return bullish_momentum or oversold_bounce
            
        except Exception as e:
            logger.warning(f"Error checking RSI bullish: {e}")
            return False
    
    # -------------------- Cash Management (VOO) --------------------
    def _get_price_with_fallback(self, symbol: str) -> Optional[float]:
        """Get current/latest price using MarketDataService with a lightweight Stooq fallback."""
        try:
            price = self.market_data.get_current_price(symbol)
            if price is not None and price > 0:
                logger.debug(f"Price ({symbol}) from MarketDataService: {price}")
                return float(price)
        except Exception as e:
            logger.warning(f"Primary price fetch failed for {symbol}: {e}")
        # Stooq fallback: last close CSV
        try:
            sym = f"{symbol.lower()}.us"
            url = f"https://stooq.com/q/d/l/?s={sym}&i=d"
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200 and 'Date,Open,High,Low,Close,Volume' in resp.text:
                lines = resp.text.strip().splitlines()
                if len(lines) >= 2:
                    parts = lines[-1].split(',')
                    if len(parts) >= 5:
                        price = float(parts[4])
                        logger.info(f"Price ({symbol}) from Stooq fallback: {price}")
                        return price
            logger.warning(f"Stooq fallback failed for {symbol}: status={resp.status_code}")
        except Exception as e:
            logger.warning(f"Error in Stooq fallback for {symbol}: {e}")
        return None
    def _get_buying_power(self) -> float:
        try:
            info = self.alpaca.get_account_info()
            if not info:
                return 0.0
            bp_val = info.get('buying_power')
            return float(bp_val) if bp_val is not None else 0.0
        except Exception as e:
            logger.warning(f"Failed to get buying power: {e}")
            return 0.0

    def _get_position_from_db(self, symbol: str) -> Optional[Dict]:
        positions = self.db.get_current_positions()
        for p in positions:
            if p.get('symbol') == symbol:
                return p
        return None

    def sell_cash_etf_for_cash(self, signal_date: date, amount_needed: float) -> float:
        """
        Sell VOO shares to raise cash for a new buy.
        Returns proceeds.
        """
        try:
            # Use live Alpaca qty to avoid overselling that could trigger a short
            live = None
            try:
                live = self.alpaca.get_position(self.cash_etf)
            except Exception:
                live = None
            if not live or int(live.get('quantity') or 0) <= 0:
                return 0.0

            current_price = self._get_price_with_fallback(self.cash_etf)
            if current_price is None or current_price <= 0:
                logger.warning(f"No valid price for {self.cash_etf} when attempting to sell for cash.")
                return 0.0

            held_qty = int(live.get('quantity') or 0)
            shares_to_sell = min(held_qty, int(amount_needed / current_price) + 1)
            if shares_to_sell <= 0:
                return 0.0

            # Temporarily enable extended hours for sweep if requested
            original_ext = getattr(self.alpaca, 'extended_hours', False)
            try:
                logger.info(f"Cash sweep SELL {self.cash_etf}: qty={shares_to_sell}, px={current_price}, after_hours={self.cash_sweep_after_hours}")
                if self.cash_sweep_after_hours:
                    setattr(self.alpaca, 'extended_hours', True)
                    limit_price = round(min(current_price * 0.995, current_price - 0.50), 2)
                    order_result = self.alpaca.place_sell_order(self.cash_etf, shares_to_sell, order_type='limit', limit_price=limit_price)
                else:
                    order_result = self.alpaca.place_sell_order(self.cash_etf, shares_to_sell, order_type='market')

                if not order_result.get('success'):
                    logger.error(f"Failed to sell {self.cash_etf} for cash sweep: {order_result.get('error')}")
                    return 0.0

                proceeds = shares_to_sell * current_price
                logger.info(f"Cash sweep SELL placed, est proceeds=${proceeds:.2f}; order: {order_result}")

                # Log and update DB position (partial or full close)
                entry_price = live.get('avg_entry_price')
                pnl = (current_price - float(entry_price)) * shares_to_sell if entry_price is not None else None
                self.db.log_trade(
                    trade_date=signal_date,
                    symbol=self.cash_etf,
                    action='SELL',
                    quantity=shares_to_sell,
                    price=current_price,
                    entry_price=float(entry_price) if entry_price is not None else None,
                    reason='cash_for_trade',
                    pnl=pnl
                )

                # Update DB to reflect live remaining qty
                remaining_qty = held_qty - shares_to_sell
                if remaining_qty > 0:
                    self.db.update_position(
                        symbol=self.cash_etf,
                        quantity=remaining_qty,
                        avg_entry_price=float(entry_price) if entry_price is not None else current_price,
                        entry_date=signal_date,
                        current_price=current_price
                    )
                else:
                    self.db.remove_position(self.cash_etf)

                logger.info(f"Sold {shares_to_sell} {self.cash_etf} to raise ${proceeds:.2f} for buy")
                return proceeds
            finally:
                # Restore original extended hours setting
                setattr(self.alpaca, 'extended_hours', original_ext)
        except Exception as e:
            logger.error(f"Error selling {self.cash_etf} for cash: {e}")
            return 0.0

    def invest_excess_cash_in_cash_etf(self, signal_date: date) -> bool:
        """
        Invest available cash above buffer into VOO.
        Uses limit orders with small buffer when sweeping after-hours.
        """
        try:
            account_value = self.alpaca.get_account_value()
            buying_power_local = self._get_buying_power()
            price = self._get_price_with_fallback(self.cash_etf)
            if price is None or price <= 0:
                logger.warning(f"Cash sweep BUY skipped: no valid price for {self.cash_etf}")
                return False

            buffer_amt = account_value * self.cash_buffer_pct
            excess_bp = max(0.0, buying_power_local - buffer_amt)
            qty = int(excess_bp / price)
            if qty <= 0:
                logger.info(f"Cash sweep BUY: no excess buying power (buffer={buffer_amt:.2f}, buying_power={buying_power_local:.2f})")
                return False

            # Temporarily enable extended hours for sweep if requested
            original_ext = getattr(self.alpaca, 'extended_hours', False)
            try:
                logger.info(f"Cash sweep BUY {self.cash_etf}: qty={qty}, px={price}, after_hours={self.cash_sweep_after_hours}")
                if self.cash_sweep_after_hours:
                    setattr(self.alpaca, 'extended_hours', True)
                    limit_price = round(max(price * 1.005, price + 0.50), 2)
                    order_result = self.alpaca.place_buy_order(self.cash_etf, qty, order_type='limit', limit_price=limit_price)
                else:
                    order_result = self.alpaca.place_buy_order(self.cash_etf, qty, order_type='market')

                if not order_result.get('success'):
                    acct = self.alpaca.get_account_info() or {}
                    buying_power = acct.get('buying_power')
                    logger.error(
                        f"Failed to buy {self.cash_etf} for cash sweep: {order_result.get('error')} | "
                        f"buying_power={buying_power} px={price:.2f} qty={qty} "
                        f"buffer_amt={buffer_amt:.2f} excess_bp={excess_bp:.2f}"
                    )
                    return False
                logger.info(f"Cash sweep BUY placed; order: {order_result}")

                # Update DB position (add or create)
                existing = self._get_position_from_db(self.cash_etf)
                if existing:
                    old_qty = int(existing['quantity'])
                    old_avg = float(existing.get('entry_price') or existing.get('avg_entry_price') or price)
                    new_qty = old_qty + qty
                    new_avg = ((old_qty * old_avg) + (qty * price)) / new_qty if new_qty > 0 else price
                    self.db.update_position(
                        symbol=self.cash_etf,
                        quantity=new_qty,
                        avg_entry_price=new_avg,
                        entry_date=existing.get('entry_date') or signal_date,
                        current_price=price
                    )
                else:
                    self.db.update_position(
                        symbol=self.cash_etf,
                        quantity=qty,
                        avg_entry_price=price,
                        entry_date=signal_date,
                        current_price=price
                    )

                self.db.log_trade(
                    trade_date=signal_date,
                    symbol=self.cash_etf,
                    action='BUY',
                    quantity=qty,
                    price=price,
                    signal_strength=0.0,
                    reason='cash_sweep'
                )

                logger.info(f"Cash sweep: bought {qty} {self.cash_etf} at ${price}")
                return True
            finally:
                setattr(self.alpaca, 'extended_hours', original_ext)
        except Exception as e:
            # Enrich error with context
            try:
                acct = self.alpaca.get_account_info() or {}
                buying_power = acct.get('buying_power')
                account_value = self.alpaca.get_account_value()
                buying_power_local = self._get_buying_power()
                logger.error(
                    f"Error investing excess cash in {self.cash_etf}: {e} | buying_power={buying_power} "
                    f"local_bp={buying_power_local:.2f} account_value={account_value:.2f}"
                )
            except Exception:
                logger.error(f"Error investing excess cash in {self.cash_etf}: {e}")
            return False
    
    def execute_buy_order(self, signal: Dict) -> bool:
        """Execute buy order for a signal"""
        try:
            if not self.trading_enabled:
                signal['action_taken'] = 'trading_disabled'
                return False
            
            symbol = signal['symbol']
            
            # Check if we already have this position
            current_positions = self.db.get_current_positions()
            if any(pos['symbol'] == symbol for pos in current_positions):
                signal['action_taken'] = 'already_owned'
                logger.info(f"Already own {symbol}, skipping buy")
                return False
            
            # Check if we have room for more positions
            if len(current_positions) >= self.max_positions:
                signal['action_taken'] = 'max_positions'
                logger.info(f"Max positions reached ({self.max_positions}), skipping {symbol}")
                return False
            
            # Calculate position size (equal weight)
            account_value = self.alpaca.get_account_value()
            position_value = account_value / self.max_positions
            
            # Get current price and calculate quantity
            current_price = self.market_data.get_current_price(symbol)
            if current_price is None:
                signal['action_taken'] = 'no_price'
                return False
            
            # Determine available buying power; if insufficient, sell VOO to cover
            buying_power_local = self._get_buying_power()
            target_qty = int(position_value / current_price)
            if target_qty <= 0:
                signal['action_taken'] = 'insufficient_funds'
                return False

            # Final quantity bounded strictly by available cash; we do not sell VOO here
            quantity = int(min(position_value, buying_power_local) / current_price)
            if quantity <= 0:
                signal['action_taken'] = 'insufficient_funds'
                return False
            
            # Execute the trade through Alpaca
            # Always attach a stop-loss child using OTO. Compute stop trigger from configured percent.
            stop_price = round(current_price * (1.0 - float(self.stop_loss)), 2)
            if getattr(self.alpaca, 'extended_hours', False):
                # Extended hours require DAY limit orders. Add small buffer over current price.
                limit_price = round(max(current_price * 1.005, current_price + 0.50), 2)
                order_result = self.alpaca.place_oto_buy_with_stop(
                    symbol, quantity, stop_price=stop_price, order_type='limit', limit_price=limit_price
                )
            else:
                order_result = self.alpaca.place_oto_buy_with_stop(
                    symbol, quantity, stop_price=stop_price, order_type='market'
                )
            if order_result['success']:
                # Log trade to database
                trade_id = self.db.log_trade(
                    trade_date=signal['signal_date'],
                    symbol=symbol,
                    action='BUY',
                    quantity=quantity,
                    price=current_price,
                    signal_strength=signal['signal_strength'],
                    reason='algorithm'
                )
                
                # Update position in database
                self.db.update_position(
                    symbol=symbol,
                    quantity=quantity,
                    avg_entry_price=current_price,
                    entry_date=signal['signal_date'],
                    current_price=current_price
                )
                
                signal['action_taken'] = 'bought'
                logger.info(f"Successfully bought {quantity} shares of {symbol} @ ${current_price}")
                return True
            else:
                signal['action_taken'] = 'order_failed'
                logger.error(f"Failed to buy {symbol}: {order_result.get('error', 'Unknown error')}")
                return False
                
        except Exception as e:
            logger.error(f"Error executing buy order for {signal['symbol']}: {e}")
            signal['action_taken'] = 'error'
            return False
    
    def execute_sell_order(self, signal: Dict) -> bool:
        """Execute sell order for a signal"""
        try:
            if not self.trading_enabled:
                signal['action_taken'] = 'trading_disabled'
                return False
            
            symbol = signal['symbol']
            # Refresh current price to avoid stale values
            current_price = None
            try:
                current_price = self.market_data.get_current_price(symbol)
            except Exception:
                current_price = signal.get('current_price')
            entry_price = signal.get('entry_price')

            # Determine live quantity from Alpaca; fall back to DB if needed
            live_qty = 0
            try:
                alp_pos = self.alpaca.get_position(symbol)
                if alp_pos and int(alp_pos.get('quantity') or 0) > 0:
                    live_qty = int(alp_pos['quantity'])
            except Exception:
                pass
            if live_qty <= 0:
                # Fallback to DB snapshot
                for p in (self.db.get_current_positions() or []):
                    if p.get('symbol') == symbol:
                        live_qty = int(p.get('quantity') or 0)
                        entry_price = entry_price or float(p.get('entry_price') or 0)
                        break

            if live_qty <= 0:
                signal['action_taken'] = 'no_position'
                logger.info(f"Sell signal for {symbol} but no live shares found; skipping and removing from DB if present")
                try:
                    self.db.remove_position(symbol)
                except Exception:
                    pass
                # Also ensure any open stop-loss orders are cancelled
                try:
                    self.alpaca.cancel_open_stop_orders(symbol)
                except Exception:
                    pass
                return False
            quantity = live_qty  # Sell ALL available shares
            
            # Execute the trade through Alpaca
            if getattr(self.alpaca, 'extended_hours', False):
                # Extended hours require DAY limit orders. Add small buffer under current price.
                limit_price = round(min(current_price * 0.995, current_price - 0.50), 2)
                order_result = self.alpaca.place_sell_order(symbol, quantity, order_type='limit', limit_price=limit_price)
            else:
                order_result = self.alpaca.place_sell_order(symbol, quantity, order_type='market')
            if order_result['success']:
                # Calculate P&L
                pnl = None
                try:
                    if current_price is not None and entry_price is not None:
                        pnl = (current_price - entry_price) * quantity
                except Exception:
                    pnl = None
                
                # Log trade to database
                trade_id = self.db.log_trade(
                    trade_date=signal['signal_date'],
                    symbol=symbol,
                    action='SELL',
                    quantity=quantity,
                    price=current_price,
                    entry_price=entry_price,
                    reason=signal['reason'],
                    pnl=pnl
                )
                
                # Remove position from database
                self.db.remove_position(symbol)
                # Cancel any open stop-loss orders tied to this symbol
                try:
                    cancel_summary = self.alpaca.cancel_open_stop_orders(symbol)
                    if cancel_summary.get('canceled'):
                        logger.info(f"Canceled {cancel_summary['canceled']} open stop orders for {symbol} after SELL")
                except Exception as ce:
                    logger.warning(f"Failed to cancel open stop orders for {symbol} after SELL: {ce}")

                signal['action_taken'] = 'sold'
                logger.info(f"Successfully sold {quantity} shares of {symbol} @ ${current_price} "
                           f"(P&L: ${pnl:.2f})")
                return True
            else:
                logger.error(f"Failed to sell {symbol}: {order_result.get('error', 'Unknown error')}")
                return False
                
        except Exception as e:
            logger.error(f"Error executing sell order for {signal['symbol']}: {e}")
            signal['action_taken'] = 'error'
            return False
