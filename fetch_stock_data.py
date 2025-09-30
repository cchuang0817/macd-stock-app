import os
import yfinance as yf
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta

DATA_DIR = "data"

def fetch_price(ticker, start, end):
    df = yf.download(ticker, start=start, end=end, progress=False)
    if df.empty:
        return pd.DataFrame()
    df = df.reset_index()
    df = df.rename(columns={"Date": "Date", "Close": "Close"})
    return df[["Date", "Close"]]

def save_to_csv(ticker, df):
    os.makedirs(DATA_DIR, exist_ok=True)
    file_path = Path(DATA_DIR) / f"{ticker}.csv"

    if file_path.exists():
        old = pd.read_csv(file_path, parse_dates=["Date"])
        merged = pd.concat([old, df]).drop_duplicates(subset=["Date"]).sort_values("Date")
        new_count = len(merged) - len(old)
    else:
        merged = df
        new_count = len(df)

    merged.to_csv(file_path, index=False, encoding="utf-8-sig")
    print(f"{ticker} 儲存 {len(merged)} 筆資料 (本次新增 {new_count} 筆)")

def main():
    # 從 company_info.csv 讀股票清單
    company_df = pd.read_csv("company_info.csv")
    tickers = company_df["ticker"].dropna().unique().tolist()

    today = datetime.today()
    six_months_ago = (today - timedelta(days=180)).strftime("%Y-%m-%d")
    today_str = today.strftime("%Y-%m-%d")

    for ticker in tickers:
        file_path = Path(DATA_DIR) / f"{ticker}.csv"

        if file_path.exists():
            # 已有資料 → 只抓最新日期之後的
            last_date = pd.read_csv(file_path, parse_dates=["Date"])["Date"].max()
            start_date = (last_date + timedelta(days=1)).strftime("%Y-%m-%d")
        else:
            # 第一次 → 抓 6 個月
            start_date = six_months_ago

        df = fetch_price(ticker, start=start_date, end=today_str)
        if not df.empty:
            save_to_csv(ticker, df)
        else:
            print(f"{ticker} 沒有抓到資料")

if __name__ == "__main__":
    main()
