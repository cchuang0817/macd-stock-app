import yfinance as yf
import pandas as pd
import os, time, random
from datetime import datetime

print("=== Step 1: 測試 yfinance 是否可抓資料 ===")
import yfinance as yf

try:
    df_test = yf.Ticker("2330.TW").history(period="1mo")
    print(f"2330.TW 測試資料筆數：{len(df_test)}")
    if not df_test.empty:
        print(df_test.tail(3))
    else:
        print("⚠️ yfinance 成功執行，但沒有回傳資料（DataFrame 為空）")
except Exception as e:
    print(f"❌ 測試失敗，錯誤訊息：{e}")

# === 基本設定 ===
CACHE_DIR = "data/cache"
OUTPUT_DIR = "data"
LOG_DIR = "data/logs"
os.makedirs(CACHE_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

# === 讀取股票清單與公司資訊 ===
tickers = [
    t.strip() for t in open("tickers_tw.txt", encoding="utf-8").read().splitlines()
    if t.strip() and not t.startswith("#")
]

print(f"目前執行位置: {os.getcwd()}")
print(f"是否存在 tickers_tw.txt: {os.path.exists('tickers_tw.txt')}")
print(f"是否存在 company_info.csv: {os.path.exists('company_info.csv')}")
print(f"讀入的股票數量: {len(tickers)}")

company_info = pd.read_csv("company_info.csv")

# === MACD 計算 ===
def calc_macd(df, fast=12, slow=26, signal=9):
    df["EMA_fast"] = df["Close"].ewm(span=fast, adjust=False).mean()
    df["EMA_slow"] = df["Close"].ewm(span=slow, adjust=False).mean()
    df["MACD"] = df["EMA_fast"] - df["EMA_slow"]
    df["Signal"] = df["MACD"].ewm(span=signal, adjust=False).mean()
    df["Hist"] = df["MACD"] - df["Signal"]
    return df.dropna()

# === MACD 條件檢查 ===
def check_macd_condition(df):
    if not ((df["MACD"] > 0).any() and (df["MACD"] < 0).any()):
        return False
    last = df.iloc[-1]
    if last["Hist"] >= 0:
        return False
    neg_hist = df[df["Hist"] < 0]
    recent_neg = neg_hist.tail(5)
    if (recent_neg["MACD"] < 0).any() or (recent_neg["Signal"] < 0).any():
        return False
    if len(df) < 3:
        return False
    h1, h2, h3 = df["Hist"].iloc[-3:]
    if not (h1 < h2 < h3 and h3 < -1):
        return False
    return True

# === 抓取股價資料（含快取） ===
def fetch_stock_data(tk):
    cache_path = f"{CACHE_DIR}/{tk}.csv"
    df = None
    try:
        if os.path.exists(cache_path):
            df_cache = pd.read_csv(cache_path, parse_dates=["Date"], index_col="Date")
            last_date = df_cache.index[-1].strftime("%Y-%m-%d")
            df_new = yf.Ticker(tk).history(start=last_date)
            if not df_new.empty:
                df = pd.concat([df_cache, df_new[~df_new.index.isin(df_cache.index)]])
            else:
                df = df_cache
        else:
            df = yf.Ticker(tk).history(period="6mo", interval="1d")
            
        if df is not None and not df.empty:
            df.to_csv(cache_path)
        return df

    except Exception as e:   # ✅ 補上這一段
        print(f"⚠️ {tk} 抓取失敗: {e}")
        return None
