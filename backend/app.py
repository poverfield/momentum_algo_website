"""
Main Flask application for the Personal Automated Trading System
"""
import os
from flask import Flask, jsonify, request, send_from_directory, g, has_request_context
from flask_cors import CORS
from dotenv import load_dotenv
import logging
from logging.handlers import RotatingFileHandler
import uuid
from datetime import datetime
from typing import List
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz

# Load environment variables
load_dotenv()

# Import our services
from services.database_service import DatabaseService
from services.trading_algorithm import TradingAlgorithm
from services.market_data_service import MarketDataService
from services.alpaca_service import AlpacaService

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key')

# Enable CORS for frontend
CORS(app)

class RequestIdFilter(logging.Filter):
    def filter(self, record):
        try:
            if has_request_context():
                record.request_id = getattr(g, 'request_id', '-')
            else:
                record.request_id = '-'
        except Exception:
            record.request_id = '-'
        return True

# Configure logging with rotation and request_id
log_level = getattr(logging, os.getenv('LOG_LEVEL', 'INFO'))
log_file = os.getenv('LOG_FILE', 'trading_system.log')
formatter = logging.Formatter('%(asctime)s %(levelname)s [%(request_id)s] %(name)s: %(message)s')
rotating = RotatingFileHandler(log_file, maxBytes=5_000_000, backupCount=3, encoding='utf-8')
rotating.setLevel(log_level)
rotating.setFormatter(formatter)
rotating.addFilter(RequestIdFilter())

stream = logging.StreamHandler()
stream.setLevel(log_level)
stream.setFormatter(formatter)
stream.addFilter(RequestIdFilter())

root_logger = logging.getLogger()
root_logger.setLevel(log_level)
root_logger.handlers = [rotating, stream]

logger = logging.getLogger(__name__)

# Initialize services
db_service = DatabaseService()
market_data_service = MarketDataService()
alpaca_service = AlpacaService()
trading_algorithm = TradingAlgorithm(alpaca_service, db_service, market_data_service)

# Scheduler setup
scheduler = None

def schedule_algorithm_runs():
    global scheduler
    try:
        enabled = os.getenv('SCHEDULE_ENABLED', 'true').lower() == 'true'
        if not enabled:
            logger.info("Scheduler disabled via SCHEDULE_ENABLED=false")
            return
        tz_name = os.getenv('SCHEDULE_TIMEZONE', 'America/New_York')
        tz = pytz.timezone(tz_name)
        # Default to 16:05 (4:05pm) local market time (ET) right after close
        times_env = os.getenv('SCHEDULE_TIMES', '16:05')
        times: List[str] = [t.strip() for t in times_env.split(',') if t.strip()]

        scheduler = BackgroundScheduler(timezone=tz)

        def job_wrapper():
            try:
                logger.info("Scheduled job: running daily trading algorithm")
                trading_algorithm.run_daily_algorithm()
            except Exception as e:
                logger.error(f"Scheduled job failed: {e}")

        for t in times:
            try:
                hh, mm = t.split(':')
                trigger = CronTrigger(day_of_week='mon-fri', hour=int(hh), minute=int(mm), timezone=tz)
                scheduler.add_job(job_wrapper, trigger, name=f"daily_run_{hh}{mm}")
                logger.info(f"Scheduled algorithm run at {t} {tz_name} (Mon-Fri)")
            except Exception as e:
                logger.error(f"Invalid schedule time '{t}': {e}")

        scheduler.start()
    except Exception as e:
        logger.error(f"Error starting scheduler: {e}")

@app.before_request
def add_request_id():
    g.request_id = str(uuid.uuid4())

@app.after_request
def add_request_id_header(response):
    response.headers['X-Request-ID'] = getattr(g, 'request_id', '-')
    return response

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'services': {
            'database': db_service.is_connected(),
            'alpaca': alpaca_service.is_connected(),
            'algorithm': True
        }
    })

