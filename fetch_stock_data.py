import yfinance as yf
import pandas as pd
import os, time, random
from datetime import datetime

# === 基本設定 ===
CACHE_DIR = "data/cache"
OUTPUT_DIR = "data"
os.makedirs(CACHE_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

# === 讀取股票清單與公司資訊 ===
tickers = [
    t.strip() for t in open("tickers_tw.txt", encoding="utf-8").read().splitlines()
    if t.strip() and not t.startswith("#")
]
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
    # Step1: 六個月內曾穿越0軸
    if not ((df["MACD"] > 0).any() and (df["MACD"] < 0).any()):
        return False
    # Step2: 當前為綠柱
    last = df.iloc[-1]
    if last["Hist"] >= 0:
        return False
    # Step3: 綠柱期間 MACD & Signal > 0
    neg_hist = df[df["Hist"] < 0]
    recent_neg = neg_hist.tail(5)
    if (recent_neg["MACD"] < 0).any() or (recent_neg["Signal"] < 0).any():
        return False
    # Step4: 綠柱連續三天收斂且 Hist < -1
    if len(df) < 3:
        return False
    h1, h2, h3 = df["Hist"].iloc[-3:]
    if not (h1 < h2 < h3 and h3 < -1):
        return False
    return True

# === 安全抓資料（含快取） ===
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
    except Exception as e:
        print(f"⚠️ {tk} 抓取失敗: {e}")
        return None

# === 主流程 ===
def main():
    results = []
    total = len(tickers)
    print(f"開始抓取 {total} 檔股票...")

    for i, tk in enumerate(tickers, start=1):
        print(f"[{i}/{total}] {tk}")
        df = fetch_stock_data(tk)

        # 若資料有效才分析
        if df is not None and not df.empty:
            df = calc_macd(df)
            if check_macd_condition(df):
                last = df.iloc[-1]
                info = company_info[company_info["Ticker"] == tk]
                name = info.iloc[0]["Name"] if not info.empty else "N/A"
                industry = info.iloc[0]["Industry"] if not info.empty else "N/A"

                results.append({
                    "Ticker": tk,
                    "Name": name,
                    "Industry": industry,
                    "LastDate": df.index[-1].strftime("%Y-%m-%d"),
                    "MACD": round(last["MACD"], 2),
                    "Signal": round(last["Signal"], 2),
                    "Hist": round(last["Hist"], 2)
                })
                print(f"✅ {tk} 符合條件")
        # 流量控制 (0.6~1.2秒)
        time.sleep(random.uniform(0.6, 1.2))

    # === 結果輸出 ===
    date_str = datetime.now().strftime("%Y-%m-%d")
    file_path = f"{OUTPUT_DIR}/macd_filtered_{date_str}.csv"

    if len(results) == 0:
        print("\n⚠️ 沒有任何股票符合 MACD 條件，輸出空白表格。")
        df_out = pd.DataFrame([{
            "Ticker": "N/A",
            "Name": "N/A",
            "Industry": "N/A",
            "LastDate": "N/A",
            "MACD": "N/A",
            "Signal": "N/A",
            "Hist": "N/A"
        }])
    else:
        df_out = pd.DataFrame(results)

    df_out.to_csv(file_path, index=False, encoding="utf-8-sig")
    print(f"\n=== 完成 ===\n共找到 {len(results)} 檔股票，結果已輸出至 {file_path}")

if __name__ == "__main__":
    main()
