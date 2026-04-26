import pandas as pd
import numpy as np
from datetime import datetime
from score_history import append_to_history, export_momentum_of_score_to_sheet
from config import *
from data_fetch import load_universe, fetch_all, fetch_benchmark
from indicators import compute_indicators, get_latest
from scoring import composite_score
from setup_detector import detect_setup, market_regime
from sheets_export import run_export

def run_scanner():
    print(f"\n{'='*50}")
    print(f"NSE SCANNER — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*50}\n")

    # 1. Load universe
    symbols = load_universe()
    print(f"Universe: {len(symbols)} stocks\n")

    # 2. Fetch benchmark
    print("Fetching benchmark (Nifty 500)...")
    bench = fetch_benchmark()
    regime = market_regime(bench) if bench is not None else "UNKNOWN"
    print(f"Market Regime: {regime}\n")

    # 3. Fetch all stocks
    print("Fetching OHLCV data...")
    data = fetch_all(symbols)
    print(f"  Successfully fetched: {len(data)} stocks\n")

    # 4. Compute indicators + scores
    print("Computing indicators and scores...")
    results = []
    for sym, df in data.items():
        try:
            df_ind = compute_indicators(df, bench)
            row    = get_latest(df_ind)
            score, sub_scores = composite_score(row, df_ind)
            setup  = detect_setup(row, df_ind, score)

            results.append({
                "Symbol":       sym,
                "Close":        round(row["Close"], 2),
                "Score":        score,
                "Tier":         setup["tier"],
                "Flags":        setup["flags"],
                "PA_Score":     sub_scores["price_action"],
                "TS_Score":     sub_scores["trend_strength"],
                "RS_Score":     sub_scores["rel_strength"],
                "MOM_Score":    sub_scores["momentum"],
                "VOL_Score":    sub_scores["volume"],
                "RSI":          round(row.get("rsi", 0), 1),
                "ADX":          round(row.get("adx", 0), 1),
                "EMA21":        round(row.get("ema21", 0), 2),
                "EMA50":        round(row.get("ema50", 0), 2),
                "RS_vs_Nifty":  round(row.get("rs_score", 0), 2),
                "Vol_Ratio":    round(row.get("vol_ratio", 0), 2),
                "ATR_Pct":      round(row.get("atr_pct", 0), 2),
                "Pct_52w_High": round(row.get("pct_from_52w_high", 0), 2),
            })
        except Exception as e:
            print(f"  Error on {sym}: {e}")

    # 5. Empty results guard — OUTSIDE the for loop, aligned with it
    if not results:
        print("\n  ERROR: No stocks scored. Check data fetch. Exiting.")
        return

    results_df = pd.DataFrame(results).sort_values("Score", ascending=False)

    # 6. Print summary
    tier_a = results_df[results_df["Tier"] == "A"]
    print(f"\nSCAN COMPLETE — {len(results_df)} stocks scored")
    print(f"Tier-A setups: {len(tier_a)}")
    print(f"Top 5:\n{results_df[['Symbol','Score','Tier','Flags']].head()}\n")

    # 7. Save local CSV backup
    ts_str = datetime.now().strftime("%Y%m%d_%H%M")
    results_df.to_csv(f"scan_{ts_str}.csv", index=False)

    # 8. Export to Google Sheets
    print("Exporting to Google Sheets...")
    sh = run_export(results_df, regime)

    # 9. Append to Score History tab in Sheets
    print("Updating score history...")
    append_to_history(results_df, sh=sh)

    # 10. Update Rising Score tab
    export_momentum_of_score_to_sheet(sh, lookback_days=5, min_sessions=3)

    print("\nDone.")

if __name__ == "__main__":
    run_scanner()