@app.route('/api/account', methods=['GET'])
def get_account():
    """Return Alpaca account summary (portfolio_value, cash, buying_power)."""
    try:
        info = alpaca_service.get_account_info()
        if info is None:
            return jsonify({'error': 'Alpaca not connected'}), 503
        return jsonify({
            'portfolio_value': info.get('portfolio_value'),
            'cash': info.get('cash'),
            'buying_power': info.get('buying_power'),
            'status': info.get('status'),
            'currency': info.get('currency')
        })
    except Exception as e:
        logger.error(f"Error getting account info: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/dashboard', methods=['GET'])
def get_dashboard():
    """Get dashboard data including portfolio summary and recent activity"""
    try:
        # Get portfolio summary
        portfolio_summary = db_service.get_portfolio_summary()
        
        # Get recent trades
        recent_trades = db_service.get_recent_trades(limit=10)
        
        # Get current positions
        current_positions = db_service.get_current_positions()
        
        # Get algorithm status
        algorithm_status = db_service.get_latest_algorithm_run()
        
        return jsonify({
            'portfolio_summary': portfolio_summary,
            'recent_trades': recent_trades,
            'current_positions': current_positions,
            'algorithm_status': algorithm_status
        })
    except Exception as e:
        logger.error(f"Error getting dashboard data: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/performance/summary', methods=['GET'])
def performance_summary():
    try:
        summary = db_service.get_performance_summary_wow_mom_yoy()
        return jsonify(summary)
    except Exception as e:
        logger.error(f"Error getting performance summary: {e}")
        return jsonify({'error': str(e)}), 500

# Frontend assets directory (React production build)
FRONTEND_DIR = os.path.join(os.path.dirname(__file__), '..', 'frontend', 'dist')

@app.route('/api/signals', methods=['GET'])
def get_signals():
    """Get daily signals with pagination and optional filters"""
    try:
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 50))
        signal_date = request.args.get('date')
        symbol = request.args.get('symbol')

        signals, total = db_service.get_signals_paginated(page, per_page, signal_date, symbol)
        return jsonify({
            'signals': signals,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total,
                'pages': (total + per_page - 1) // per_page
            }
        })
    except Exception as e:
        logger.error(f"Error getting signals: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/runs', methods=['GET'])
def get_runs():
    """Get algorithm runs with pagination and optional filters"""
    try:
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 50))
        status = request.args.get('status')
        run_date = request.args.get('date')

        runs, total = db_service.get_algorithm_runs_paginated(page, per_page, status, run_date)
        return jsonify({
            'runs': runs,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total,
                'pages': (total + per_page - 1) // per_page
            }
        })
    except Exception as e:
        logger.error(f"Error getting runs: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/positions', methods=['GET'])
def get_positions():
    """Get current positions from database"""
    try:
        positions = db_service.get_current_positions()
        return jsonify({'positions': positions})
    except Exception as e:
        logger.error(f"Error getting positions: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/positions/refresh', methods=['POST'])
def refresh_positions():
    """Fetch live positions from Alpaca and return them without persisting."""
    try:
        # Pull positions directly from Alpaca
        live_positions = alpaca_service.get_positions()

        # Normalize to frontend schema expected by Positions.jsx
        normalized = []
        for p in live_positions:
            try:
                symbol = p.get('symbol')
                qty = int(p.get('quantity') or 0)
                avg_entry = float(p.get('avg_entry_price')) if p.get('avg_entry_price') is not None else None
                current_price = float(p.get('current_price')) if p.get('current_price') is not None else None

                unrealized = None
                unrealized_pct = None
                if avg_entry is not None and current_price is not None:
                    unrealized = (current_price - avg_entry) * qty
                    if avg_entry != 0:
                        unrealized_pct = ((current_price - avg_entry) / avg_entry) * 100.0

                normalized.append({
                    'symbol': symbol,
                    'quantity': qty,
                    'entry_price': avg_entry,
                    'entry_date': None,
                    'current_price': current_price,
                    'unrealized_pnl': unrealized,
                    'unrealized_pnl_pct': unrealized_pct
                })
            except Exception as inner_e:
                logger.warning(f"Failed to normalize position {p}: {inner_e}")
        from datetime import datetime
        synced_at = datetime.now().isoformat()
        return jsonify({'positions': normalized, 'source': 'alpaca', 'synced_at': synced_at})
    except Exception as e:
        logger.error(f"Error refreshing positions from Alpaca: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/diagnostics', methods=['GET'])
def get_diagnostics():
    """Return MACD/RSI diagnostics over a subset of tickers"""
    try:
        sample_n = int(request.args.get('sample_n', 50))
        days_back = int(request.args.get('days_back', 600))
        tickers = market_data_service.get_sp500_tickers()[:sample_n]
        from datetime import date
        data = market_data_service.get_daily_market_data(date.today(), tickers, days_back=days_back)
        passed_macd = []
        passed_rsi = []
        passed_both = []
        for symbol in data.columns:
            series = data[symbol].dropna()
            macd_df = market_data_service.calculate_macd(series)
            rsi_df = market_data_service.calculate_rsi(series)
            if macd_df is None or rsi_df is None or len(macd_df) < 2 or len(rsi_df) < 2:
                continue
            current_macd, prev_macd = macd_df['macd'].iloc[-1], macd_df['macd'].iloc[-2]
            macd_ok = (current_macd > 0 and prev_macd <= 0) or (current_macd > prev_macd and current_macd > 0)
            current_rsi, prev_rsi = rsi_df['rsi'].iloc[-1], rsi_df['rsi'].iloc[-2]
            rsi_ok = (current_rsi > 50 and prev_rsi <= 50) or (current_rsi > 30 and prev_rsi <= 30)
            if macd_ok:
                passed_macd.append(symbol)
            if rsi_ok:
                passed_rsi.append(symbol)
            if macd_ok and rsi_ok:
                passed_both.append(symbol)
        return jsonify({
            'sample_size': len(tickers),
            'days': int(data.shape[0]) if not data.empty else 0,
            'macd_ok_count': len(passed_macd),
            'rsi_ok_count': len(passed_rsi),
            'both_ok_count': len(passed_both),
            'macd_ok_sample': passed_macd[:10],
            'rsi_ok_sample': passed_rsi[:10],
            'both_ok_sample': passed_both[:10]
        })
    except Exception as e:
        logger.error(f"Error computing diagnostics: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/trades', methods=['GET'])
def get_trades():
    """Get trade history with pagination"""
    try:
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 50))
        
        trades, total = db_service.get_trades_paginated(page, per_page)
        
        return jsonify({
            'trades': trades,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total,
                'pages': (total + per_page - 1) // per_page
            }
        })
    except Exception as e:
        logger.error(f"Error getting trades: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/performance', methods=['GET'])
def get_performance():
    """Get performance metrics and benchmark comparison"""
    try:
        metrics = db_service.get_performance_metrics()
        benchmark_comparison = db_service.get_benchmark_comparison()
        monthly_returns = db_service.get_monthly_returns()
        
        return jsonify({
            'metrics': metrics,
            'benchmark_comparison': benchmark_comparison,
            'monthly_returns': monthly_returns
        })
    except Exception as e:
        logger.error(f"Error getting performance data: {e}")
        return jsonify({'error': str(e)}), 500

# Frontend routes (registered AFTER API routes)
@app.route('/')
def serve_index():
    try:
        return send_from_directory(FRONTEND_DIR, 'index.html')
    except Exception as e:
        logger.error(f"Error serving index.html: {e}")
        return jsonify({'error': 'Frontend not found'}), 404

@app.route('/<path:path>')
def serve_static(path):
    # Don't hijack API routes
    if path.startswith('api/'):
        return jsonify({'error': 'Not found'}), 404
    # Try to serve the static asset; fall back to index.html for SPA routes
    full_path = os.path.join(FRONTEND_DIR, path)
    if os.path.exists(full_path):
        return send_from_directory(FRONTEND_DIR, path)
    return send_from_directory(FRONTEND_DIR, 'index.html')

@app.route('/api/algorithm/run', methods=['POST'])
def run_algorithm():
    """Manually trigger algorithm run (for testing)"""
    try:
        if not os.getenv('ALGORITHM_ENABLED', 'false').lower() == 'true':
            return jsonify({'error': 'Algorithm is disabled'}), 400
            
        result = trading_algorithm.run_daily_algorithm()
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error running algorithm: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/sync', methods=['POST'])
def sync_data():
    """Manual data refresh hook (placeholder)"""
    try:
        # Placeholder: could prefetch popular tickers or clear caches
        return jsonify({'status': 'ok', 'message': 'Sync requested'}), 200
    except Exception as e:
        logger.error(f"Error during sync: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    # Initialize database on startup
    db_service.initialize_database()
    
    # Start scheduler
    schedule_algorithm_runs()
    
    # Start Flask app
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('FLASK_ENV') == 'development'
    
    logger.info(f"Starting trading system on port {port}")
    app.run(host='0.0.0.0', port=port, debug=debug)
