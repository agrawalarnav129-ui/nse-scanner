import numpy as np
from config import *

def score_price_action(row, df):
    score = 0
    close = row["Close"]

    # EMA stack (30 pts)
    if close > row["ema21"] > row["ema50"] > row["ema200"]:
        score += 30
    elif close > row["ema21"] > row["ema50"]:
        score += 20
    elif close > row["ema21"]:
        score += 10

    # Proximity to 52w high (20 pts)
    pct_off = abs(row.get("pct_from_52w_high", 100))
    if pct_off <= 2:
        score += 20
    elif pct_off <= 5:
        score += 15
    elif pct_off <= 10:
        score += 8

    # BB position (15 pts)
    bb_range = row["bb_upper"] - row["bb_lower"] + 1e-9
    bb_pos   = (close - row["bb_lower"]) / bb_range
    score   += min(15, int(bb_pos * 15))

    # Range breakout (20 pts)
    recent_high = df["High"].iloc[-BREAKOUT_LOOKBACK:-1].max()
    if close > recent_high and row.get("atr_pct", 0) >= ATR_BREAKOUT_MIN:
        score += 20
    elif close > recent_high * 0.98:
        score += 10

    # Last candle bullish body (15 pts)
    last       = df.iloc[-1]
    crange     = last["High"] - last["Low"]
    if crange > 0:
        body_ratio = (last["Close"] - last["Open"]) / crange
        score     += max(0, int(body_ratio * 15))

    return min(100, score)

def score_trend_strength(row):
    score = 0

    # ADX level (40 pts)
    adx_val = row.get("adx", 0) or 0
    if adx_val >= 40:
        score += 40
    elif adx_val >= 30:
        score += 30
    elif adx_val >= 25:
        score += 20
    elif adx_val >= 20:
        score += 10

    # DI alignment (20 pts)
    if row.get("dmp", 0) > row.get("dmn", 0):
        score += 20

    # EMA21 slope — now live, not a placeholder (40 pts)
    slope = row.get("ema21_slope", 0) or 0
    close = row.get("Close", 1) or 1
    slope_pct = (slope / close) * 100   # normalise by price

    if slope_pct >= 0.5:
        score += 40
    elif slope_pct >= 0.2:
        score += 28
    elif slope_pct >= 0:
        score += 15
    # negative slope = 0 pts

    return min(100, score)

def score_relative_strength(row):
    rs = row.get("rs_score", 0) or 0
    normalized = (rs + 15) / 30 * 100
    return max(0, min(100, normalized))

def score_momentum(row):
    score = 0

    rsi_val = row.get("rsi", 50) or 50
    if 55 <= rsi_val <= 70:
        score += 50
    elif 50 <= rsi_val < 55:
        score += 35
    elif 70 < rsi_val <= RSI_OVERBOUGHT:
        score += 25
    elif rsi_val < RSI_OVERSOLD:
        score += 5

    hist = row.get("macd_hist", 0) or 0
    if hist > 0:
        score += 30
        if row.get("macd", 0) > row.get("macd_signal", 0):
            score += 20

    return min(100, score)

def score_volume(row):
    vr = row.get("vol_ratio", 1) or 1
    if vr >= 3.0:   return 100
    elif vr >= 2.0: return 80
    elif vr >= VOL_SURGE_RATIO: return 60
    elif vr >= 1.2: return 35
    elif vr >= 0.8: return 15
    return 0

def composite_score(row, df):
    scores = {
        "price_action":   score_price_action(row, df),
        "trend_strength": score_trend_strength(row),
        "rel_strength":   score_relative_strength(row),
        "momentum":       score_momentum(row),
        "volume":         score_volume(row),
    }
    total = sum(scores[k] * WEIGHTS[k] for k in scores)
    return round(total, 1), scores