# Personal Automated Trading System

## Project Overview

A personal web-based trading system that automatically executes trades based on technical analysis algorithms, integrated with Alpaca brokerage API.

**Key Objectives:**
- Automate daily trading decisions based on momentum/technical analysis algorithm
- Track portfolio performance and trade history
- Monitor algorithm effectiveness vs benchmarks
- Simple, clean web interface for monitoring

---

## Trading Algorithm Specification

### Algorithm Overview
The system uses a **3-factor momentum-based trading strategy** with the following logic:

1. **Universe Selection**: S&P 500 stocks (503 tickers)
2. **Primary Filter**: Top 30 stocks by 12-1 month momentum 
3. **Technical Confirmation**: MACD bullish crossover AND RSI signal
4. **Position Management**: Max 15 positions, 7% stop loss
5. **Cash Management**: Excess cash invested in S&P 500 (^GSPC)

### Signal Generation Process

#### Step 1: Momentum Ranking (12-1 Strategy)
```python
# 12-month return minus 1-month return
momentum_12_1 = returns_12m - returns_1m
```
- Calculate monthly returns
- 12-month return - 1-month return = momentum score
- Rank all S&P 500 stocks by momentum
- Select top 30 highest momentum stocks

#### Step 2: MACD Filter
```python
# Bullish MACD conditions
macd_bullish = (current_macd > 0 and prev_macd <= 0) or 
               (current_macd > prev_macd and current_macd > 0)
```

#### Step 3: RSI Filter  
```python
# RSI bounce conditions
rsi_signal = (current_rsi > 50 and prev_rsi <= 50) or 
             (current_rsi > 30 and prev_rsi <= 30)
```

#### Step 4: Signal Strength Calculation
```python
signal_strength = (momentum_rank * 0.4 + macd_strength * 0.3 + rsi_strength * 0.3)
```

### Trading Rules

**Entry Conditions:**
- Stock must be in top 30 by momentum
- MACD shows bullish crossover/momentum
- RSI shows bullish signal (>50 or bounce from oversold)
- Maximum 15 simultaneous positions

**Exit Conditions:**
- Stock drops out of top 30 momentum ranking
- 7% stop loss triggered
- Position size: Equal weight (portfolio_value / 15)

**Cash Management:**
- Excess cash automatically invested in S&P 500 (^GSPC)
- 5% cash buffer maintained for new trades
- S&P 500 shares sold as needed to fund new positions

### Data Requirements

**Market Data Sources:**
- **Primary**: Yahoo Finance (yfinance) for historical data
- **Real-time**: Alpaca API for live trading
- **Benchmark**: S&P 500 (^GSPC) for cash management

**Required Data Points:**
- Daily OHLCV data for all S&P 500 stocks
- Minimum 252 trading days of history for momentum calculation
- Real-time price feeds during market hours

**Technical Indicators:**
- MACD (12, 26, 9 periods)
- RSI (14 periods)  
- 12-1 month momentum (calculated monthly, forward-filled daily)

### Algorithm Performance
**Backtest Results (2015-2024):**
- Total Return: 877.94% vs S&P 500's ~240%
- Win Rate: 23.3% (188 wins / 807 total trades)
- Strategy: High-conviction, momentum-based with strict risk management

---

## Database Schema

```sql
-- Trading Database Schema
CREATE TABLE trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trade_date DATE NOT NULL,
    symbol VARCHAR(10) NOT NULL,
    action VARCHAR(4) NOT NULL CHECK (action IN ('BUY', 'SELL')),
    quantity INTEGER NOT NULL,
    price DECIMAL(10,4) NOT NULL,
    entry_price DECIMAL(10,4),  -- For sell orders
    signal_strength DECIMAL(5,4),
    reason VARCHAR(50),  -- 'algorithm', 'stop_loss', 'momentum_exit', 'cash_for_trade'
    pnl DECIMAL(12,4),  -- Profit/Loss for sell orders
    commission DECIMAL(8,4) DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE portfolio_snapshots (
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
);

CREATE TABLE positions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol VARCHAR(10) NOT NULL UNIQUE,
    quantity INTEGER NOT NULL,
    avg_entry_price DECIMAL(10,4) NOT NULL,
    entry_date DATE NOT NULL,
    current_price DECIMAL(10,4),
    unrealized_pnl DECIMAL(12,4),
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE algorithm_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_date DATE NOT NULL,
    status VARCHAR(20) NOT NULL,  -- 'success', 'error', 'no_signals'
    signals_generated INTEGER DEFAULT 0,
    trades_executed INTEGER DEFAULT 0,
    error_message TEXT,
    execution_time_seconds INTEGER,
    top_momentum_stocks TEXT,  -- JSON array of top 30 stocks
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE daily_signals (
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
    action_taken VARCHAR(10),  -- 'bought', 'ignored', 'insufficient_cash'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX idx_trades_date ON trades(trade_date);
CREATE INDEX idx_trades_symbol ON trades(symbol);
CREATE INDEX idx_signals_date ON daily_signals(signal_date);
CREATE INDEX idx_algorithm_runs_date ON algorithm_runs(run_date);
```

