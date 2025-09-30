import os
import requests
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path

def load_tickers(file_path="company_info.csv"):
    df = pd.read_csv(file_path, encoding="utf-8-sig")
    return df["Ticker"].dropna().tolist()

def fetch_twse(code, date_str):
    url = f"https://www.twse.com.tw/exchangeReport/STOCK_DAY?response=json&date={date_str}&stockNo={code}"
    resp = requests.get(url)
    data = resp.json()
    if "data" not in data:
        return pd.DataFrame()

    df = pd.DataFrame(data["data"], columns=data["fields"])
    df["Date"] = pd.to_datetime(df["日期"], format="%Y/%m/%d", errors="coerce")
    df["Close"] = pd.to_numeric(df["收盤價"].str.replace(",", ""), errors="coerce")
    return df[["Date", "Close"]].dropna()

def fetch_stock_data(ticker, data_dir="data"):
    os.makedirs(data_dir, exist_ok=True)
    file_path = Path(data_dir) / f"{ticker}.csv"
    code = ticker.split(".")[0]

    today = datetime.today()
    start_date = today.replace(day=1) - timedelta(days=180)  # 6 個月前

    all_data = []
    d = start_date
    while d <= today:
        first_day = d.replace(day=1)
        date_str = first_day.strftime("%Y%m%d")
        df = fetch_twse(code, date_str)
        if not df.empty:
            all_data.append(df)
        d += timedelta(days=32)  # 下一個月

    if not all_data:
        print(f"{ticker}: 沒有抓到資料")
        return

    df_all = pd.concat(all_data, ignore_index=True)
    df_all = df_all.drop_duplicates(subset=["Date"])
    df_all = df_all.sort_values("Date")
    df_all.to_csv(file_path, index=False)
    print(f"{ticker} 更新完成，共 {len(df_all)} 筆")

def main():
    tickers = load_tickers("company_info.csv")
    print(f"共 {len(tickers)} 檔股票，開始抓取/更新...")
    for ticker in tickers:
        try:
            fetch_stock_data(ticker)
        except Exception as e:
            print(f"{ticker} 失敗: {e}")

if __name__ == "__main__":
    main()
