# Personal Automated Trading System

A web-based automated trading system that executes trades based on a 3-factor momentum strategy using technical analysis. The system integrates with Alpaca for paper trading and provides a clean web interface for monitoring performance.

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- Alpaca Paper Trading Account (free)
- Node.js 16+ (for frontend)

### Backend Setup

1. **Clone and navigate to backend**
   ```bash
   cd backend
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your Alpaca paper trading credentials
   ```

4. **Test the algorithm (Phase 1 Validation)**
   ```bash
   python test_algorithm.py
   ```

5. **Run the Flask application**
   ```bash
   python app.py
   ```

### Environment Variables

Create a `.env` file in the backend directory:

```env
# Alpaca API (use paper trading initially)
ALPACA_API_KEY=your_paper_trading_api_key
ALPACA_SECRET_KEY=your_paper_trading_secret_key
ALPACA_BASE_URL=https://paper-api.alpaca.markets

# Flask Configuration
FLASK_ENV=development
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
DATA_SOURCE=yfinance
MARKET_TIMEZONE=America/New_York

# Logging
LOG_LEVEL=INFO
LOG_FILE=trading_system.log
```

## 📊 Trading Algorithm

### Strategy Overview
The system uses a **3-factor momentum-based trading strategy**:

1. **Universe Selection**: S&P 500 stocks
2. **Primary Filter**: Top 30 stocks by 12-1 month momentum
3. **Technical Confirmation**: MACD bullish crossover AND RSI signal
4. **Position Management**: Max 15 positions, 7% stop loss
5. **Cash Management**: Excess cash invested in S&P 500

### Signal Generation Process

#### Step 1: Momentum Ranking (12-1 Strategy)
```python
momentum_12_1 = returns_12m - returns_1m
```

#### Step 2: MACD Filter
```python
macd_bullish = (current_macd > 0 and prev_macd <= 0) or 
               (current_macd > prev_macd and current_macd > 0)
```

#### Step 3: RSI Filter
```python
rsi_signal = (current_rsi > 50 and prev_rsi <= 50) or 
             (current_rsi > 30 and prev_rsi <= 30)
```

#### Step 4: Signal Strength
```python
signal_strength = (momentum_rank * 0.4 + macd_strength * 0.3 + rsi_strength * 0.3)
```

## 🏗️ Architecture

### Backend Services
- **TradingAlgorithm**: Core algorithm logic and signal generation
- **MarketDataService**: Data fetching and technical analysis (Yahoo Finance)
- **AlpacaService**: Paper trading execution and account management
- **DatabaseService**: SQLite database operations and logging

### Database Schema
- **trades**: All buy/sell transactions
- **positions**: Current portfolio positions
- **portfolio_snapshots**: Daily portfolio values
- **algorithm_runs**: Algorithm execution logs
- **daily_signals**: Generated trading signals

## 🔄 Development Phases

### ✅ Phase 1: Algorithm Validation (CURRENT)
- [x] Port TradingBacktest class to production
- [x] Integrate with live market data
- [x] Implement paper trading execution
- [x] Database logging system
- [x] Validation test script

**Run Phase 1 validation:**
```bash
python test_algorithm.py
```

### 📋 Phase 2: Core Backend (NEXT)
- [ ] Complete Flask API endpoints
- [ ] Enhanced error handling
- [ ] Performance metrics calculation
- [ ] Scheduler integration

### 🎨 Phase 3: Frontend Dashboard
- [ ] React application
- [ ] Portfolio overview
- [ ] Trade history and charts
- [ ] Algorithm monitoring

### 🚀 Phase 4: Production Deployment
- [ ] Render.com deployment
- [ ] Live trading activation
- [ ] Monitoring and alerts

## 📈 Backtest Performance (2015-2024)
- **Total Return**: 877.94% vs S&P 500's ~240%
- **Win Rate**: 23.3% (188 wins / 807 total trades)
- **Strategy**: High-conviction momentum with strict risk management

## 🛡️ Risk Management

### Paper Trading Requirements
- **MANDATORY**: All development uses Alpaca paper trading
- Live trading only after 30+ days of successful paper trading
- 7% stop loss per position
- Maximum 15 positions
- Daily algorithm monitoring

### Safety Features
- Trading can be disabled via `TRADING_ENABLED=false`
- All signals logged even when trading is disabled
- Comprehensive error handling and logging
- Position size limits and stop losses

## 📊 API Endpoints

### Core Endpoints
- `GET /api/health` - System health check
- `GET /api/dashboard` - Portfolio summary and recent activity
- `GET /api/trades` - Trade history with pagination
- `GET /api/performance` - Performance metrics and benchmarks
- `POST /api/algorithm/run` - Manual algorithm trigger (testing)

## 🔧 Testing

### Run Algorithm Validation
```bash
python test_algorithm.py
```

This will test:
- Database connectivity
- Market data fetching
- Technical indicator calculations
- Signal generation
- Alpaca API connection (if configured)

### Expected Output
```
✓ Database service connected successfully
✓ Retrieved 503 S&P 500 tickers
✓ Retrieved market data: 100 days, 5 tickers
✓ Technical indicators calculated
✓ Generated X buy signals
✓ Full algorithm run completed successfully
```

## 📝 Logging

All system activity is logged to:
- Console output
- `trading_system.log` file
- Database (trades, signals, algorithm runs)

Log levels: DEBUG, INFO, WARNING, ERROR

