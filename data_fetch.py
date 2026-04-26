import yfinance as yf
import pandas as pd
import numpy as np
import time
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from config import *

def load_universe():
    df = pd.read_csv(UNIVERSE_FILE)
    symbols = df["Symbol"].dropna().tolist()
    symbols = [
        s.strip() + ".NS" if not str(s).strip().endswith(".NS")
        else s.strip()
        for s in symbols
    ]
    return symbols

def make_session():
    """Requests session with retry logic and browser-like headers."""
    session = requests.Session()
    retry = Retry(
        total=5,
        backoff_factor=2,
        status_forcelist=[429, 500, 502, 503, 504]
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    })
    return session

def fetch_benchmark():
    """Fetch Nifty 50 with retries."""
    session = make_session()
    candidates = ["^NSEI", "NIFTYBEES.NS", "JUNIORBEES.NS"]
    for ticker in candidates:
        for attempt in range(3):
            try:
                t = yf.Ticker(ticker, session=session)
                df = t.history(period=f"{LOOKBACK_DAYS}d", auto_adjust=True)
                if df is not None and not df.empty and len(df) > 50:
                    print(f"  Benchmark fetched: {ticker}")
                    return df["Close"]
            except Exception as e:
                print(f"  Benchmark attempt {attempt+1} failed for {ticker}: {e}")
                time.sleep(3 * (attempt + 1))
    print("  WARNING: All benchmark tickers failed. Regime = UNKNOWN.")
    return None

def fetch_all(symbols):
    """
    Bulk download in batches of 100.
    yfinance bulk download is far more reliable on cloud IPs
    than individual ticker fetches.
    """
    session  = make_session()
    data     = {}
    failed   = []
    batch_size = 100

    batches = [symbols[i:i+batch_size] for i in range(0, len(symbols), batch_size)]

    for batch_num, batch in enumerate(batches):
        print(f"  Downloading batch {batch_num+1}/{len(batches)} ({len(batch)} symbols)...")

        for attempt in range(3):
            try:
                raw = yf.download(
                    tickers=batch,
                    period=f"{LOOKBACK_DAYS}d",
                    interval="1d",
                    auto_adjust=True,
                    group_by="ticker",
                    threads=True,
                    progress=False,
                    session=session,
                )
                break
            except Exception as e:
                print(f"    Batch {batch_num+1} attempt {attempt+1} failed: {e}")
                time.sleep(5 * (attempt + 1))
                if attempt == 2:
                    print(f"    Skipping batch {batch_num+1}")
                    raw = pd.DataFrame()

        if raw.empty:
            failed.extend(batch)
            continue

        # Parse multi-ticker download output
        for sym in batch:
            try:
                if len(batch) == 1:
                    df = raw.copy()
                else:
                    if sym not in raw.columns.get_level_values(0):
                        failed.append(sym)
                        continue
                    df = raw[sym].copy()

                df = df[["Open", "High", "Low", "Close", "Volume"]].copy()
                df.dropna(subset=["Close"], inplace=True)
                df.index = pd.to_datetime(df.index)

                if len(df) < 60:
                    failed.append(sym)
                    continue

                data[sym] = df

            except Exception:
                failed.append(sym)

        # Polite delay between batches to avoid rate limiting
        if batch_num < len(batches) - 1:
            time.sleep(2)

    print(f"\n  Done. Successful: {len(data)} | Failed: {len(failed)}")
    if failed:
        pd.Series(failed).to_csv("failed_symbols.csv", index=False, header=["Symbol"])
        print(f"  Failed symbols saved to failed_symbols.csv")

    return data