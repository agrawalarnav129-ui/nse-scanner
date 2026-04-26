import pandas as pd
import numpy as np
from config import *

# ─── Core calculation functions ─────────────────────────────

def ema(series, length):
    return series.ewm(span=length, adjust=False).mean()

def rsi(close, length=RSI_PERIOD):
    delta = close.diff()
    gain  = delta.clip(lower=0)
    loss  = (-delta).clip(lower=0)
    avg_gain = gain.ewm(com=length - 1, adjust=False).mean()
    avg_loss = loss.ewm(com=length - 1, adjust=False).mean()
    rs = avg_gain / (avg_loss + 1e-10)
    return 100 - (100 / (1 + rs))

def atr(high, low, close, length=ATR_PERIOD):
    tr = pd.concat([
        high - low,
        (high - close.shift()).abs(),
        (low  - close.shift()).abs()
    ], axis=1).max(axis=1)
    return tr.ewm(com=length - 1, adjust=False).mean()

def adx(high, low, close, length=ADX_PERIOD):
    up   = high.diff()
    down = (-low.diff())
    dmp  = pd.Series(np.where((up > down) & (up > 0), up, 0.0), index=close.index)
    dmn  = pd.Series(np.where((down > up) & (down > 0), down, 0.0), index=close.index)

    tr_val = atr(high, low, close, length)

    smooth_dmp = dmp.ewm(com=length - 1, adjust=False).mean()
    smooth_dmn = dmn.ewm(com=length - 1, adjust=False).mean()

    di_pos = 100 * smooth_dmp / (tr_val + 1e-10)
    di_neg = 100 * smooth_dmn / (tr_val + 1e-10)

    dx     = 100 * (di_pos - di_neg).abs() / (di_pos + di_neg + 1e-10)
    adx_   = dx.ewm(com=length - 1, adjust=False).mean()

    return adx_, di_pos, di_neg

def macd(close, fast=12, slow=26, signal=9):
    ema_fast   = ema(close, fast)
    ema_slow   = ema(close, slow)
    macd_line  = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram  = macd_line - signal_line
    return macd_line, signal_line, histogram

def bbands(close, length=BB_PERIOD, std=2.0):
    mid   = close.rolling(length).mean()
    sigma = close.rolling(length).std(ddof=0)
    upper = mid + std * sigma
    lower = mid - std * sigma
    width = (upper - lower) / (mid + 1e-10)
    return upper, mid, lower, width

# ─── Main indicator computation ─────────────────────────────

def compute_indicators(df, benchmark_close):
    out = df.copy()

    # Strip timezone from index — GitHub Actions returns tz-aware NSE data
    # which conflicts with benchmark's tz-naive index during alignment
    if out.index.tzinfo is not None:
        out.index = out.index.tz_localize(None)

    # ... rest of the function unchanged

    # EMAs
    out["ema21"]  = ema(out["Close"], EMA_SHORT)
    out["ema50"]  = ema(out["Close"], EMA_MID)
    out["ema200"] = ema(out["Close"], EMA_LONG)

    # EMA slope (5-bar delta on EMA21 — fixes the static slope weakness)
    out["ema21_slope"] = out["ema21"].diff(5)

    # RSI
    out["rsi"] = rsi(out["Close"], RSI_PERIOD)

    # ATR
    out["atr"]     = atr(out["High"], out["Low"], out["Close"], ATR_PERIOD)
    out["atr_pct"] = (out["atr"] / out["Close"]) * 100

    # ADX
    out["adx"], out["dmp"], out["dmn"] = adx(
        out["High"], out["Low"], out["Close"], ADX_PERIOD
    )

    # MACD
    out["macd"], out["macd_signal"], out["macd_hist"] = macd(out["Close"])

    # Bollinger Bands
    out["bb_upper"], out["bb_mid"], out["bb_lower"], out["bb_width"] = bbands(
        out["Close"], BB_PERIOD
    )

    # Volume
    out["vol_ma20"]  = out["Volume"].rolling(VOL_MA).mean()
    out["vol_ratio"] = out["Volume"] / (out["vol_ma20"] + 1e-10)

    # Relative Strength vs Nifty
    if benchmark_close is not None:
        try:
            # Strip timezone from both indexes so they can be compared
            out.index         = out.index.tz_localize(None) if out.index.tzinfo else out.index
            bench_index       = benchmark_close.index.tz_localize(None) if benchmark_close.index.tzinfo else benchmark_close.index
            bench_tz_stripped = pd.Series(benchmark_close.values, index=bench_index)
            aligned           = bench_tz_stripped.reindex(out.index, method="ffill")
            stock_ret         = out["Close"].pct_change(RS_LOOKBACK)
            bench_ret         = aligned.pct_change(RS_LOOKBACK)
            out["rs_score"]   = (stock_ret - bench_ret) * 100
        except Exception as e:
            print(f"  RS score failed: {e} — setting to 0")
            out["rs_score"]   = 0.0
    else:
        out["rs_score"] = 0.0

    # 52-week metrics
    out["high_52w"]          = out["High"].rolling(252).max()
    out["pct_from_52w_high"] = ((out["Close"] - out["high_52w"]) / out["high_52w"]) * 100

    return out

def get_latest(df):
    return df.iloc[-1].to_dict()