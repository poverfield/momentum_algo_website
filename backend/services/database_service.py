"""
Database service for managing SQLite database operations
"""
import sqlite3
import os
import logging
from datetime import datetime, date
from typing import List, Dict, Optional, Tuple
import json

logger = logging.getLogger(__name__)

class DatabaseService:
    def __init__(self):
        self.db_path = os.getenv('DATABASE_PATH', 'trading.db')
        self.initialize_database()
    
    def get_connection(self):
        """Get database connection"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Enable dict-like access
        return conn
    
    def is_connected(self) -> bool:
        """Check if database is accessible"""
        try:
            with self.get_connection() as conn:
                conn.execute('SELECT 1')
            return True
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            return False
    
    def initialize_database(self):
        """Create database tables if they don't exist"""
        try:
            with self.get_connection() as conn:
                # Create trades table
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS trades (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        trade_date DATE NOT NULL,
                        symbol VARCHAR(10) NOT NULL,
                        action VARCHAR(4) NOT NULL CHECK (action IN ('BUY', 'SELL')),
                        quantity INTEGER NOT NULL,
                        price DECIMAL(10,4) NOT NULL,
                        entry_price DECIMAL(10,4),
                        signal_strength DECIMAL(5,4),
                        reason VARCHAR(50),
                        pnl DECIMAL(12,4),
                        commission DECIMAL(8,4) DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Create portfolio_snapshots table
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS portfolio_snapshots (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        snapshot_date DATE NOT NULL UNIQUE,
                        total_value DECIMAL(15,4) NOT NULL,
                        cash_balance DECIMAL(15,4) NOT NULL,
                        stock_value DECIMAL(15,4) NOT NULL,
                        sp500_shares INTEGER DEFAULT 0,
                        sp500_value DECIMAL(15,4) DEFAULT 0,
                        num_positions INTEGER DEFAULT 0,
                        daily_pnl DECIMAL(12,4),
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Create positions table
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS positions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        symbol VARCHAR(10) NOT NULL UNIQUE,
                        quantity INTEGER NOT NULL,
                        avg_entry_price DECIMAL(10,4) NOT NULL,
                        entry_date DATE NOT NULL,
                        current_price DECIMAL(10,4),
                        unrealized_pnl DECIMAL(12,4),
                        last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Create algorithm_runs table
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS algorithm_runs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        run_date DATE NOT NULL,
                        status VARCHAR(20) NOT NULL,
                        signals_generated INTEGER DEFAULT 0,
                        trades_executed INTEGER DEFAULT 0,
                        error_message TEXT,
                        execution_time_seconds INTEGER,
                        top_momentum_stocks TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Create daily_signals table
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS daily_signals (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        signal_date DATE NOT NULL,
                        symbol VARCHAR(10) NOT NULL,
                        signal_strength DECIMAL(5,4) NOT NULL,
                        momentum_rank INTEGER,
                        momentum_value DECIMAL(8,6),
                        macd_value DECIMAL(8,6),
                        rsi_value DECIMAL(6,2),
                        is_top_momentum BOOLEAN DEFAULT FALSE,
                        macd_bullish BOOLEAN DEFAULT FALSE,
                        rsi_bullish BOOLEAN DEFAULT FALSE,
                        action_taken VARCHAR(10),
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Create indexes
                conn.execute('CREATE INDEX IF NOT EXISTS idx_trades_date ON trades(trade_date)')
                conn.execute('CREATE INDEX IF NOT EXISTS idx_trades_symbol ON trades(symbol)')
                conn.execute('CREATE INDEX IF NOT EXISTS idx_signals_date ON daily_signals(signal_date)')
                conn.execute('CREATE INDEX IF NOT EXISTS idx_algorithm_runs_date ON algorithm_runs(run_date)')
                
                conn.commit()
                logger.info("Database initialized successfully")
                
        except Exception as e:
            logger.error(f"Error initializing database: {e}")
            raise
    
    def log_trade(self, trade_date: date, symbol: str, action: str, quantity: int, 
                  price: float, entry_price: Optional[float] = None, 
                  signal_strength: Optional[float] = None, reason: str = 'algorithm',
                  pnl: Optional[float] = None, commission: float = 0) -> int:
        """Log a trade to the database"""
        try:
            with self.get_connection() as conn:
                cursor = conn.execute('''
                    INSERT INTO trades (trade_date, symbol, action, quantity, price, 
                                      entry_price, signal_strength, reason, pnl, commission)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (trade_date, symbol, action, quantity, price, entry_price, 
                      signal_strength, reason, pnl, commission))
                
                trade_id = cursor.lastrowid
                conn.commit()
                logger.info(f"Logged trade: {action} {quantity} {symbol} @ ${price}")
                return trade_id
                
        except Exception as e:
            logger.error(f"Error logging trade: {e}")
            raise
    
    def update_position(self, symbol: str, quantity: int, avg_entry_price: float, 
                       entry_date: date, current_price: Optional[float] = None):
        """Update or insert position"""
        try:
            with self.get_connection() as conn:
                # Calculate unrealized P&L if current price provided
                unrealized_pnl = None
                if current_price:
                    unrealized_pnl = (current_price - avg_entry_price) * quantity
                
                conn.execute('''
                    INSERT OR REPLACE INTO positions 
                    (symbol, quantity, avg_entry_price, entry_date, current_price, unrealized_pnl)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (symbol, quantity, avg_entry_price, entry_date, current_price, unrealized_pnl))
                
                conn.commit()
                logger.info(f"Updated position: {symbol} - {quantity} shares @ ${avg_entry_price}")
                
        except Exception as e:
            logger.error(f"Error updating position: {e}")
            raise
    
    def remove_position(self, symbol: str):
        """Remove a position from the database"""
        try:
            with self.get_connection() as conn:
                conn.execute('DELETE FROM positions WHERE symbol = ?', (symbol,))
                conn.commit()
                logger.info(f"Removed position: {symbol}")
                
        except Exception as e:
            logger.error(f"Error removing position: {e}")
            raise
    
    def log_algorithm_run(self, run_date: date, status: str, signals_generated: int = 0,
                         trades_executed: int = 0, error_message: Optional[str] = None,
                         execution_time: Optional[int] = None, 
                         top_momentum_stocks: Optional[List[str]] = None):
        """Log algorithm run results"""
        try:
            with self.get_connection() as conn:
                top_stocks_json = json.dumps(top_momentum_stocks) if top_momentum_stocks else None
                
                conn.execute('''
                    INSERT INTO algorithm_runs 
                    (run_date, status, signals_generated, trades_executed, 
                     error_message, execution_time_seconds, top_momentum_stocks)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (run_date, status, signals_generated, trades_executed, 
                      error_message, execution_time, top_stocks_json))
                
                conn.commit()
                logger.info(f"Logged algorithm run: {status} - {signals_generated} signals, {trades_executed} trades")
                
        except Exception as e:
            logger.error(f"Error logging algorithm run: {e}")
            raise
    
    def log_daily_signals(self, signals: List[Dict]):
        """Log daily signals generated by algorithm"""
        try:
            with self.get_connection() as conn:
                for signal in signals:
                    conn.execute('''
                        INSERT INTO daily_signals 
                        (signal_date, symbol, signal_strength, momentum_rank, momentum_value,
                         macd_value, rsi_value, is_top_momentum, macd_bullish, rsi_bullish, action_taken)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        signal['signal_date'], signal['symbol'], signal['signal_strength'],
                        signal.get('momentum_rank'), signal.get('momentum_value'),
                        signal.get('macd_value'), signal.get('rsi_value'),
                        signal.get('is_top_momentum', False), signal.get('macd_bullish', False),
                        signal.get('rsi_bullish', False), signal.get('action_taken')
                    ))
                
                conn.commit()
                logger.info(f"Logged {len(signals)} daily signals")
                
        except Exception as e:
            logger.error(f"Error logging daily signals: {e}")
            raise
    
    def get_current_positions(self) -> List[Dict]:
        """Get all current positions"""
        try:
            with self.get_connection() as conn:
                cursor = conn.execute('''
                    SELECT symbol, quantity, avg_entry_price, entry_date, 
                           current_price, unrealized_pnl, last_updated
                    FROM positions 
                    WHERE quantity > 0
                    ORDER BY symbol
                ''')
                
                positions = []
                for row in cursor.fetchall():
                    positions.append({
                        'symbol': row['symbol'],
                        'quantity': row['quantity'],
                        'entry_price': float(row['avg_entry_price']),
                        'entry_date': row['entry_date'],
                        'current_price': float(row['current_price']) if row['current_price'] else None,
                        'unrealized_pnl': float(row['unrealized_pnl']) if row['unrealized_pnl'] else None,
                        'last_updated': row['last_updated']
                    })
                
                return positions
                
        except Exception as e:
            logger.error(f"Error getting current positions: {e}")
            return []

    def get_performance_summary_wow_mom_yoy(self) -> Dict:
        """
        Compute WoW, MoM, YoY performance based on realized trade PnL.
        Uses trades.pnL where present (we log PnL on SELL). BUY PnL may be NULL and is ignored.
        Returns each period's total and delta vs prior comparable period, with percent change.
        """
        try:
            with self.get_connection() as conn:
                def sum_pnl(days: int) -> float:
                    cursor = conn.execute(
                        '''SELECT COALESCE(SUM(pnl), 0) AS s FROM trades
                           WHERE pnl IS NOT NULL AND trade_date >= date('now', ?)''',
                        (f'-{days} days',)
                    )
                    return float(cursor.fetchone()['s'])

                wow_current = sum_pnl(7)
                wow_prior = 0.0
                cursor = conn.execute(
                    '''SELECT COALESCE(SUM(pnl), 0) AS s FROM trades
                       WHERE pnl IS NOT NULL AND trade_date < date('now', '-0 days')
                         AND trade_date >= date('now', '-14 days')'''
                )
                wow_prior = float(cursor.fetchone()['s'])

                mom_current = sum_pnl(30)
                cursor = conn.execute(
                    '''SELECT COALESCE(SUM(pnl), 0) AS s FROM trades
                       WHERE pnl IS NOT NULL AND trade_date < date('now', '-0 days')
                         AND trade_date >= date('now', '-60 days')'''
                )
                mom_prior = float(cursor.fetchone()['s'])

                yoy_current = sum_pnl(365)
                cursor = conn.execute(
                    '''SELECT COALESCE(SUM(pnl), 0) AS s FROM trades
                       WHERE pnl IS NOT NULL AND trade_date < date('now', '-0 days')
                         AND trade_date >= date('now', '-730 days')'''
                )
                yoy_prior = float(cursor.fetchone()['s'])

                def fmt(cur: float, prior: float) -> Dict:
                    delta = cur - prior
                    pct = (delta / abs(prior)) * 100 if prior != 0 else None
                    return {
                        'current': round(cur, 2),
                        'prior': round(prior, 2),
                        'delta': round(delta, 2),
                        'delta_pct': round(pct, 2) if pct is not None else None
                    }

                return {
                    'wow': fmt(wow_current, wow_prior),
                    'mom': fmt(mom_current, mom_prior),
                    'yoy': fmt(yoy_current, yoy_prior)
                }
        except Exception as e:
            logger.error(f"Error computing performance summary: {e}")
            return {
                'wow': {'current': 0, 'prior': 0, 'delta': 0, 'delta_pct': None},
                'mom': {'current': 0, 'prior': 0, 'delta': 0, 'delta_pct': None},
                'yoy': {'current': 0, 'prior': 0, 'delta': 0, 'delta_pct': None}
            }
    
    def get_recent_trades(self, limit: int = 10) -> List[Dict]:
        """Get recent trades"""
        try:
            with self.get_connection() as conn:
                cursor = conn.execute('''
                    SELECT id, trade_date, symbol, action, quantity, price, 
                           signal_strength, reason, pnl, created_at
                    FROM trades 
                    ORDER BY created_at DESC 
                    LIMIT ?
                ''', (limit,))
                
                trades = []
                for row in cursor.fetchall():
                    trades.append({
                        'id': row['id'],
                        'date': row['trade_date'],
                        'symbol': row['symbol'],
                        'action': row['action'],
                        'quantity': row['quantity'],
                        'price': float(row['price']),
                        'signal_strength': float(row['signal_strength']) if row['signal_strength'] else None,
                        'reason': row['reason'],
                        'pnl': float(row['pnl']) if row['pnl'] else None
                    })
                
                return trades
                
        except Exception as e:
            logger.error(f"Error getting recent trades: {e}")
            return []
    
    def get_portfolio_summary(self) -> Dict:
        """Get portfolio summary from latest snapshot"""
        try:
            with self.get_connection() as conn:
                cursor = conn.execute('''
                    SELECT total_value, cash_balance, stock_value, sp500_value,
                           daily_pnl, num_positions, snapshot_date
                    FROM portfolio_snapshots 
                    ORDER BY snapshot_date DESC 
                    LIMIT 1
                ''')
                
                row = cursor.fetchone()
                if row:
                    # Calculate total return percentage (assuming initial capital from env)
                    initial_capital = float(os.getenv('INITIAL_CAPITAL', 50000))
                    total_return_pct = ((float(row['total_value']) - initial_capital) / initial_capital) * 100
                    
                    return {
                        'total_value': float(row['total_value']),
                        'cash_balance': float(row['cash_balance']),
                        'stock_value': float(row['stock_value']),
                        'sp500_value': float(row['sp500_value']) if row['sp500_value'] else 0,
                        'daily_pnl': float(row['daily_pnl']) if row['daily_pnl'] else 0,
                        'total_return_pct': round(total_return_pct, 2),
                        'num_positions': row['num_positions'],
                        'last_updated': row['snapshot_date']
                    }
                else:
                    # Return default values if no snapshots exist
                    initial_capital = float(os.getenv('INITIAL_CAPITAL', 50000))
                    return {
                        'total_value': initial_capital,
                        'cash_balance': initial_capital,
                        'stock_value': 0,
                        'sp500_value': 0,
                        'daily_pnl': 0,
                        'total_return_pct': 0,
                        'num_positions': 0,
                        'last_updated': None
                    }
                
        except Exception as e:
            logger.error(f"Error getting portfolio summary: {e}")
            return {}
    
    def get_latest_algorithm_run(self) -> Dict:
        """Get latest algorithm run status"""
        try:
            with self.get_connection() as conn:
                cursor = conn.execute('''
                    SELECT run_date, status, signals_generated, trades_executed,
                           error_message, created_at
                    FROM algorithm_runs 
                    ORDER BY created_at DESC 
                    LIMIT 1
                ''')
                
                row = cursor.fetchone()
                if row:
                    return {
                        'last_run': row['created_at'],
                        'status': row['status'],
                        'next_run': None,  # TODO: Calculate based on schedule
                        'signals_generated': row['signals_generated'],
                        'trades_executed': row['trades_executed'],
                        'error_message': row['error_message']
                    }
                else:
                    return {
                        'last_run': None,
                        'status': 'never_run',
                        'next_run': None,
                        'signals_generated': 0,
                        'trades_executed': 0,
                        'error_message': None
                    }
                
        except Exception as e:
            logger.error(f"Error getting algorithm status: {e}")
            return {}
    
    def get_trades_paginated(self, page: int, per_page: int) -> Tuple[List[Dict], int]:
        """Get paginated trades"""
        try:
            with self.get_connection() as conn:
                # Get total count
                cursor = conn.execute('SELECT COUNT(*) as total FROM trades')
                total = cursor.fetchone()['total']
                
                # Get paginated results
                offset = (page - 1) * per_page
                cursor = conn.execute('''
                    SELECT id, trade_date, symbol, action, quantity, price, 
                           signal_strength, reason, pnl, created_at
                    FROM trades 
                    ORDER BY created_at DESC 
                    LIMIT ? OFFSET ?
                ''', (per_page, offset))
                
                trades = []
                for row in cursor.fetchall():
                    trades.append({
                        'id': row['id'],
                        'date': row['trade_date'],
                        'symbol': row['symbol'],
                        'action': row['action'],
                        'quantity': row['quantity'],
                        'price': float(row['price']),
                        'signal_strength': float(row['signal_strength']) if row['signal_strength'] else None,
                        'reason': row['reason'],
                        'pnl': float(row['pnl']) if row['pnl'] else None
                    })
                
                return trades, total
                
        except Exception as e:
            logger.error(f"Error getting paginated trades: {e}")
            return [], 0
    
    def get_performance_metrics(self) -> Dict:
        """Calculate and return performance metrics"""
        # TODO: Implement performance calculations
        # This is a placeholder - will need to calculate from trade history
        return {
            'total_return_pct': 0,
            'annualized_return': 0,
            'volatility': 0,
            'sharpe_ratio': 0,
            'max_drawdown': 0,
            'win_rate': 0,
            'avg_win': 0,
            'avg_loss': 0
        }
    
    def get_benchmark_comparison(self) -> Dict:
        """Get benchmark comparison data"""
        # TODO: Implement benchmark comparison
        return {
            'spy_return': 0,
            'outperformance': 0,
            'beta': 0,
            'correlation': 0
        }
    
    def get_monthly_returns(self) -> List[Dict]:
        """Get monthly returns data"""
        # TODO: Implement monthly returns calculation
        return []

    def get_signals_paginated(self, page: int, per_page: int,
                              signal_date: Optional[str] = None,
                              symbol: Optional[str] = None) -> Tuple[List[Dict], int]:
        """Get paginated daily signals with optional filters"""
        try:
            with self.get_connection() as conn:
                where = []
                params: List = []
                if signal_date:
                    where.append('signal_date = ?')
                    params.append(signal_date)
                if symbol:
                    where.append('symbol = ?')
                    params.append(symbol.upper())

                where_sql = f"WHERE {' AND '.join(where)}" if where else ''

                # Total count
                cursor = conn.execute(f'SELECT COUNT(*) as total FROM daily_signals {where_sql}', params)
                total = cursor.fetchone()['total']

                # Page
                offset = (page - 1) * per_page
                cursor = conn.execute(
                    f'''SELECT id, signal_date, symbol, signal_strength, momentum_rank, momentum_value,
                               macd_value, rsi_value, is_top_momentum, macd_bullish, rsi_bullish, created_at
                        FROM daily_signals {where_sql}
                        ORDER BY signal_date DESC, signal_strength DESC
                        LIMIT ? OFFSET ?''', params + [per_page, offset]
                )

                signals: List[Dict] = []
                for row in cursor.fetchall():
                    signals.append({
                        'id': row['id'],
                        'signal_date': row['signal_date'],
                        'symbol': row['symbol'],
                        'signal_strength': float(row['signal_strength']) if row['signal_strength'] is not None else None,
                        'momentum_rank': row['momentum_rank'],
                        'momentum_value': float(row['momentum_value']) if row['momentum_value'] is not None else None,
                        'macd_value': float(row['macd_value']) if row['macd_value'] is not None else None,
                        'rsi_value': float(row['rsi_value']) if row['rsi_value'] is not None else None,
                        'is_top_momentum': bool(row['is_top_momentum']) if row['is_top_momentum'] is not None else False,
                        'macd_bullish': bool(row['macd_bullish']) if row['macd_bullish'] is not None else False,
                        'rsi_bullish': bool(row['rsi_bullish']) if row['rsi_bullish'] is not None else False,
                        'created_at': row['created_at']
                    })

                return signals, total
        except Exception as e:
            logger.error(f"Error getting paginated signals: {e}")
            return [], 0

    def get_algorithm_runs_paginated(self, page: int, per_page: int,
                                     status: Optional[str] = None,
                                     run_date: Optional[str] = None) -> Tuple[List[Dict], int]:
        """Get paginated algorithm runs with optional filters"""
        try:
            with self.get_connection() as conn:
                where = []
                params: List = []
                if status:
                    where.append('status = ?')
                    params.append(status)
                if run_date:
                    where.append('run_date = ?')
                    params.append(run_date)

                where_sql = f"WHERE {' AND '.join(where)}" if where else ''

                # Total count
                cursor = conn.execute(f'SELECT COUNT(*) as total FROM algorithm_runs {where_sql}', params)
                total = cursor.fetchone()['total']

                # Page
                offset = (page - 1) * per_page
                cursor = conn.execute(
                    f'''SELECT id, run_date, status, signals_generated, trades_executed,
                               error_message, execution_time_seconds, top_momentum_stocks, created_at
                        FROM algorithm_runs {where_sql}
                        ORDER BY created_at DESC
                        LIMIT ? OFFSET ?''', params + [per_page, offset]
                )

                runs: List[Dict] = []
                for row in cursor.fetchall():
                    # top_momentum_stocks stored as JSON text
                    try:
                        top_list = json.loads(row['top_momentum_stocks']) if row['top_momentum_stocks'] else []
                    except Exception:
                        top_list = []
                    runs.append({
                        'id': row['id'],
                        'run_date': row['run_date'],
                        'status': row['status'],
                        'signals_generated': row['signals_generated'],
                        'trades_executed': row['trades_executed'],
                        'error_message': row['error_message'],
                        'execution_time_seconds': row['execution_time_seconds'],
                        'top_momentum_stocks': top_list,
                        'created_at': row['created_at']
                    })

                return runs, total
        except Exception as e:
            logger.error(f"Error getting paginated algorithm runs: {e}")
            return [], 0
