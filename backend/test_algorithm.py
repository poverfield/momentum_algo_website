"""
Test script for validating the trading algorithm
Run this to test Phase 1 - Algorithm Validation
"""
import os
import sys
import logging
from datetime import date, datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the backend directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.database_service import DatabaseService
from services.market_data_service import MarketDataService
from services.alpaca_service import AlpacaService
from services.trading_algorithm import TradingAlgorithm

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('test_algorithm.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def test_services():
    """Test all services individually"""
    logger.info("=" * 50)
    logger.info("TESTING INDIVIDUAL SERVICES")
    logger.info("=" * 50)
    
    # Test Database Service
    logger.info("Testing Database Service...")
    db_service = DatabaseService()
    if db_service.is_connected():
        logger.info("✓ Database service connected successfully")
    else:
        logger.error("✗ Database service connection failed")
        return False
    
    # Test Market Data Service
    logger.info("Testing Market Data Service...")
    market_data_service = MarketDataService()
    
    # Test S&P 500 ticker fetching
    tickers = market_data_service.get_sp500_tickers()
    if tickers and len(tickers) > 0:
        logger.info(f"✓ Retrieved {len(tickers)} S&P 500 tickers")
        logger.info(f"Sample tickers: {tickers[:10]}")
    else:
        logger.error("✗ Failed to retrieve S&P 500 tickers")
        return False
    
    # Test market data fetching (small sample)
    logger.info("Testing market data fetching...")
    sample_tickers = tickers[:5]  # Test with first 5 tickers
    market_data = market_data_service.get_daily_market_data(date.today(), sample_tickers, days_back=300)
    
    if not market_data.empty:
        logger.info(f"✓ Retrieved market data: {market_data.shape[0]} days, {market_data.shape[1]} tickers")
        logger.info(f"Date range: {market_data.index[0]} to {market_data.index[-1]}")
    else:
        logger.error("✗ Failed to retrieve market data")
        return False
    
    # Test technical indicators
    logger.info("Testing technical indicators...")
    sample_symbol = sample_tickers[0]
    sample_data = market_data[sample_symbol].dropna()
    
    macd_data = market_data_service.calculate_macd(sample_data)
    rsi_data = market_data_service.calculate_rsi(sample_data)
    
    if macd_data is not None and rsi_data is not None:
        logger.info(f"✓ Technical indicators calculated for {sample_symbol}")
        logger.info(f"Latest MACD: {macd_data['macd'].iloc[-1]:.4f}")
        logger.info(f"Latest RSI: {rsi_data['rsi'].iloc[-1]:.2f}")
    else:
        logger.error("✗ Failed to calculate technical indicators")
        return False
    
    # Test Alpaca Service (if credentials provided)
    logger.info("Testing Alpaca Service...")
    alpaca_service = AlpacaService()
    
    if alpaca_service.is_connected():
        logger.info("✓ Alpaca service connected successfully")
        
        # Get account info
        account_info = alpaca_service.get_account_info()
        if account_info:
            logger.info(f"Account Status: {account_info['status']}")
            logger.info(f"Portfolio Value: ${account_info['portfolio_value']:,.2f}")
            logger.info(f"Buying Power: ${account_info['buying_power']:,.2f}")
        
        # Get current positions
        positions = alpaca_service.get_positions()
        logger.info(f"Current positions: {len(positions)}")
        
    else:
        logger.warning("⚠ Alpaca service not connected (check API credentials)")
        logger.info("This is OK for initial testing - you can set up Alpaca credentials later")
    
    return True

def test_algorithm():
    """Test the complete trading algorithm"""
    logger.info("=" * 50)
    logger.info("TESTING TRADING ALGORITHM")
    logger.info("=" * 50)
    
    try:
        # Initialize services
        db_service = DatabaseService()
        market_data_service = MarketDataService()
        alpaca_service = AlpacaService()
        
        # Initialize algorithm
        trading_algorithm = TradingAlgorithm(alpaca_service, db_service, market_data_service)
        
        logger.info("Testing signal generation...")
        
        # Generate signals for today (or most recent trading day)
        test_date = date.today()
        signals = trading_algorithm.generate_daily_signals(test_date)
        
        if signals:
            logger.info(f"✓ Generated {len(signals)} buy signals")
            
            # Show top 5 signals
            logger.info("Top 5 signals:")
            for i, signal in enumerate(signals[:5]):
                logger.info(f"  {i+1}. {signal['symbol']}: "
                           f"strength={signal['signal_strength']:.3f}, "
                           f"rank={signal['momentum_rank']}, "
                           f"RSI={signal['rsi_value']:.1f}")
        else:
            logger.warning("⚠ No buy signals generated (this could be normal depending on market conditions)")
        
        # Test sell signal checking (will be empty if no positions)
        logger.info("Testing sell signal generation...")
        sell_signals = trading_algorithm.check_sell_signals(test_date)
        
        if sell_signals:
            logger.info(f"✓ Generated {len(sell_signals)} sell signals")
        else:
            logger.info("No sell signals (no current positions)")
        
        # Test full algorithm run (without actual trading)
        logger.info("Testing full algorithm run...")
        
        # Temporarily disable trading for test
        original_trading_enabled = trading_algorithm.trading_enabled
        trading_algorithm.trading_enabled = False
        
        result = trading_algorithm.run_daily_algorithm()
        
        # Restore original setting
        trading_algorithm.trading_enabled = original_trading_enabled
        
        if result['status'] == 'success':
            logger.info("✓ Full algorithm run completed successfully")
            logger.info(f"Signals generated: {result['signals_generated']}")
            logger.info(f"Execution time: {result['execution_time']}s")
        else:
            logger.error(f"✗ Algorithm run failed: {result.get('error', 'Unknown error')}")
            return False
        
        return True
        
    except Exception as e:
        logger.error(f"✗ Algorithm test failed: {e}")
        return False

def test_database_operations():
    """Test database operations"""
    logger.info("=" * 50)
    logger.info("TESTING DATABASE OPERATIONS")
    logger.info("=" * 50)
    
    try:
        db_service = DatabaseService()
        
        # Test logging a sample trade
        logger.info("Testing trade logging...")
        trade_id = db_service.log_trade(
            trade_date=date.today(),
            symbol='TEST',
            action='BUY',
            quantity=100,
            price=150.25,
            signal_strength=0.85,
            reason='test'
        )
        
        if trade_id:
            logger.info(f"✓ Trade logged with ID: {trade_id}")
        else:
            logger.error("✗ Failed to log trade")
            return False
        
        # Test position update
        logger.info("Testing position update...")
        db_service.update_position(
            symbol='TEST',
            quantity=100,
            avg_entry_price=150.25,
            entry_date=date.today(),
            current_price=155.50
        )
        logger.info("✓ Position updated")
        
        # Test getting positions
        positions = db_service.get_current_positions()
        logger.info(f"✓ Retrieved {len(positions)} positions")
        
        # Test algorithm run logging
        logger.info("Testing algorithm run logging...")
        db_service.log_algorithm_run(
            run_date=date.today(),
            status='test',
            signals_generated=5,
            trades_executed=0,
            execution_time=30,
            top_momentum_stocks=['AAPL', 'MSFT', 'GOOGL']
        )
        logger.info("✓ Algorithm run logged")
        
        # Clean up test data
        logger.info("Cleaning up test data...")
        db_service.remove_position('TEST')
        logger.info("✓ Test data cleaned up")
        
        return True
        
    except Exception as e:
        logger.error(f"✗ Database test failed: {e}")
        return False

def main():
    """Run all tests"""
    logger.info("STARTING ALGORITHM VALIDATION TESTS")
    logger.info(f"Test started at: {datetime.now()}")
    
    # Check environment variables
    logger.info("Checking environment configuration...")
    required_vars = ['DATABASE_PATH', 'INITIAL_CAPITAL', 'MAX_POSITIONS', 'STOP_LOSS_PERCENT']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        logger.warning(f"Missing environment variables: {missing_vars}")
        logger.info("Using default values for missing variables")
    else:
        logger.info("✓ All required environment variables found")
    
    # Run tests
    tests_passed = 0
    total_tests = 3
    
    if test_services():
        tests_passed += 1
        logger.info("✓ Services test PASSED")
    else:
        logger.error("✗ Services test FAILED")
    
    if test_database_operations():
        tests_passed += 1
        logger.info("✓ Database operations test PASSED")
    else:
        logger.error("✗ Database operations test FAILED")
    
    if test_algorithm():
        tests_passed += 1
        logger.info("✓ Algorithm test PASSED")
    else:
        logger.error("✗ Algorithm test FAILED")
    
    # Summary
    logger.info("=" * 50)
    logger.info("TEST SUMMARY")
    logger.info("=" * 50)
    logger.info(f"Tests passed: {tests_passed}/{total_tests}")
    
    if tests_passed == total_tests:
        logger.info("🎉 ALL TESTS PASSED! Algorithm validation successful.")
        logger.info("You can now proceed to Phase 2: Core Backend Development")
    else:
        logger.error("❌ Some tests failed. Please fix the issues before proceeding.")
    
    logger.info(f"Test completed at: {datetime.now()}")

if __name__ == "__main__":
    main()
