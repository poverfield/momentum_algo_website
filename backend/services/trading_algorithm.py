from __future__ import annotations
"""
Core Trading Algorithm Service - Production version of TradingBacktest class
Implements the 3-factor momentum-based trading strategy
"""
import os
import logging
import pandas as pd
import numpy as np
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
            
            # Check if market is open (unless after-hours execution is allowed)
            if not self.market_data.is_market_open() and not self.allow_after_hours:
                logger.info("Market is closed, skipping algorithm run (set ALLOW_AFTER_HOURS=true to override)")
                return {'status': 'market_closed', 'message': 'Market is not open'}
            
            # Step 1: Generate buy signals
            buy_signals = self.generate_daily_signals(run_date)
            logger.info(f"Generated {len(buy_signals)} buy signals")
            
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
                
                # Execute buy orders
                for buy_signal in buy_signals:
                    if self.execute_buy_order(buy_signal):
                        trades_executed += 1
            else:
                logger.info("Trading disabled - signals generated but no trades executed")
            
            # Step 4: Log signals to database
            all_signals = buy_signals + sell_signals
            if all_signals:
                self.db.log_daily_signals(all_signals)
            
            # Step 5: Log algorithm run
            execution_time = int(time.time() - start_time)
            top_momentum_stocks = [signal['symbol'] for signal in buy_signals[:30]]
            
            self.db.log_algorithm_run(
                run_date=run_date,
                status='success',
                signals_generated=len(all_signals),
                trades_executed=trades_executed,
                execution_time=execution_time,
                top_momentum_stocks=top_momentum_stocks
            )
            
            logger.info(f"Algorithm run completed successfully in {execution_time}s - "
                       f"{len(all_signals)} signals, {trades_executed} trades")
            
            return {
                'status': 'success',
                'signals_generated': len(all_signals),
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
    
    def generate_daily_signals(self, signal_date: date) -> List[Dict]:
        """
        Generate buy signals based on momentum + technical analysis
        Returns list of buy signals sorted by signal strength
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
            signals = []
            passed_macd = []
            passed_rsi = []
            passed_both = []
            for symbol in top_momentum.index:
                try:
                    # Get technical indicators for this stock
                    macd_data = self.market_data.calculate_macd(market_data[symbol])
                    rsi_data = self.market_data.calculate_rsi(market_data[symbol])
                    
                    if macd_data is None or rsi_data is None:
                        continue
                    
                    # Check MACD bullish condition
                    macd_bullish = self.check_macd_bullish(macd_data)
                    
                    # Check RSI signal
                    rsi_bullish = self.check_rsi_bullish(rsi_data)
                    
                    # Calculate signal strength if filters pass
                    filters_ok = (macd_bullish and rsi_bullish) or (self.relaxed_filters and (macd_bullish or rsi_bullish))
                    if filters_ok:
                        passed_both.append(symbol)
                        momentum_rank = list(top_momentum.index).index(symbol) + 1
                        momentum_value = top_momentum[symbol]
                        
                        # Signal strength calculation (momentum 40%, MACD 30%, RSI 30%)
                        momentum_strength = (31 - momentum_rank) / 30  # Higher rank = higher strength
                        macd_strength = min(abs(macd_data['macd'].iloc[-1]) / 2, 1)  # Normalize MACD
                        rsi_strength = min((rsi_data['rsi'].iloc[-1] - 50) / 50, 1)  # RSI above 50
                        
                        signal_strength = (momentum_strength * 0.4 + 
                                         macd_strength * 0.3 + 
                                         rsi_strength * 0.3)
                        
                        signals.append({
                            'signal_date': signal_date,
                            'symbol': symbol,
                            'signal_strength': round(signal_strength, 4),
                            'momentum_rank': momentum_rank,
                            'momentum_value': round(momentum_value, 6),
                            'macd_value': round(macd_data['macd'].iloc[-1], 6),
                            'rsi_value': round(rsi_data['rsi'].iloc[-1], 2),
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
            return signals
            
        except Exception as e:
            logger.error(f"Error generating daily signals: {e}")
            return []
    
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
                
                try:
                    # Get current price
                    current_price = self.market_data.get_current_price(symbol)
                    if current_price is None:
                        logger.warning(f"Could not get current price for {symbol}")
                        continue
                    
                    # Check stop loss (7% loss)
                    loss_pct = (entry_price - current_price) / entry_price
                    if loss_pct >= self.stop_loss:
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
            
            current_macd = macd_data['macd'].iloc[-1]
            prev_macd = macd_data['macd'].iloc[-2]
            
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
            
            quantity = int(position_value / current_price)
            if quantity <= 0:
                signal['action_taken'] = 'insufficient_funds'
                return False
            
            # Execute the trade through Alpaca
            if getattr(self.alpaca, 'extended_hours', False):
                # Extended hours require DAY limit orders. Add small buffer over current price.
                limit_price = round(max(current_price * 1.005, current_price + 0.50), 2)
                order_result = self.alpaca.place_buy_order(symbol, quantity, order_type='limit', limit_price=limit_price)
            else:
                order_result = self.alpaca.place_buy_order(symbol, quantity, order_type='market')
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
            quantity = signal['quantity']
            entry_price = signal['entry_price']
            current_price = signal['current_price']
            
            # Execute the trade through Alpaca
            if getattr(self.alpaca, 'extended_hours', False):
                # Extended hours require DAY limit orders. Add small buffer under current price.
                limit_price = round(min(current_price * 0.995, current_price - 0.50), 2)
                order_result = self.alpaca.place_sell_order(symbol, quantity, order_type='limit', limit_price=limit_price)
            else:
                order_result = self.alpaca.place_sell_order(symbol, quantity, order_type='market')
            if order_result['success']:
                # Calculate P&L
                pnl = (current_price - entry_price) * quantity
                
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
                
                signal['action_taken'] = 'sold'
                logger.info(f"Successfully sold {quantity} shares of {symbol} @ ${current_price} "
                           f"(P&L: ${pnl:.2f})")
                return True
            else:
                signal['action_taken'] = 'order_failed'
                logger.error(f"Failed to sell {symbol}: {order_result.get('error', 'Unknown error')}")
                return False
                
        except Exception as e:
            logger.error(f"Error executing sell order for {signal['symbol']}: {e}")
            signal['action_taken'] = 'error'
            return False