## ▶️ Local Serving Scripts

Use these simple scripts to run the backend API and the React frontend locally on Windows (PowerShell):

### Backend API
- Path: `backend/serve.ps1`
- Starts Flask on `http://127.0.0.1:5000`

Run from the project root (or any directory):

```powershell
.\backend\serve.ps1
```

Or from the backend directory:

```powershell
cd backend
.\serve.ps1
```

### Frontend (React + Vite)
- Path: `frontend/serve.ps1`
- Starts Vite dev server on `http://127.0.0.1:5173` and proxies `/api` to `http://127.0.0.1:5000`

Run from the project root (or any directory):

```powershell
.\frontend\serve.ps1
```

Or from the frontend directory:

```powershell
cd frontend
.\serve.ps1
```

### Notes
- If PowerShell blocks running scripts, allow local scripts for the current user:

```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
```

- Direct alternatives if you prefer not to use the scripts:
  - Backend: `cd backend` then `python app.py`
  - Frontend: `cd frontend` then `npm install` and `npm run dev`

## 🐍 Python Virtual Environment (Windows PowerShell)

Set up and use a virtual environment for the backend to ensure dependencies (like `python-dotenv`) are installed and isolated.

### Create and activate venv

```powershell
cd backend

# Create venv in the backend directory
python -m venv .venv #only needed nce

# Activate it (PowerShell)
.\.venv\Scripts\Activate.ps1

# Upgrade pip (optional but recommended)
python -m pip install --upgrade pip
```

If PowerShell blocks script execution, allow local scripts for your user:

```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
```

### Install backend dependencies

```powershell
pip install -r requirements.txt
```

### Run the backend inside the venv

Option A: use the serve script

```powershell
./serve.ps1
```

Option B: run directly

```powershell
python app.py
```

You should see the API start on `http://127.0.0.1:5000`.

## ☁️ Render Single-Service Deployment (API + Frontend on one origin)

Deploy both the Flask API and the React app on a single Render Web Service. Flask serves the built React app from `frontend/dist/` (already wired in `backend/app.py` via `FRONTEND_DIR = ../frontend/dist`).

### 1) Create the Web Service
- Dashboard → New → Web Service → Connect this repo
- Root directory: `backend/`
- Start command: `python app.py`
- Environment: Python 3.x (Render default)

### 2) Build Command
Render runs this on each deploy. It builds the frontend and installs backend deps.

```bash
npm ci --prefix ../frontend
npm run build --prefix ../frontend
pip install -r requirements.txt
```

### 3) Persistent Disk (SQLite)
- Service → Settings → Disks → Add Disk
- Size: 1–2 GB to start
- Mount at default working directory
- Ensure `DATABASE_PATH=trading.db` so SQLite lives on the disk

### 4) Environment Variables
Set in Render → Service → Environment (copy values from your `backend/.env`):

- **Alpaca**
  - `ALPACA_API_KEY`
  - `ALPACA_SECRET_KEY`
  - `ALPACA_BASE_URL=https://paper-api.alpaca.markets`
- **Flask**
  - `SECRET_KEY=<strong-random-string>`
- **Database**
  - `DATABASE_PATH=trading.db`
- **Algorithm**
  - `ALGORITHM_ENABLED=true`
  - `TRADING_ENABLED=true` (paper)
  - `MAX_POSITIONS=15`
  - `STOP_LOSS_PERCENT=0.07`
  - `INITIAL_CAPITAL=50000`
  - `RELAXED_FILTERS=false`
  - `ALLOW_AFTER_HOURS=true`
  - `EXTENDED_HOURS=true`
- **Scheduler**
  - `SCHEDULE_ENABLED=true`
  - `SCHEDULE_TIMEZONE=America/New_York`
  - `SCHEDULE_TIMES=17:00`
- **Logging**
  - `LOG_LEVEL=INFO`
  - `LOG_FILE=trading_system.log`

### 5) Health Check
- Service → Settings → Health Check Path = `/api/health`

### 6) Deploy and Validate
- After deploy, open the service URL.
- UI (served by Flask): navigate to `/` and browse Dashboard, Runs, Signals, Positions, Trades, Diagnostics, Performance.
- API smoke tests:
  - `GET /api/health`
  - `GET /api/runs?per_page=5`
  - `GET /api/performance/summary`
  - Optional: `POST /api/algorithm/run` (manual run)

### 7) Scheduler Verification
- Around 5:00pm ET, logs should show: `Scheduled job: running daily trading algorithm`.
- `GET /api/runs` should show a new run entry.

### Notes
- CORS: Not required with single-service (same origin). If you later split services, restrict CORS in `backend/app.py` to your frontend domain.
- Security (optional): Add a bearer token for write endpoints (`POST /api/algorithm/run`, `POST /api/sync`).
- Backups (optional): Use APScheduler to copy `trading.db` nightly to a dated backup; optionally upload to cloud storage.

## 🤝 Contributing

1. Always test with paper trading first
2. Run validation tests before committing
3. Follow the phased development approach
4. Maintain comprehensive logging

## ⚠️ Disclaimer

This is a personal trading system for educational and research purposes. Past performance does not guarantee future results. Always use paper trading for development and testing.

## 📞 Support

For issues or questions:
1. Check the logs (`trading_system.log`)
2. Run the validation test script
3. Verify environment variables
4. Check Alpaca API credentials and permissions
#   m o m e n t u m _ a l g o _ w e b s i t e  
 