import os
import requests
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path

# 建立資料夾（確保 data/ 存在）
DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

# 載入股票代號清單（從 company_info.csv）
def load_tickers(file_path="company_info.csv"):
    df = pd.read_csv(file_path, encoding="utf-8-sig")
    return df["Ticker"].dropna().tolist()

# 從 TWSE 抓單日資料
def fetch_twse(date_str, code):
    url = f"https://www.twse.com.tw/exchangeReport/STOCK_DAY?response=json&date={date_str}&stockNo={code}"
    try:
        resp = requests.get(url, timeout=10)
        data = resp.json()

        if "data" not in data:
            return pd.DataFrame()

        df = pd.DataFrame(data["data"], columns=data["fields"])

        # 清理欄位
        df["Date"] = pd.to_datetime(df["日期"].str.replace("/", "-"), errors="coerce")
        df["Close"] = pd.to_numeric(df["收盤價"].str.replace(",", ""), errors="coerce")

        return df[["Date", "Close"]]
    except Exception as e:
        print(f"Error: {code} 抓取失敗 - {e}")
        return pd.DataFrame()

# 抓取或更新單一股票
def fetch_stock_data(ticker, data_dir=DATA_DIR):
    file_path = data_dir / f"{ticker}.csv"
    code = ticker.split(".")[0]  # 取股票代號（不含 .TW/.TWO）

    today = datetime.today().strftime("%Y%m%d")

    if file_path.exists():
        # 已有 → 嘗試補最新一天
        df_old = pd.read_csv(file_path, parse_dates=["Date"])
        last_date = df_old["Date"].max()
        last_date_str = last_date.strftime("%Y%m%d")

        if last_date_str >= today:
            print(f"{ticker}: 已是最新，無需更新")
            return

        df_new = fetch_twse(today, code)
        if not df_new.empty:
            df_all = pd.concat([df_old, df_new], ignore_index=True)
            df_all.drop_duplicates(subset=["Date"], inplace=True)
            df_all.to_csv(file_path, index=False)
            print(f"{ticker}: 更新 1 筆")
        else:
            print(f"{ticker}: 無法取得新資料")
    else:
        # 第一次 → 抓最近 6 個月
        start_date = datetime.today() - timedelta(days=180)
        df_list = []

        # 每月抓一次
        for i in range(6):
            dt = (start_date + timedelta(days=i * 30)).strftime("%Y%m%d")
            df_part = fetch_twse(dt, code)
            if not df_part.empty:
                df_list.append(df_part)

        if df_list:
            df = pd.concat(df_list, ignore_index=True)
            df.drop_duplicates(subset=["Date"], inplace=True)
            df.to_csv(file_path, index=False)
            print(f"{ticker}: 初次下載 {len(df)} 筆")
        else:
            print(f"{ticker}: 初次下載失敗")

# 主程式
def main():
    tickers = load_tickers("company_info.csv")
    print(f"共 {len(tickers)} 檔股票，開始抓取/更新...")

    for ticker in tickers:
        fetch_stock_data(ticker)

if __name__ == "__main__":
    main()