---

## API Response Formats

### GET /api/dashboard
```json
{
    "portfolio_summary": {
        "total_value": 125000.50,
        "cash_balance": 5000.25,
        "stock_value": 115000.25,
        "sp500_value": 5000.00,
        "daily_pnl": 1250.75,
        "total_return_pct": 25.5,
        "num_positions": 12
    },
    "recent_trades": [
        {
            "id": 1,
            "date": "2024-01-15",
            "symbol": "AAPL",
            "action": "BUY",
            "quantity": 100,
            "price": 150.25,
            "signal_strength": 0.85
        }
    ],
    "current_positions": [
        {
            "symbol": "AAPL",
            "quantity": 100,
            "entry_price": 150.25,
            "current_price": 155.50,
            "unrealized_pnl": 525.00,
            "weight_pct": 12.4
        }
    ],
    "algorithm_status": {
        "last_run": "2024-01-15T09:30:00Z",
        "status": "success",
        "next_run": "2024-01-16T09:30:00Z",
        "signals_generated": 5,
        "trades_executed": 2
    }
}
```

### GET /api/trades
```json
{
    "trades": [
        {
            "id": 1,
            "date": "2024-01-15",
            "symbol": "AAPL", 
            "action": "BUY",
            "quantity": 100,
            "price": 150.25,
            "signal_strength": 0.85,
            "reason": "algorithm",
            "pnl": null
        }
    ],
    "pagination": {
        "page": 1,
        "per_page": 50,
        "total": 150,
        "pages": 3
    }
}
```

### GET /api/performance
```json
{
    "metrics": {
        "total_return_pct": 25.5,
        "annualized_return": 18.2,
        "volatility": 15.8,
        "sharpe_ratio": 1.15,
        "max_drawdown": -8.5,
        "win_rate": 23.3,
        "avg_win": 850.25,
        "avg_loss": -245.75
    },
    "benchmark_comparison": {
        "spy_return": 12.1,
        "outperformance": 13.4,
        "beta": 1.25,
        "correlation": 0.78
    },
    "monthly_returns": [
        {"month": "2024-01", "portfolio": 2.5, "spy": 1.2},
        {"month": "2024-02", "portfolio": -1.8, "spy": -0.5}
    ]
}
```

---

## Algorithm Integration Details

### TradingBacktest Class Integration
The existing `TradingBacktest` class will be refactored into production components:

**Core Algorithm Service:**
```python
class TradingAlgorithm:
    def __init__(self, alpaca_client, db_service):
        self.alpaca = alpaca_client
        self.db = db_service
        self.max_positions = 15
        self.stop_loss = 0.07
        
    def generate_daily_signals(self, date):
        """Main algorithm entry point - returns buy/sell signals"""
        # 1. Fetch current market data
        # 2. Calculate momentum rankings  
        # 3. Apply MACD/RSI filters
        # 4. Return ranked buy signals
        pass
        
    def check_sell_signals(self, date, current_positions):
        """Check existing positions for sell signals"""
        # 1. Check stop losses
        # 2. Check momentum rankings
        # 3. Return sell signals
        pass
```

**Data Processing Pipeline:**
```python
class MarketDataService:
    def get_sp500_tickers(self):
        """Returns current S&P 500 ticker list"""
        
    def calculate_momentum_12_1(self, price_data):
        """Calculate 12-1 month momentum scores"""
        
    def calculate_technical_indicators(self, price_data):
        """Calculate MACD, RSI for all stocks"""
        
    def get_daily_market_data(self, date):
        """Fetch required data for algorithm run"""
```

