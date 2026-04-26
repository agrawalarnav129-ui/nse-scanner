import pandas as pd
import numpy as np
import os
from datetime import datetime

HISTORY_FILE = "score_history.csv"

HISTORY_COLS = [
    "Date", "Symbol", "Close", "Score", "Tier", "Flags",
    "PA_Score", "TS_Score", "RS_Score", "MOM_Score", "VOL_Score",
    "RSI", "ADX", "Vol_Ratio", "RS_vs_Nifty", "ATR_Pct", "Pct_52w_High"
]

def append_to_history(results_df, sh=None):
    today = datetime.now().strftime("%Y-%m-%d")

    df = results_df.copy()
    df["Date"] = today
    available = [c for c in HISTORY_COLS if c in df.columns]
    df = df[available]
    df.replace([np.inf, -np.inf], np.nan, inplace=True)
    df = df.where(pd.notnull(df), "")

    if sh is not None:
        # Save to Google Sheets Score History tab
        try:
            ws = sh.worksheet("Score History")
        except Exception:
            ws = sh.add_worksheet(title="Score History", rows=50000, cols=25)
            ws.append_row(HISTORY_COLS)
            print("  Created 'Score History' tab in Google Sheets.")

        # Check if today already exists — avoid duplicate rows on re-run
        existing_dates = ws.col_values(1)
        if today in existing_dates:
            print(f"  Score History: {today} already logged. Skipping.")
            return

        rows = df[available].values.tolist()
        ws.append_rows(rows, value_input_option="RAW")
        print(f"  Score History tab updated — {len(rows)} rows added for {today}")

    else:
        # Local fallback — save to CSV
        if os.path.exists(HISTORY_FILE):
            existing = pd.read_csv(HISTORY_FILE)
            existing = existing[existing["Date"] != today]
            combined = pd.concat([existing, df], ignore_index=True)
        else:
            combined = df
        combined.to_csv(HISTORY_FILE, index=False)
        print(f"  Score history saved locally — {len(combined)} total rows")


def get_momentum_of_score(sh, lookback_days=5, min_sessions=3, min_score=50):
    """Read history from Sheets and return rising-score stocks."""
    try:
        ws  = sh.worksheet("Score History")
        data = ws.get_all_records()
        if not data:
            print("  Score History tab is empty.")
            return pd.DataFrame()
    except Exception:
        print("  Score History tab not found.")
        return pd.DataFrame()

    df = pd.DataFrame(data)
    df["Date"]  = pd.to_datetime(df["Date"])
    df["Score"] = pd.to_numeric(df["Score"], errors="coerce")

    cutoff = df["Date"].max() - pd.Timedelta(days=lookback_days)
    df = df[df["Date"] >= cutoff]

    results = []
    for symbol, grp in df.groupby("Symbol"):
        grp = grp.sort_values("Date")
        if len(grp) < min_sessions:
            continue
        latest_score = grp["Score"].iloc[-1]
        if latest_score < min_score:
            continue

        scores       = grp["Score"].values
        dates        = np.arange(len(scores))
        slope        = np.polyfit(dates, scores, 1)[0]
        delta        = float(scores[-1]) - float(scores[0])
        daily_deltas = np.diff(scores)
        pos_days     = int((daily_deltas > 0).sum())
        consistency  = round(pos_days / len(daily_deltas) * 100, 1)

        results.append({
            "Symbol":          symbol,
            "Sessions":        len(grp),
            "Latest_Score":    round(latest_score, 1),
            "Score_Delta":     round(delta, 1),
            "Slope_Per_Day":   round(slope, 2),
            "Consistency_Pct": consistency,
            "Latest_Tier":     grp["Tier"].iloc[-1],
            "Latest_Flags":    grp["Flags"].iloc[-1],
            "Latest_Close":    grp["Close"].iloc[-1],
            "Latest_RSI":      grp["RSI"].iloc[-1],
            "Score_Trail":     " → ".join(str(round(float(s), 1)) for s in scores),
        })

    if not results:
        return pd.DataFrame()

    out = pd.DataFrame(results)
    out = out[out["Slope_Per_Day"] > 0]
    out = out.sort_values("Slope_Per_Day", ascending=False)
    return out


def export_momentum_of_score_to_sheet(sh, lookback_days=5, min_sessions=3):
    import gspread
    mos = get_momentum_of_score(sh, lookback_days=lookback_days, min_sessions=min_sessions)

    try:
        ws = sh.worksheet("Rising Score")
    except gspread.exceptions.WorksheetNotFound:
        ws = sh.add_worksheet(title="Rising Score", rows=200, cols=20)

    ws.clear()

    if mos.empty:
        ws.update("A1", [["No data yet — needs 3+ days of history"]])
        print("  Rising Score: not enough history yet.")
        return

    mos.replace([np.inf, -np.inf], np.nan, inplace=True)
    mos = mos.where(pd.notnull(mos), "")
    ws.update([mos.columns.tolist()] + mos.values.tolist())
    ws.freeze(rows=1)
    print(f"  Rising Score tab updated — {len(mos)} candidates")