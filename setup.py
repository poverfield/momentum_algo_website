"""
Setup script for the Personal Automated Trading System
Run this to set up the development environment
"""
import os
import subprocess
import sys
from pathlib import Path

def run_command(command, description):
    """Run a command and handle errors"""
    print(f"\n{description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✓ {description} completed successfully")
        if result.stdout:
            print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ {description} failed")
        if e.stderr:
            print(f"Error: {e.stderr}")
        return False

def check_python_version():
    """Check if Python version is compatible"""
    print("Checking Python version...")
    version = sys.version_info
    if version.major == 3 and version.minor >= 9:
        print(f"✓ Python {version.major}.{version.minor}.{version.micro} is compatible")
        return True
    else:
        print(f"✗ Python {version.major}.{version.minor}.{version.micro} is not compatible")
        print("Please install Python 3.9 or higher")
        return False

def setup_backend():
    """Set up the backend environment"""
    print("\n" + "=" * 50)
    print("SETTING UP BACKEND")
    print("=" * 50)
    
    # Change to backend directory
    backend_dir = Path(__file__).parent / "backend"
    os.chdir(backend_dir)
    
    # Install Python packages
    if not run_command("pip install -r requirements.txt", "Installing Python packages"):
        print("Note: Some packages might fail to install. This is common with TA-Lib.")
        print("You can continue without TA-Lib for basic functionality.")
    
    # Create .env file if it doesn't exist
    if not os.path.exists('.env'):
        print("\nCreating .env file...")
        with open('.env', 'w') as f:
            f.write("""# Alpaca API (use paper trading initially)
ALPACA_API_KEY=
ALPACA_SECRET_KEY=
ALPACA_BASE_URL=https://paper-api.alpaca.markets

# Flask Configuration
FLASK_ENV=development
SECRET_KEY=dev-secret-key-change-in-production

# Database
DATABASE_PATH=trading.db

# Algorithm Settings
ALGORITHM_ENABLED=true
TRADING_ENABLED=false
MAX_POSITIONS=15
STOP_LOSS_PERCENT=0.07
INITIAL_CAPITAL=50000

# Market Data
DATA_SOURCE=yfinance
MARKET_TIMEZONE=America/New_York

# Logging
LOG_LEVEL=INFO
LOG_FILE=trading_system.log
""")
        print("✓ Created .env file")
    else:
        print("✓ .env file already exists")
    
    return True

def run_basic_test():
    """Run basic functionality test"""
    print("\n" + "=" * 50)
    print("RUNNING BASIC TESTS")
    print("=" * 50)
    
    return run_command("python simple_test.py", "Running basic functionality test")

def main():
    """Main setup function"""
    print("=" * 60)
    print("PERSONAL AUTOMATED TRADING SYSTEM - SETUP")
    print("=" * 60)
    
    # Check Python version
    if not check_python_version():
        return
    
    # Set up backend
    if not setup_backend():
        print("Backend setup failed")
        return
    
    # Run basic test
    run_basic_test()
    
    print("\n" + "=" * 60)
    print("SETUP COMPLETE")
    print("=" * 60)
    
    print("\nNext steps:")
    print("1. Set up Alpaca paper trading account at: https://alpaca.markets/")
    print("2. Get your paper trading API keys")
    print("3. Add your API keys to backend/.env file:")
    print("   ALPACA_API_KEY=your_key_here")
    print("   ALPACA_SECRET_KEY=your_secret_here")
    print("4. Run full algorithm validation:")
    print("   cd backend && python test_algorithm.py")
    print("5. Start the Flask application:")
    print("   cd backend && python app.py")
    
    print("\n📚 Documentation:")
    print("- README.md for detailed setup instructions")
    print("- project_details.md for algorithm specifications")
    
    print("\n⚠️  Important:")
    print("- Always use paper trading for development")
    print("- Set TRADING_ENABLED=false until you're ready")
    print("- Monitor logs in backend/trading_system.log")

if __name__ == "__main__":
    main()
