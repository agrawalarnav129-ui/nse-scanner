import yfinance as yf
import pandas as pd
import numpy as np
import time
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

def fetch_benchmark():
    candidates = ["^NSEI", "NIFTYBEES.NS", "JUNIORBEES.NS"]
    for ticker in candidates:
        try:
            df = yf.Ticker(ticker).history(
                period=f"{LOOKBACK_DAYS}d",
                auto_adjust=True
            )
            if df is not None and not df.empty and len(df) > 50:
                print(f"  Benchmark fetched: {ticker}")
                return df["Close"]
        except Exception as e:
            print(f"  Benchmark failed for {ticker}: {e}")
            time.sleep(2)
    print("  WARNING: All benchmark tickers failed. Regime = UNKNOWN.")
    return None

def fetch_all(symbols):
    data      = {}
    failed    = []
    batch_size = 100
    batches   = [symbols[i:i+batch_size] for i in range(0, len(symbols), batch_size)]

    for batch_num, batch in enumerate(batches):
        print(f"  Downloading batch {batch_num+1}/{len(batches)} ({len(batch)} symbols)...")

        success = False
        for attempt in range(3):
            try:
                raw = yf.download(
                    tickers=" ".join(batch),
                    period=f"{LOOKBACK_DAYS}d",
                    interval="1d",
                    auto_adjust=True,
                    group_by="ticker",
                    threads=True,
                    progress=False,
                )
                success = True
                break
            except Exception as e:
                wait = 5 * (attempt + 1)
                print(f"    Attempt {attempt+1} failed: {e} — retrying in {wait}s")
                time.sleep(wait)

        if not success or raw is None or raw.empty:
            print(f"    Batch {batch_num+1} skipped after 3 attempts.")
            failed.extend(batch)
            continue

        # Parse results
        for sym in batch:
            try:
                # Single ticker download has flat columns
                if len(batch) == 1:
                    df = raw.copy()
                else:
                    # Multi-ticker has MultiIndex columns (ticker, OHLCV)
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

            except Exception as e:
                failed.append(sym)

        # Polite pause between batches
        if batch_num < len(batches) - 1:
            time.sleep(3)

    print(f"\n  Done. Successful: {len(data)} | Failed: {len(failed)}")
    if failed:
        pd.Series(failed).to_csv("failed_symbols.csv", index=False, header=["Symbol"])
        print(f"  Failed symbols saved to failed_symbols.csv")

    return data