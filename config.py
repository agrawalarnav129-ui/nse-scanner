# ─── UNIVERSE ───────────────────────────────────────────────
UNIVERSE_FILE = "nifty500.csv"          # column: "Symbol" with .NS suffix
BENCHMARK = "^NSEI"   # Nifty 50 — most reliable via yfinance
SECTOR_ETFS = {
    "IT":     "0P0001EK9L.BO",
    "Bank":   "BANKBEES.NS",
    "Auto":   "0P0001EK9K.BO",
    "Pharma": "PHARMABEES.NS",
    "FMCG":   "FMCGIETF.NS",
}

# ─── SCORING WEIGHTS ────────────────────────────────────────
WEIGHTS = {
    "price_action":   0.30,
    "trend_strength": 0.25,
    "rel_strength":   0.20,
    "momentum":       0.15,
    "volume":         0.10,
}

# ─── INDICATOR PARAMETERS ───────────────────────────────────
EMA_SHORT   = 21
EMA_MID     = 50
EMA_LONG    = 200
RSI_PERIOD  = 14
ADX_PERIOD  = 14
ATR_PERIOD  = 14
BB_PERIOD   = 20
VOL_MA      = 20
RS_LOOKBACK = 63   # ~3 months of trading days

# ─── THRESHOLDS ──────────────────────────────────────────────
RSI_OVERSOLD     = 40
RSI_OVERBOUGHT   = 75
ADX_TREND_MIN    = 25
VOL_SURGE_RATIO  = 1.5        # volume > 1.5x 20-day avg
ATR_BREAKOUT_MIN = 0.5        # min ATR % for valid breakout
BREAKOUT_LOOKBACK = 20        # periods for range high detection
SCORE_TIER_A     = 75         # top picks
SCORE_TIER_B     = 55
WATCHLIST_SIZE   = 30

# ─── DATA ───────────────────────────────────────────────────
LOOKBACK_DAYS = 300           # daily candles to fetch