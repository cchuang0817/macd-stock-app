import os
import ssl
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path

# 保險：避免 SSL 憑證問題
try:
    ssl._create_default_https_context = ssl._create_unverified_context
except Exception:
    pass

# 股票清單（從 company_info.csv 讀取）
def load_tickers(file_path="company_info.csv"):
    df = pd.read_csv(file_path, encoding="utf-8-sig")
    return df["Ticker"].dropna().tolist()

# 抓取單一股票
def fetch_stock_data(ticker, data_dir="data"):
    os.makedirs(data_dir, exist_ok=True)
    file_path = Path(data_dir) / f"{ticker}.csv"

    if file_path.exists():
        # 如果已存在 → 從最後日期開始更新
        df_old = pd.read_csv(file_path, parse_dates=["Date"])
        last_date = df_old["Date"].max()
        start_date = (pd.to_datetime(last_date) + timedelta(days=1)).strftime("%Y-%m-%d")
        df_new = yf.download(ticker, start=start_date, interval="1d", progress=False)

        if not df_new.empty:
            df_new.reset_index(inplace=True)
            df_all = pd.concat([df_old, df_new], ignore_index=True)
            df_all.drop_duplicates(subset=["Date"], inplace=True)
            df_all.to_csv(file_path, index=False)
            print(f"✅ 更新 {ticker}: {len(df_new)} 筆 (總共 {len(df_all)})")
        else:
            print(f"ℹ️ {ticker}: 沒有新資料")
    else:
        # 初次下載 → 抓 6 個月
        df = yf.download(ticker, period="6mo", interval="1d", progress=False)
        if not df.empty:
            df.reset_index(inplace=True)
            df.to_csv(file_path, index=False)
            print(f"📥 初次下載 {ticker}: {len(df)} 筆")
        else:
            print(f"⚠️ {ticker}: 無法取得資料")

def main():
    tickers = load_tickers("company_info.csv")
    print(f"共 {len(tickers)} 檔股票，開始下載/更新...")
    for ticker in tickers:
        try:
            fetch_stock_data(ticker)
        except Exception as e:
            print(f"❌ {ticker} 失敗: {e}")

if __name__ == "__main__":
    main()
