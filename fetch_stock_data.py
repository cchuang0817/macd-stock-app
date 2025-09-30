import os
import requests
import pandas as pd
from pathlib import Path
from datetime import datetime

# TWSE API
def fetch_twse(stock_id, year, month):
    url = f"https://www.twse.com.tw/exchangeReport/STOCK_DAY?response=json&date={year}{month:02d}01&stockNo={stock_id}"
    resp = requests.get(url)
    data = resp.json()
    if data.get("stat") != "OK":
        return pd.DataFrame()
    df = pd.DataFrame(data["data"], columns=data["fields"])
    df["Date"] = pd.to_datetime(df["日期"].str.replace("/", "-"), errors="coerce")
    df["Close"] = pd.to_numeric(df["收盤價"].str.replace(",", ""), errors="coerce")
    return df[["Date", "Close"]]

# TPEx API
def fetch_tpex(stock_id, year, month):
    url = f"https://www.tpex.org.tw/web/stock/aftertrading/daily_trading_info/st43_result.php?l=zh-tw&d={year}/{month:02d}&stkno={stock_id}"
    resp = requests.get(url)
    data = resp.json()
    if not data.get("aaData"):
        return pd.DataFrame()
    df = pd.DataFrame(data["aaData"])
    df["Date"] = pd.to_datetime(df[0].str.replace("/", "-"), errors="coerce")
    df["Close"] = pd.to_numeric(df[6].str.replace(",", ""), errors="coerce")
    return df[["Date", "Close"]]

# 存檔
def save_to_csv(ticker, df, data_dir="data"):
    os.makedirs(data_dir, exist_ok=True)
    file_path = Path(data_dir) / f"{ticker}.csv"

    if file_path.exists():
        old = pd.read_csv(file_path, parse_dates=["Date"])
        merged = pd.concat([old, df]).drop_duplicates(subset=["Date"]).sort_values("Date")
    else:
        merged = df
    merged.to_csv(file_path, index=False, encoding="utf-8-sig")
    print(f"{ticker} 儲存 {len(merged)} 筆資料 (本次新增 {len(df)} 筆)")

# 主程式
def main():
    # 測試用，後面你可以改成讀 company_info.csv
    tickers = ["1101.TW", "5483.TWO"]

    today = datetime.today()
    year = today.year
    months = [4, 5, 6, 7, 8, 9]  # 先固定測試 4~9 月

    for ticker in tickers:
        stock_id = ticker.split(".")[0]
        all_df = pd.DataFrame()

        for m in months:
            if ticker.endswith(".TW"):
                df = fetch_twse(stock_id, year, m)
            elif ticker.endswith(".TWO"):
                df = fetch_tpex(stock_id, year, m)
            else:
                continue

            if not df.empty:
                all_df = pd.concat([all_df, df])

        if not all_df.empty:
            save_to_csv(ticker, all_df)
        else:
            print(f"{ticker} 沒有抓到資料")

if __name__ == "__main__":
    main()
