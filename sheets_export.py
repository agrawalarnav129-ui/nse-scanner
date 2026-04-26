import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import numpy as np
from datetime import datetime
from config import WATCHLIST_SIZE
import os
import json

SHEET_ID = os.environ.get("https://docs.google.com/spreadsheets/d/18jBAdzzgqBgrEn4JxXLg8Vux3FnB-VSMEdDzg6_SzvI/edit?gid=456463925#gid=456463925", "18jBAdzzgqBgrEn4JxXLg8Vux3FnB-VSMEdDzg6_SzvI")

SCOPES = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

def get_sheet():
    creds_json = os.environ.get("GOOGLE_CREDS")

    if creds_json:
        # Running on GitHub Actions — credentials from secret
        creds_dict = json.loads(creds_json)
        creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    else:
        # Running locally — use credentials.json file
        creds = Credentials.from_service_account_file("credentials.json", scopes=SCOPES)

    client = gspread.authorize(creds)
    return client.open_by_key(SHEET_ID)

def sanitize(df):
    df = df.copy()
    df.replace([np.inf, -np.inf], np.nan, inplace=True)
    df = df.where(pd.notnull(df), "")
    return df

def to_rows(df, cols):
    subset = sanitize(df[cols])
    return [subset.columns.tolist()] + subset.values.tolist()

def export_master_scan(sh, results_df):
    ws = sh.worksheet("Master Scan")
    ws.clear()
    cols = ["Symbol","Close","Score","Tier","Flags",
            "PA_Score","TS_Score","RS_Score","MOM_Score","VOL_Score",
            "RSI","ADX","EMA21","EMA50","RS_vs_Nifty",
            "Vol_Ratio","ATR_Pct","Pct_52w_High","Timestamp"]
    ws.update(to_rows(results_df, cols))
    ws.freeze(rows=1)

def export_watchlist(sh, results_df):
    ws = sh.worksheet("Watchlist Top30")
    ws.clear()
    top30 = results_df.sort_values("Score", ascending=False).head(WATCHLIST_SIZE)
    cols  = ["Symbol","Close","Score","Tier","Flags","RSI","ADX","Vol_Ratio","RS_vs_Nifty"]
    ws.update(to_rows(top30, cols))
    ws.freeze(rows=1)

def export_alerts(sh, results_df):
    ws = sh.worksheet("Breakout Alerts")
    ws.clear()
    alerts = results_df[results_df["Tier"] == "A"].sort_values("Score", ascending=False)
    cols   = ["Symbol","Close","Score","Flags","RSI","ADX","Vol_Ratio","ATR_Pct","Timestamp"]
    ws.update(to_rows(alerts, cols))
    ws.freeze(rows=1)

def export_regime(sh, regime, timestamp):
    ws = sh.worksheet("Regime Dashboard")
    ws.clear()
    ws.update("A1", [
        ["Metric",        "Value"],
        ["Market Regime", regime],
        ["Last Updated",  timestamp],
        ["Tier-A Stocks", "=COUNTIF('Breakout Alerts'!C:C,\">74\")"],
        ["Tier-B Stocks", "=COUNTIF('Master Scan'!D:D,\"B\")"],
    ])

def run_export(results_df, regime):
    sh  = get_sheet()
    ts  = datetime.now().strftime("%Y-%m-%d %H:%M")
    results_df = results_df.copy()
    results_df["Timestamp"] = ts
    export_master_scan(sh, results_df)
    export_watchlist(sh, results_df)
    export_alerts(sh, results_df)
    export_regime(sh, regime, ts)
    print(f"  Google Sheets updated at {ts}")
    return sh