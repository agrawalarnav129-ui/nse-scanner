import yfinance as yf
import pandas as pd
import numpy as np
from config import *

def load_universe():
    df = pd.read_csv(UNIVERSE_FILE)
    symbols = df["Symbol"].dropna().tolist()
    # Auto-append .NS if not already present
    symbols = [s.strip() + ".NS" if not str(s).strip().endswith(".NS") else s.strip() for s in symbols]
    return symbols

def fetch_stock(symbol, period_days=LOOKBACK_DAYS):
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=f"{period_days}d", interval="1d", auto_adjust=True)
        if df.empty or len(df) < 60:
            return None
        df.index = pd.to_datetime(df.index)
        df = df[["Open", "High", "Low", "Close", "Volume"]].copy()
        df.dropna(inplace=True)
        return df
    except Exception:
        return None

def fetch_benchmark():
    try:
        # ^NSEI = Nifty 50, no .NS suffix needed for indices
        df = yf.Ticker("^NSEI").history(period=f"{LOOKBACK_DAYS}d", auto_adjust=True)
        return df["Close"]
    except Exception:
        return None

def fetch_all(symbols):
    data = {}
    failed = []

    for i, sym in enumerate(symbols):
        df = fetch_stock(sym)
        if df is not None:
            data[sym] = df
        else:
            failed.append(sym)

        if i % 50 == 0:
            print(f"  Fetched {i}/{len(symbols)} — success so far: {len(data)}")

    print(f"\n  Done. Successful: {len(data)} | Failed/skipped: {len(failed)}")
    if failed:
        # Save failed symbols so you can inspect/fix them
        pd.Series(failed).to_csv("failed_symbols.csv", index=False, header=["Symbol"])
        print(f"  Failed symbols saved to failed_symbols.csv")

    return data