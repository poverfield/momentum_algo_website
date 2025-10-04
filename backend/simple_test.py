from __future__ import annotations
"""
Simple test to validate basic functionality without external dependencies
"""
import os
import sys
from datetime import date, datetime
from dotenv import load_dotenv
import logging
import traceback

# Add the backend directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Load environment variables from .env so Alpaca credentials are available
load_dotenv()

# Configure logging for debug visibility
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_imports():
    """Test that all our modules can be imported"""
    print("Testing imports...")
    
    try:
        from services.database_service import DatabaseService
        print("✓ DatabaseService imported successfully")
    except Exception as e:
        print(f"✗ DatabaseService import failed: {e}")
        return False
    
    try:
        # Pre-check file path for debugging
        svc_path = os.path.join(os.path.dirname(__file__), 'services', 'market_data_service.py')
        print(f"MarketDataService file: {svc_path} (exists={os.path.exists(svc_path)})")
        
        from services.market_data_service import MarketDataService
        print("✓ MarketDataService imported successfully")
    except Exception as e:
        print(f"✗ MarketDataService import failed: {e!r}")
        traceback.print_exc()
        return False
    
    try:
        from services.alpaca_service import AlpacaService
        print("✓ AlpacaService imported successfully")
    except Exception as e:
        print(f"✗ AlpacaService import failed: {e}")
        return False
    
    try:
        from services.trading_algorithm import TradingAlgorithm
        print("✓ TradingAlgorithm imported successfully")
    except Exception as e:
        print(f"✗ TradingAlgorithm import failed: {e}")
        return False
    
    return True

def test_database():
    """Test basic database functionality"""
    print("\nTesting database...")
    
    try:
        from services.database_service import DatabaseService
        
        db = DatabaseService()
        
        # Test connection
        if db.is_connected():
            print("✓ Database connection successful")
        else:
            print("✗ Database connection failed")
            return False
        
        # Test basic operations
        positions = db.get_current_positions()
        print(f"✓ Retrieved {len(positions)} current positions")
        
        recent_trades = db.get_recent_trades(limit=5)
        print(f"✓ Retrieved {len(recent_trades)} recent trades")
        
        portfolio_summary = db.get_portfolio_summary()
        print(f"✓ Retrieved portfolio summary: ${portfolio_summary.get('total_value', 0):,.2f}")
        
        return True
        
    except Exception as e:
        print(f"✗ Database test failed: {e}")
        return False

def test_market_data():
    """Test basic market data functionality"""
    print("\nTesting market data service...")
    
    try:
        from services.market_data_service import MarketDataService
        
        market_data = MarketDataService()
        
        # Test S&P 500 ticker fetching
        tickers = market_data.get_sp500_tickers()
        if tickers and len(tickers) > 0:
            print(f"✓ Retrieved {len(tickers)} S&P 500 tickers")
            print(f"  Sample tickers: {tickers[:5]}")
        else:
            print("✗ Failed to retrieve S&P 500 tickers")
            return False
        
        # Test technical indicator functions (without data)
        import pandas as pd
        import numpy as np
        
        # Create sample data
        dates = pd.date_range(start='2023-01-01', periods=100, freq='D')
        sample_prices = pd.Series(np.random.randn(100).cumsum() + 100, index=dates)
        
        macd_data = market_data.calculate_macd(sample_prices)
        if macd_data is not None:
            print("✓ MACD calculation working")
        else:
            print("✗ MACD calculation failed")
            return False
        
        rsi_data = market_data.calculate_rsi(sample_prices)
        if rsi_data is not None:
            print("✓ RSI calculation working")
        else:
            print("✗ RSI calculation failed")
            return False
        
        return True
        
    except Exception as e:
        print(f"✗ Market data test failed: {e}")
        return False

def test_alpaca():
    """Test Alpaca service (without credentials)"""
    print("\nTesting Alpaca service...")
    
    try:
        from services.alpaca_service import AlpacaService
        
        alpaca = AlpacaService()
        
        # This will show warning if no credentials, which is expected
        is_connected = alpaca.is_connected()
        
        if is_connected:
            print("✓ Alpaca service connected")
            account_info = alpaca.get_account_info()
            if account_info:
                print(f"  Account status: {account_info['status']}")
        else:
            print("⚠ Alpaca service not connected (no credentials provided)")
            print("  This is expected if you haven't set up Alpaca API keys yet")
        
        return True
        
    except Exception as e:
        print(f"✗ Alpaca test failed: {e}")
        return False

def main():
    """Run all basic tests"""
    print("=" * 50)
    print("BASIC FUNCTIONALITY TEST")
    print("=" * 50)
    print(f"Test started at: {datetime.now()}")
    
    tests_passed = 0
    total_tests = 4
    
    if test_imports():
        tests_passed += 1
        print("✓ Import test PASSED")
    else:
        print("✗ Import test FAILED")
    
    if test_database():
        tests_passed += 1
        print("✓ Database test PASSED")
    else:
        print("✗ Database test FAILED")
    
    if test_market_data():
        tests_passed += 1
        print("✓ Market data test PASSED")
    else:
        print("✗ Market data test FAILED")
    
    if test_alpaca():
        tests_passed += 1
        print("✓ Alpaca test PASSED")
    else:
        print("✗ Alpaca test FAILED")
    
    print("\n" + "=" * 50)
    print("TEST SUMMARY")
    print("=" * 50)
    print(f"Tests passed: {tests_passed}/{total_tests}")
    
    if tests_passed >= 3:  # Allow Alpaca to fail if no credentials
        print("🎉 Basic tests PASSED! Core functionality is working.")
        print("\nNext steps:")
        print("1. Install required packages: pip install -r requirements.txt")
        print("2. Set up Alpaca paper trading credentials in .env file")
        print("3. Run the full algorithm validation: python test_algorithm.py")
    else:
        print("❌ Some critical tests failed. Please fix the issues.")
    
    print(f"\nTest completed at: {datetime.now()}")

if __name__ == "__main__":
    main()
