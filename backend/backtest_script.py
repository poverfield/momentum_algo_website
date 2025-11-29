"""
Momentum Trading Strategy Backtest
===================================
A standalone script to backtest a 3-factor momentum trading strategy:
1. 12-1 month momentum ranking
2. MACD technical filter
3. RSI technical filter

Usage:
    python backtest.py

Requirements:
    pip install pandas numpy yfinance talib
"""

import pandas as pd
import numpy as np
import yfinance as yf
import talib
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')


class TradingBacktest:
    """
    Backtesting framework for momentum-based trading strategy
    """
    
    def __init__(self, tickers, start_date, end_date,
                 initial_capital=50000, max_positions=15, stop_loss=0.07):
        """
        Initialize backtest parameters
        
        Args:
            tickers: List of stock symbols to trade
            start_date: Backtest start date (YYYY-MM-DD)
            end_date: Backtest end date (YYYY-MM-DD)
            initial_capital: Starting portfolio value
            max_positions: Maximum number of positions to hold
            stop_loss: Stop loss percentage (0.07 = 7%)
        """
        self.tickers = tickers
        self.start_date = start_date
        self.end_date = end_date
        self.initial_capital = initial_capital
        self.max_positions = max_positions
        self.stop_loss = stop_loss
        
        # Portfolio tracking
        self.cash = initial_capital
        self.positions = {}
        self.sp500_shares = 0
        self.portfolio_value_history = []
        self.trades_log = []
        
        # Data containers
        self.price_data = None
        self.momentum_data = None
        self.macd_data = None
        self.rsi_data = None
        self.dates = None
        
        print(f"\n{'='*60}")
        print(f"BACKTEST INITIALIZATION")
        print(f"{'='*60}")
        print(f"Period: {start_date} to {end_date}")
        print(f"Universe: {len(tickers)} stocks")
        print(f"Initial Capital: ${initial_capital:,.0f}")
        print(f"Max Positions: {max_positions}")
        print(f"Stop Loss: {stop_loss*100:.1f}%")
        print(f"{'='*60}\n")
    
    def download_data(self):
        """Download historical price data for all tickers"""
        print("Downloading price data...")
        
        # Add S&P 500 for cash management
        all_tickers = self.tickers + ['^GSPC']
        
        # Download with buffer for technical indicators
        buffer_start = pd.to_datetime(self.start_date) - timedelta(days=400)
        
        try:
            data = yf.download(
                all_tickers,
                start=buffer_start,
                end=self.end_date,
                progress=True,
                group_by='ticker',
                auto_adjust=True
            )
            
            # Extract close prices
            price_data = {}
            for ticker in all_tickers:
                try:
                    if len(all_tickers) == 1:
                        price_data[ticker] = data['Close']
                    else:
                        price_data[ticker] = data[ticker]['Close']
                except:
                    print(f"Warning: Could not get data for {ticker}")
            
            self.price_data = pd.DataFrame(price_data)
            self.price_data = self.price_data.fillna(method='ffill').dropna()
            
            print(f"✓ Downloaded data for {len(self.price_data.columns)} tickers")
            print(f"  Date range: {self.price_data.index[0].date()} to {self.price_data.index[-1].date()}")
            print(f"  Trading days: {len(self.price_data)}\n")
            
        except Exception as e:
            print(f"Error downloading data: {e}")
            raise
    
    def calculate_momentum_12_1(self):
        """Calculate 12-1 month momentum"""
        print("Calculating 12-1 month momentum...")
        
        # Resample to monthly
        monthly_data = self.price_data.resample('M').last()
        
        # Calculate returns
        returns_12m = monthly_data.pct_change(12)
        returns_1m = monthly_data.pct_change(1)
        
        # 12-1 momentum
        momentum_12_1 = returns_12m - returns_1m
        
        # Forward fill to daily frequency
        momentum_daily = momentum_12_1.reindex(self.price_data.index, method='ffill')
        
        # Drop rows with NaN
        self.momentum_data = momentum_daily.dropna(axis=0)
        
        print(f"✓ Momentum calculated for {len(self.momentum_data.columns)} stocks")
        print(f"  Valid from: {self.momentum_data.index[0].date()}\n")
    
    def calculate_technical_indicators(self):
        """Calculate MACD and RSI indicators"""
        print("Calculating technical indicators (MACD, RSI)...")
        
        macd_data = {}
        rsi_data = {}
        
        for ticker in self.price_data.columns:
            try:
                prices = self.price_data[ticker].dropna()
                
                # MACD (we use the histogram)
                macd_line, macd_signal, macd_hist = talib.MACD(
                    prices.values,
                    fastperiod=12,
                    slowperiod=26,
                    signalperiod=9
                )
                macd_data[ticker] = pd.Series(macd_hist, index=prices.index)
                
                # RSI
                rsi = talib.RSI(prices.values, timeperiod=14)
                rsi_data[ticker] = pd.Series(rsi, index=prices.index)
                
            except Exception as e:
                print(f"Warning: Error calculating indicators for {ticker}: {e}")
                continue
        
        self.macd_data = pd.DataFrame(macd_data)
        self.rsi_data = pd.DataFrame(rsi_data)
        
        # Align dates with momentum data
        first_valid_date = self.momentum_data.first_valid_index()
        self.macd_data = self.macd_data.loc[self.macd_data.index >= first_valid_date]
        self.rsi_data = self.rsi_data.loc[self.rsi_data.index >= first_valid_date]
        
        print(f"✓ Technical indicators calculated")
        print(f"  MACD stocks: {len(self.macd_data.columns)}")
        print(f"  RSI stocks: {len(self.rsi_data.columns)}\n")
    
    def prepare_data(self):
        """Prepare all data for backtesting"""
        self.download_data()
        self.calculate_momentum_12_1()
        self.calculate_technical_indicators()
        
        # Get common dates for trading
        self.dates = sorted(list(
            set(self.momentum_data.index) & 
            set(self.macd_data.index) & 
            set(self.rsi_data.index)
        ))
        
        # Filter to backtest period
        backtest_start = pd.to_datetime(self.start_date)
        self.dates = [d for d in self.dates if d >= backtest_start]
        
        print(f"Data preparation complete!")
        print(f"Trading period: {self.dates[0].date()} to {self.dates[-1].date()}")
        print(f"Trading days: {len(self.dates)}\n")
    
    def get_top_momentum_stocks(self, date, n=30):
        """Get top N stocks by momentum on given date"""
        if date not in self.momentum_data.index:
            return []
        
        momentum_row = self.momentum_data.loc[date].dropna()
        top_stocks = momentum_row.nlargest(n).index.tolist()
        return top_stocks
    
    def check_macd_bullish(self, stock, date):
        """Check for MACD bullish signal"""
        if date not in self.macd_data.index or stock not in self.macd_data.columns:
            return False
        
        date_idx = self.macd_data.index.get_loc(date)
        if date_idx < 1:
            return False
        
        current_macd = self.macd_data.loc[date, stock]
        prev_macd = self.macd_data.iloc[date_idx-1, self.macd_data.columns.get_loc(stock)]
        
        if pd.isna(current_macd) or pd.isna(prev_macd):
            return False
        
        # Bullish: MACD crosses above 0 or is positive and increasing
        bullish = (current_macd > 0 and prev_macd <= 0) or \
                  (current_macd > prev_macd and current_macd > 0)
        return bullish
    
    def check_rsi_bullish(self, stock, date):
        """Check for RSI bullish signal"""
        if date not in self.rsi_data.index or stock not in self.rsi_data.columns:
            return False
        
        date_idx = self.rsi_data.index.get_loc(date)
        if date_idx < 1:
            return False
        
        current_rsi = self.rsi_data.loc[date, stock]
        prev_rsi = self.rsi_data.iloc[date_idx-1, self.rsi_data.columns.get_loc(stock)]
        
        if pd.isna(current_rsi) or pd.isna(prev_rsi):
            return False
        
        # Bullish: RSI crosses above 50 or bounces from oversold (>30)
        bullish = (current_rsi > 50 and prev_rsi <= 50) or \
                  (current_rsi > 30 and prev_rsi <= 30)
        return bullish
    
    def calculate_signal_strength(self, stock, date):
        """Calculate signal strength (0-1)"""
        if date not in self.momentum_data.index:
            return 0
        
        momentum_row = self.momentum_data.loc[date].dropna()
        if stock not in momentum_row.index:
            return 0
        
        # Momentum percentile rank
        momentum_rank = (momentum_row >= momentum_row[stock]).sum() / len(momentum_row)
        
        # MACD strength
        macd_val = self.macd_data.loc[date, stock] if stock in self.macd_data.columns else 0
        macd_strength = max(0, min(1, (macd_val + 1) / 2)) if not pd.isna(macd_val) else 0
        
        # RSI strength
        rsi_val = self.rsi_data.loc[date, stock] if stock in self.rsi_data.columns else 50
        rsi_strength = max(0, (rsi_val - 50) / 50) if not pd.isna(rsi_val) else 0
        
        # Weighted combination
        signal_strength = (momentum_rank * 0.4 + macd_strength * 0.3 + rsi_strength * 0.3)
        return signal_strength
    
    def get_buy_signals(self, date):
        """Get buy signals for given date"""
        top_momentum = self.get_top_momentum_stocks(date, 30)
        buy_signals = []
        
        for stock in top_momentum:
            if stock not in self.tickers:
                continue
            
            macd_signal = self.check_macd_bullish(stock, date)
            rsi_signal = self.check_rsi_bullish(stock, date)
            
            if macd_signal and rsi_signal:
                strength = self.calculate_signal_strength(stock, date)
                if strength > 0:
                    buy_signals.append((stock, strength))
        
        buy_signals.sort(key=lambda x: x[1], reverse=True)
        return buy_signals
    
    def check_sell_signals(self, date):
        """Check for sell signals on existing positions"""
        sells = []
        top_momentum = self.get_top_momentum_stocks(date, 30)
        
        for stock in list(self.positions.keys()):
            if date not in self.price_data.index or stock not in self.price_data.columns:
                continue
            
            current_price = self.price_data.loc[date, stock]
            entry_price = self.positions[stock]['entry_price']
            
            if pd.isna(current_price):
                continue
            
            # Stop loss
            if current_price <= entry_price * (1 - self.stop_loss):
                sells.append((stock, 'stop_loss'))
            # Momentum exit
            elif stock not in top_momentum:
                sells.append((stock, 'momentum_exit'))
        
        return sells
    
    def invest_excess_cash_in_sp500(self, date):
        """Invest excess cash in S&P 500"""
        if '^GSPC' not in self.price_data.columns or date not in self.price_data.index:
            return
        
        sp500_price = self.price_data.loc[date, '^GSPC']
        if pd.isna(sp500_price) or sp500_price <= 0:
            return
        
        portfolio_value = self.get_portfolio_value(date)
        cash_buffer = portfolio_value * 0.05
        excess_cash = max(0, self.cash - cash_buffer)
        
        if excess_cash > sp500_price:
            shares_to_buy = int(excess_cash / sp500_price)
            cost = shares_to_buy * sp500_price
            
            self.sp500_shares += shares_to_buy
            self.cash -= cost
            
            self.trades_log.append({
                'date': date,
                'stock': '^GSPC',
                'action': 'BUY',
                'shares': shares_to_buy,
                'price': sp500_price,
                'signal_strength': 0
            })
    
    def sell_sp500_for_cash(self, date, amount_needed):
        """Sell S&P 500 shares to raise cash"""
        if self.sp500_shares <= 0 or '^GSPC' not in self.price_data.columns:
            return 0
        
        if date not in self.price_data.index:
            return 0
        
        sp500_price = self.price_data.loc[date, '^GSPC']
        if pd.isna(sp500_price) or sp500_price <= 0:
            return 0
        
        shares_to_sell = min(self.sp500_shares, int(amount_needed / sp500_price) + 1)
        
        if shares_to_sell > 0:
            proceeds = shares_to_sell * sp500_price
            self.sp500_shares -= shares_to_sell
            self.cash += proceeds
            
            self.trades_log.append({
                'date': date,
                'stock': '^GSPC',
                'action': 'SELL',
                'shares': shares_to_sell,
                'price': sp500_price,
                'entry_price': 0,
                'pnl': 0,
                'reason': 'cash_for_trade'
            })
            
            return proceeds
        
        return 0
    
    def execute_buy(self, stock, date, signal_strength):
        """Execute buy order"""
        if date not in self.price_data.index or stock not in self.price_data.columns:
            return False
        
        price = self.price_data.loc[date, stock]
        if pd.isna(price) or price <= 0:
            return False
        
        target_position_value = self.get_portfolio_value(date) / self.max_positions
        shares = int(target_position_value / price)
        cost = shares * price
        
        if shares > 0:
            if cost > self.cash:
                self.sell_sp500_for_cash(date, cost - self.cash)
            
            if cost <= self.cash:
                self.positions[stock] = {
                    'shares': shares,
                    'entry_price': price,
                    'entry_date': date
                }
                self.cash -= cost
                
                self.trades_log.append({
                    'date': date,
                    'stock': stock,
                    'action': 'BUY',
                    'shares': shares,
                    'price': price,
                    'signal_strength': signal_strength
                })
                return True
        
        return False
    
    def execute_sell(self, stock, date, reason):
        """Execute sell order"""
        if stock not in self.positions:
            return False
        
        if date not in self.price_data.index or stock not in self.price_data.columns:
            return False
        
        price = self.price_data.loc[date, stock]
        if pd.isna(price) or price <= 0:
            return False
        
        shares = self.positions[stock]['shares']
        entry_price = self.positions[stock]['entry_price']
        
        self.cash += shares * price
        
        self.trades_log.append({
            'date': date,
            'stock': stock,
            'action': 'SELL',
            'shares': shares,
            'price': price,
            'entry_price': entry_price,
            'pnl': shares * (price - entry_price),
            'reason': reason
        })
        
        del self.positions[stock]
        return True
    
    def get_portfolio_value(self, date):
        """Calculate total portfolio value"""
        portfolio_value = self.cash
        
        for stock, position in self.positions.items():
            if date in self.price_data.index and stock in self.price_data.columns:
                current_price = self.price_data.loc[date, stock]
                if not pd.isna(current_price):
                    portfolio_value += position['shares'] * current_price
        
        if self.sp500_shares > 0 and '^GSPC' in self.price_data.columns:
            if date in self.price_data.index:
                sp500_price = self.price_data.loc[date, '^GSPC']
                if not pd.isna(sp500_price):
                    portfolio_value += self.sp500_shares * sp500_price
        
        return portfolio_value
    
    def run(self):
        """Run the backtest"""
        print(f"\n{'='*60}")
        print(f"STARTING BACKTEST")
        print(f"{'='*60}\n")
        
        # Prepare all data
        self.prepare_data()
        
        # Initialize with S&P 500 investment
        if len(self.dates) > 0:
            self.invest_excess_cash_in_sp500(self.dates[0])
        
        # Main backtest loop
        print("Running backtest simulation...\n")
        for i, date in enumerate(self.dates):
            # Sell signals first
            sell_signals = self.check_sell_signals(date)
            for stock, reason in sell_signals:
                self.execute_sell(stock, date, reason)
            
            # Buy signals
            buy_signals = self.get_buy_signals(date)
            positions_to_fill = self.max_positions - len(self.positions)
            
            for stock, strength in buy_signals[:positions_to_fill]:
                if stock not in self.positions:
                    self.execute_buy(stock, date, strength)
            
            # Invest excess cash
            self.invest_excess_cash_in_sp500(date)
            
            # Track portfolio value
            portfolio_value = self.get_portfolio_value(date)
            self.portfolio_value_history.append({
                'date': date,
                'portfolio_value': portfolio_value,
                'cash': self.cash,
                'positions': len(self.positions),
                'sp500_shares': self.sp500_shares
            })
            
            # Progress update
            if i % 50 == 0 or i == len(self.dates) - 1:
                print(f"  {date.date()} | Portfolio: ${portfolio_value:,.0f} | "
                      f"Positions: {len(self.positions)} | Progress: {i+1}/{len(self.dates)}")
        
        print("\nBacktest simulation complete!\n")
        self.generate_results()
    
    def generate_results(self):
        """Generate and display results"""
        if not self.portfolio_value_history:
            print("No data to analyze")
            return
        
        final_value = self.portfolio_value_history[-1]['portfolio_value']
        total_return = (final_value - self.initial_capital) / self.initial_capital
        
        # Trade statistics
        trades_df = pd.DataFrame(self.trades_log)
        if len(trades_df) > 0:
            sell_trades = trades_df[trades_df['action'] == 'SELL'].copy()
            sell_trades = sell_trades[sell_trades['stock'] != '^GSPC']  # Exclude S&P 500
            
            winning_trades = len(sell_trades[sell_trades['pnl'] > 0])
            losing_trades = len(sell_trades[sell_trades['pnl'] <= 0])
            total_trades = len(sell_trades)
            win_rate = winning_trades / total_trades if total_trades > 0 else 0
            
            avg_win = sell_trades[sell_trades['pnl'] > 0]['pnl'].mean() if winning_trades > 0 else 0
            avg_loss = sell_trades[sell_trades['pnl'] <= 0]['pnl'].mean() if losing_trades > 0 else 0
        else:
            winning_trades = losing_trades = total_trades = win_rate = 0
            avg_win = avg_loss = 0
        
        # Calculate S&P 500 benchmark return
        if '^GSPC' in self.price_data.columns:
            sp500_start = self.price_data.loc[self.dates[0], '^GSPC']
            sp500_end = self.price_data.loc[self.dates[-1], '^GSPC']
            sp500_return = (sp500_end - sp500_start) / sp500_start
        else:
            sp500_return = 0
        
        # Display results
        print(f"\n{'='*60}")
        print(f"BACKTEST RESULTS")
        print(f"{'='*60}")
        print(f"Initial Capital:       ${self.initial_capital:>15,.2f}")
        print(f"Final Portfolio Value: ${final_value:>15,.2f}")
        print(f"Total Return:          ${final_value - self.initial_capital:>15,.2f}")
        print(f"Total Return %:        {total_return:>15.2%}")
        print(f"{'='*60}")
        print(f"Total Trades:          {total_trades:>15}")
        print(f"Winning Trades:        {winning_trades:>15}")
        print(f"Losing Trades:         {losing_trades:>15}")
        print(f"Win Rate:              {win_rate:>15.1%}")
        if avg_win > 0:
            print(f"Avg Win:               ${avg_win:>15,.2f}")
        if avg_loss < 0:
            print(f"Avg Loss:              ${avg_loss:>15,.2f}")
        print(f"{'='*60}")
        print(f"S&P 500 Return:        {sp500_return:>15.2%}")
        print(f"Outperformance:        {total_return - sp500_return:>15.2%}")
        print(f"{'='*60}\n")
        
        # Save results
        self.save_results()
    
    def save_results(self):
        """Save backtest results to CSV files"""
        try:
            # Portfolio value history
            portfolio_df = pd.DataFrame(self.portfolio_value_history)
            portfolio_df.to_csv('backtest_portfolio_history.csv', index=False)
            print("✓ Saved portfolio history to: backtest_portfolio_history.csv")
            
            # Trade log
            trades_df = pd.DataFrame(self.trades_log)
            trades_df.to_csv('backtest_trades_log.csv', index=False)
            print("✓ Saved trade log to: backtest_trades_log.csv")
            
        except Exception as e:
            print(f"Warning: Could not save results to CSV: {e}")


