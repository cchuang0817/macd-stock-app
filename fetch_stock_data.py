import os
import time
import random
from datetime import datetime
import pandas as pd
import numpy as np
import yfinance as yf

# === 基本路徑設定 ===
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CACHE_DIR = os.path.join(BASE_DIR, "data", "cache")
OUTPUT_DIR = os.path.join(BASE_DIR, "data")
LOG_DIR = os.path.join(BASE_DIR, "data", "logs")

os.makedirs(CACHE_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

# === 股票清單讀取 ===
tickers_file = os.path.join(BASE_DIR, "tickers_tw.txt")
if not os.path.exists(tickers_file):
    print(f"❌ 找不到股票清單檔案：{tickers_file}")
    exit(1)

with open(tickers_file, "r", encoding="utf-8") as f:
    tickers = [line.strip() for line in f if line.strip() and not line.startswith("#")]

print(f"✅ 已載入股票清單：{len(tickers)} 檔\n")


# === Cache 機制 ===
def load_data_with_cache(ticker, period="6mo", interval="1d", cache_hours=24):
    cache_file = os.path.join(CACHE_DIR, f"{ticker}_{interval}.csv")
    if os.path.exists(cache_file):
        age_hours = (time.time() - os.path.getmtime(cache_file)) / 3600
        if age_hours < cache_hours:
            print(f"  ↳ 使用快取資料: {os.path.basename(cache_file)}")
            return pd.read_csv(cache_file, index_col=0, parse_dates=True)
    df = yf.Ticker(ticker).history(period=period, interval=interval)
    if not df.empty:
        df.to_csv(cache_file)
        print(f"  ↳ 已更新快取: {os.path.basename(cache_file)}")
    return df


# === 技術指標函式 ===
def calc_macd(df, fast=12, slow=26, signal=9):
    df["EMA_fast"] = df["Close"].ewm(span=fast, adjust=False).mean()
    df["EMA_slow"] = df["Close"].ewm(span=slow, adjust=False).mean()
    df["MACD"] = df["EMA_fast"] - df["EMA_slow"]
    df["Signal"] = df["MACD"].ewm(span=signal, adjust=False).mean()
    df["Hist"] = df["MACD"] - df["Signal"]
    return df

def calc_rsi(df, period=14):
    delta = df["Close"].diff()
    gain = (delta.where(delta > 0, 0)).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
    rs = gain / loss
    df["RSI"] = 100 - (100 / (1 + rs))
    return df

def calc_atr(df, period=14):
    df["H-L"] = df["High"] - df["Low"]
    df["H-PC"] = abs(df["High"] - df["Close"].shift(1))
    df["L-PC"] = abs(df["Low"] - df["Close"].shift(1))
    df["TR"] = df[["H-L", "H-PC", "L-PC"]].max(axis=1)
    df["ATR"] = df["TR"].rolling(period).mean()
    return df


# === 回測模組（僅主策略使用） ===
def simple_backtest(df):
    balance, position = 100000, 0
    for i in range(1, len(df)):
        prev, curr = df.iloc[i - 1], df.iloc[i]
        if prev["MACD"] < prev["Signal"] and curr["MACD"] > curr["Signal"] and balance > 0:
            position = balance / curr["Close"]
            balance = 0
        elif prev["MACD"] > prev["Signal"] and curr["MACD"] < curr["Signal"] and position > 0:
            balance = position * curr["Close"]
            position = 0
    final_value = balance + (position * df["Close"].iloc[-1])
    roi = (final_value / 100000 - 1) * 100
    return round(roi, 2)


# === 主策略條件 ===
def check_macd_main(df, df_week, info):
    df = df.sort_index(ascending=True).copy()

    # 1️⃣ 六個月內 MACD 曾穿越 0 軸
    if not ((df["MACD"] > 0).any() and (df["MACD"] < 0).any()):
        return False

    # 2️⃣ 當前為綠柱、MACD未破0
    last = df.iloc[-1]
    if last["Hist"] >= 0 or last["MACD"] < 0 or last["Signal"] < 0:
        return False

    # 3️⃣ 三天綠柱收斂
    if len(df) < 3: return False
    h1, h2, h3 = df["Hist"].iloc[-3:]
    if not (h1 < 0 and h2 < 0 and h3 < 0): return False
    if not (abs(h1) > abs(h2) > abs(h3) and -1 <= h3 < 0): return False

    # 4️⃣ 週線多頭共振
    if df_week["MACD"].iloc[-1] <= 0 or df_week["Signal"].iloc[-1] <= 0:
        return False

    # 5️⃣ 成交量萎縮（3MA < 20MA）
    df["Vol_MA3"] = df["Volume"].rolling(3).mean()
    df["Vol_MA20"] = df["Volume"].rolling(20).mean()
    if df["Vol_MA3"].iloc[-1] > df["Vol_MA20"].iloc[-1]:
        return False

    # 6️⃣ 收盤價在季線之上
    df["MA60"] = df["Close"].rolling(60).mean()
    if df["Close"].iloc[-1] < df["MA60"].iloc[-1]:
        return False

    # 7️⃣ RSI 不過熱
    if df["RSI"].iloc[-1] > 70:
        return False

    # 8️⃣ 牛市背離
    recent = df.tail(40)
    low1 = recent["Close"].iloc[-20:-10].min()
    low2 = recent["Close"].iloc[-10:].min()
    macd_low1 = recent.loc[recent["Close"].iloc[-20:-10].idxmin(), "MACD"]
    macd_low2 = recent.loc[recent["Close"].iloc[-10:].idxmin(), "MACD"]
    if not (low2 < low1 and macd_low2 > macd_low1):
        return False

    # 9️⃣ 基本面：PE 與營收成長
    pe = info.get("trailingPE", 0) or 0
    growth = info.get("revenueGrowth", 0) or 0
    if pe <= 0 or pe > 30: return False
    if growth < 0: return False

    return True


# === 主流程 ===
def main():
    start_time = time.time()
    main_results, backtest_results, failed = [], [], []

    print(f"開始抓取 {len(tickers)} 檔股票...\n")

    for i, tk in enumerate(tickers, start=1):
        print(f"[{i}/{len(tickers)}] {tk}")

        try:
            df = load_data_with_cache(tk, period="6mo", interval="1d")
            df_week = load_data_with_cache(tk, period="1y", interval="1wk")

            if df.empty or df_week.empty:
                failed.append((tk, "No Data"))
                continue

            df = calc_macd(df)
            df = calc_rsi(df)
            df = calc_atr(df)
            df_week = calc_macd(df_week)
            info = yf.Ticker(tk).info or {}

            if df.empty: continue

            # === 主策略判斷 ===
            if check_macd_main(df, df_week, info):
                last = df.iloc[-1]
                pe = info.get("trailingPE", "N/A")
                growth = info.get("revenueGrowth", "N/A")
                atr = round(last["ATR"], 2)
                stop_loss = round(last["Close"] - 2 * atr, 2)
                take_profit = round(last["Close"] + 3 * atr, 2)
                main_results.append({
                    "Ticker": tk,
                    "LastDate": df.index[-1].strftime("%Y-%m-%d"),
                    "MACD": round(last["MACD"], 2),
                    "Signal": round(last["Signal"], 2),
                    "Hist": round(last["Hist"], 2),
                    "ATR": atr,
                    "StopLoss": stop_loss,
                    "TakeProfit": take_profit,
                    "PE": pe,
                    "RevenueGrowth": growth
                })
                print(f"  ✅ {tk} 符合主策略")

                # === 僅主策略股票回測 ===
                df_all = load_data_with_cache(tk, period="2y", interval="1d")
                if not df_all.empty:
                    df_all = calc_macd(df_all)
                    roi = simple_backtest(df_all)
                    backtest_results.append({"Ticker": tk, "ROI(%)": roi})
            else:
                print(f"  ℹ️ {tk} 不符合條件")

        except Exception as e:
            print(f"❌ {tk} 發生錯誤: {e}")
            failed.append((tk, str(e)))

        # 避免被封鎖
        time.sleep(random.uniform(0.8, 1.2))

    # === 結果輸出 ===
    date_str = datetime.now().strftime("%Y-%m-%d")
    out_main = os.path.join(OUTPUT_DIR, f"macd_main_{date_str}.csv")
    out_backtest = os.path.join(OUTPUT_DIR, f"macd_backtest_{date_str}.csv")
    log_file = os.path.join(LOG_DIR, f"log_{date_str}.txt")

    pd.DataFrame(main_results or [{"Ticker": "N/A"}]).to_csv(out_main, index=False, encoding="utf-8-sig")
    pd.DataFrame(backtest_results or [{"Ticker": "N/A"}]).to_csv(out_backtest, index=False, encoding="utf-8-sig")

    # === Log Summary ===
    avg_roi = round(np.mean([b["ROI(%)"] for b in backtest_results]) if backtest_results else 0, 2)
    duration = round((time.time() - start_time) / 60, 2)
    summary = f"""
=== MACD Pro v2 任務完成 {date_str} ===
總股票數: {len(tickers)}
成功處理: {len(tickers) - len(failed)}
符合主策略: {len(main_results)}
回測樣本: {len(backtest_results)}
平均回測報酬率: {avg_roi}%
執行時間: {duration} 分鐘
"""
    print(summary)
    with open(log_file, "w", encoding="utf-8") as f:
        f.write(summary)

if __name__ == "__main__":
    main()
