import numpy as np
from config import *

def _ema(series, length):
    return series.ewm(span=length, adjust=False).mean()

def detect_setup(row, df, comp_score):
    flags = []
    tier  = "C"

    # Breakout setup
    recent_high = df["High"].iloc[-BREAKOUT_LOOKBACK:-1].max()
    bb_squeeze  = row.get("bb_width", 99) < 0.04
    vol_surge   = row.get("vol_ratio", 0) >= VOL_SURGE_RATIO
    close       = row["Close"]

    if close > recent_high and vol_surge and row.get("adx", 0) >= 20:
        flags.append("BREAKOUT")

    if bb_squeeze and row.get("rsi", 50) > 50:
        flags.append("BB_SQUEEZE_SETUP")

    # Momentum continuation
    ema_aligned = close > row.get("ema21", 0) > row.get("ema50", 0)
    macd_bull   = row.get("macd_hist", 0) > 0
    rsi_mid     = 50 < row.get("rsi", 50) < 75

    if ema_aligned and macd_bull and rsi_mid:
        flags.append("MOMENTUM_CONT")

    # Tier assignment
    if comp_score >= SCORE_TIER_A and flags:
        tier = "A"
    elif comp_score >= SCORE_TIER_B:
        tier = "B"

    return {
        "flags":     "|".join(flags) if flags else "NONE",
        "tier":      tier,
        "watchlist": tier in ("A", "B"),
    }

def market_regime(benchmark_close):
    """Bull / Sideways / Bear — returns UNKNOWN if benchmark data unavailable."""
    if benchmark_close is None or len(benchmark_close) < 200:
        print("  Benchmark data insufficient — defaulting regime to UNKNOWN.")
        return "UNKNOWN"

    try:
        ema50  = _ema(benchmark_close, 50).iloc[-1]
        ema200 = _ema(benchmark_close, 200).iloc[-1]
        price  = benchmark_close.iloc[-1]

        if price > ema50 > ema200:
            return "BULL"
        elif price < ema50 < ema200:
            return "BEAR"
        return "SIDEWAYS"
    except Exception as e:
        print(f"  Regime calculation failed: {e} — defaulting to UNKNOWN.")
        return "UNKNOWN"