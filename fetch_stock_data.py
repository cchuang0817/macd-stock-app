import os
import requests
import pandas as pd
from datetime import datetime
from pathlib import Path

DATA_DIR = "data"
TICKER = "1101.TW"
STOCK_NO = "1101"

# 建立資料夾
os.makedirs(DATA_DIR, exist_ok=True)

def fetch_twse(stock_no: str, date: str) -> pd.DataFrame:
    """抓取 TWSE 單月股價 (日收盤價)"""
    url = f"https://www.twse.com.tw/exchangeReport/STOCK_DAY?response=json&date={date}&stockNo={stock_no}"
    resp = requests.get(url)
    resp.raise_for_status()
    data = resp.json()

    if data.get("stat") != "OK":
        return pd.DataFrame(columns=["Date", "Close"])

    rows = data["data"]
    df = pd.DataFrame(rows, columns=data["fields"])
    df["Date"] = pd.to_datetime(df["日期"].str.replace("/", "-"), errors="coerce")
    df["Close"] = pd.to_numeric(df["收盤價"].str.replace(",", ""), errors="coerce")
    return df[["Date", "Close"]].dropna()

def initialize_stock(stock_no: str, ticker: str):
    """初始化：抓取最近 6 個月資料"""
    today = datetime.today()
    year, month = today.year, today.month
    months = []
    for i in range(6):
        m = month - i
        y = year
        if m <= 0:
            m += 12
            y -= 1
        months.append(f"{y}{m:02d}01")

    all_data = []
    for m in months[::-1]:  # 由舊到新
        df = fetch_twse(stock_no, m)
        if not df.empty:
            all_data.append(df)

    if all_data:
        df_all = pd.concat(all_data, ignore_index=True)
        file_path = Path(DATA_DIR) / f"{ticker}.csv"
        df_all.to_csv(file_path, index=False)
        print(f"{ticker} 初始化完成，共 {len(df_all)} 筆")
    else:
        print(f"{ticker} 初始化失敗，無資料")

def update_stock(stock_no: str, ticker: str):
    """每日更新：補上缺的日期"""
    file_path = Path(DATA_DIR) / f"{ticker}.csv"
    if not file_path.exists():
        initialize_stock(stock_no, ticker)
        return

    df_old = pd.read_csv(file_path, parse_dates=["Date"])
    last_date = df_old["Date"].max()
    this_month = last_date.strftime("%Y%m01")

    df_new = fetch_twse(stock_no, this_month)
    if df_new.empty:
        print(f"{ticker} 沒有抓到新資料")
        return

    df_all = pd.concat([df_old, df_new], ignore_index=True)
    df_all.drop_duplicates(subset=["Date"], inplace=True)
    df_all.sort_values("Date", inplace=True)
    df_all.to_csv(file_path, index=False)
    print(f"{ticker} 更新完成，共 {len(df_all)} 筆")

def main():
    update_stock(STOCK_NO, TICKER)

if __name__ == "__main__":
    main()
