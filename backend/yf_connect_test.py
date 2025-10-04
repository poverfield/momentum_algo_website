import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

# How many years of daily data to pull
years = 2

end_date = datetime.now()
start_date = end_date - timedelta(days=years * 365)

print("yfinance version:", getattr(yf, "__version__", "unknown"))
print("Start:", start_date.strftime('%Y-%m-%d'))
print("End  :", end_date.strftime('%Y-%m-%d'))

# Simplest possible download call for a single ticker
try:
    aapl_data = yf.download(
        'AAPL',
        start=start_date.strftime('%Y-%m-%d'),
        end=end_date.strftime('%Y-%m-%d'),
        progress=False
    )
    print("Downloaded rows:", len(aapl_data))
    print(aapl_data.head())
except Exception as e:
    print("Error while downloading with yfinance:", repr(e))