def main():
    """Main entry point"""
    
    # S&P 500 major stocks (you can expand this list)
    TICKERS = [
        'AAPL', 'MSFT', 'AMZN', 'NVDA', 'GOOGL', 'TSLA', 'GOOG', 'META', 'UNH', 'XOM',
        'LLY', 'JNJ', 'JPM', 'V', 'PG', 'MA', 'HD', 'CVX', 'MRK', 'ABBV',
        'PEP', 'KO', 'AVGO', 'PFE', 'TMO', 'COST', 'WMT', 'BAC', 'CRM', 'ACN',
        'NFLX', 'LIN', 'AMD', 'CSCO', 'ABT', 'DHR', 'TXN', 'VZ', 'ADBE', 'NKE',
        'WFC', 'COP', 'BMY', 'RTX', 'QCOM', 'PM', 'T', 'UPS', 'SPGI', 'LOW',
        'NEE', 'HON', 'ORCL', 'UNP', 'MS', 'INTU', 'CAT', 'BA', 'GE', 'AMD',
        'SBUX', 'GS', 'BLK', 'AXP', 'ELV', 'BKNG', 'DE', 'TJX', 'GILD', 'MDT',
        'ADP', 'MMC', 'LRCX', 'AMT', 'VRTX', 'SYK', 'CVS', 'BDX', 'CI', 'MDLZ',
        'CB', 'ADI', 'REGN', 'TMUS', 'SO', 'MO', 'ZTS', 'DUK', 'PLD', 'EOG',
        'SCHW', 'SLB', 'CME', 'ITW', 'HUM', 'NOC', 'MMM', 'USB', 'PNC', 'CL'
    ]
    
    # Backtest parameters
    START_DATE = '2020-01-01'
    END_DATE = '2024-12-31'
    INITIAL_CAPITAL = 50000
    MAX_POSITIONS = 15
    STOP_LOSS = 0.07  # 7%
    
    # Run backtest
    backtest = TradingBacktest(
        tickers=TICKERS,
        start_date=START_DATE,
        end_date=END_DATE,
        initial_capital=INITIAL_CAPITAL,
        max_positions=MAX_POSITIONS,
        stop_loss=STOP_LOSS
    )
    
    backtest.run()
    
    print("\nBacktest complete! Results saved to CSV files.")
    print("You can now analyze:")
    print("  - backtest_portfolio_history.csv")
    print("  - backtest_trades_log.csv")


if __name__ == '__main__':
    main()