### Scheduler Integration
```python
# Daily algorithm execution at market open
@scheduler.scheduled_job('cron', hour=9, minute=45, timezone='America/New_York')
def run_daily_algorithm():
    if not is_market_open():
        return
        
    try:
        # 1. Generate signals
        signals = algorithm.generate_daily_signals(datetime.now().date())
        
        # 2. Execute trades
        trade_executor.process_signals(signals)
        
        # 3. Log results
        db.log_algorithm_run(signals, status='success')
        
    except Exception as e:
        logger.error(f"Algorithm execution failed: {e}")
        db.log_algorithm_run([], status='error', error=str(e))
```

---

## Technology Stack

### Backend
- **Language**: Python 3.9+
- **Framework**: Flask 
- **Database**: SQLite (single user, file-based)
- **Task Scheduling**: APScheduler or cron jobs
- **APIs**: Alpaca Trade API
- **Data Source**: Yahoo Finance (yfinance) + Alpaca
- **Technical Analysis**: TA-Lib, pandas
- **Deployment**: Render.com (free tier)

### Frontend
- **Framework**: React.js
- **Styling**: Tailwind CSS
- **Charts**: Recharts for performance charts
- **HTTP Client**: Axios
- **Build Tool**: Vite

### Dependencies

**Backend (requirements.txt):**
```
Flask==2.3.2
Flask-CORS==4.0.0
alpaca-trade-api==3.0.0
yfinance==0.2.18
pandas==2.0.3
numpy==1.24.3
TA-Lib==0.4.28
APScheduler==3.10.1
python-dotenv==1.0.0
requests==2.31.0
```

**Frontend (package.json):**
```json
{
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0", 
    "react-router-dom": "^6.14.2",
    "axios": "^1.4.0",
    "recharts": "^2.7.2",
    "tailwindcss": "^3.3.3"
  }
}
```

---

## Environment Configuration

### Required Environment Variables
```env
# Alpaca API (use paper trading initially)
ALPACA_API_KEY=your_paper_trading_api_key
ALPACA_SECRET_KEY=your_paper_trading_secret_key
ALPACA_BASE_URL=https://paper-api.alpaca.markets

# Flask Configuration
FLASK_ENV=production
SECRET_KEY=your_secret_key_here

# Database
DATABASE_PATH=trading.db

# Algorithm Settings
ALGORITHM_ENABLED=true
TRADING_ENABLED=false  # Set to false for data collection mode
MAX_POSITIONS=15
STOP_LOSS_PERCENT=0.07
INITIAL_CAPITAL=50000

# Market Data
DATA_SOURCE=yfinance  # Primary data source
MARKET_TIMEZONE=America/New_York

# Logging
LOG_LEVEL=INFO
LOG_FILE=trading_system.log
```

---

## Development Phases

### Phase 1: Algorithm Validation (Priority: CRITICAL)
Before building the web interface, validate the algorithm works with live data:

**Requirements:**
- Port `TradingBacktest` class to production `TradingAlgorithm`
- Integrate with live market data (yfinance + Alpaca)
- Implement paper trading execution with alpaca
- Database logging of all signals and decisions

**Success Criteria:**
- Algorithm runs daily without errors
- Signals match backtest expectations
- All trades logged to database
- Paper trading P&L tracked

### Phase 2: Core Backend (After Algorithm Validation)
- Database schema implementation
- Flask API with core endpoints
- Alpaca integration for live trading
- Basic error handling and logging

### Phase 3: Frontend Dashboard
- React app with trading dashboard
- Portfolio overview and trade history
- Performance charts and metrics
- Algorithm status monitoring

### Phase 4: Production Deployment
- Render.com deployment
- Live trading activation (after thorough testing)
- Monitoring and alerting

---

## Risk Management & Testing

### Paper Trading Requirements
- **MANDATORY**: All initial development must use Alpaca paper trading
- Live trading only after 30+ days of successful paper trading
- Stop loss enforcement at 7% loss per position
- Maximum 15 positions to limit concentration risk
- Daily monitoring of algorithm performance vs expectations

### Testing Strategy
```python
# Mock algorithm for development
class MockTradingAlgorithm:
    """Generate predictable signals for frontend testing"""
    def generate_daily_signals(self, date):
        return [
            {"symbol": "AAPL", "signal_strength": 0.85, "action": "BUY"},
            {"symbol": "MSFT", "signal_strength": 0.78, "action": "BUY"}
        ]
```

### Monitoring Requirements
- Daily algorithm execution logs
- Trade execution monitoring  
- Performance deviation alerts
- Error notification system
- Database backup strategy
