import os
import requests
import pandas as pd
from datetime import datetime
from pathlib import Path

DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)


def fetch_twse(stock_id, year, month):
    """抓取上市股票（月資料，JSON）"""
    url = f"https://www.twse.com.tw/exchangeReport/STOCK_DAY?response=json&date={year}{month:02d}01&stockNo={stock_id}"
    resp = requests.get(url)
    data = resp.json()

    if data.get("stat") != "OK":
        return pd.DataFrame()

    df = pd.DataFrame(data["data"], columns=data["fields"])
    df["Date"] = pd.to_datetime(df["日期"].str.replace("/", "-"), errors="coerce")
    df["Close"] = pd.to_numeric(df["收盤價"].str.replace(",", ""), errors="coerce")
    return df[["Date", "Close"]]


def fetch_tpex(stock_id, year, month):
    """抓取上櫃股票（月資料，CSV）"""
    roc_year = year - 1911  # 民國年
    url = f"https://www.tpex.org.tw/web/stock/aftertrading/daily_trading_info/st43_download.php?d={roc_year}/{month:02d}&stkno={stock_id}&s=0,asc,0"
    resp = requests.get(url)
    resp.encoding = "utf-8"

    if resp.status_code != 200 or len(resp.text) < 20:
        return pd.DataFrame()

    try:
        df = pd.read_csv(pd.compat.StringIO(resp.text))
    except Exception:
        from io import StringIO
        df = pd.read_csv(StringIO(resp.text))

    if "日期" not in df.columns or "收盤" not in df.columns:
        return pd.DataFrame()

    df["Date"] = pd.to_datetime(df["日期"].astype(str).str.replace("/", "-"), errors="coerce")
    df["Close"] = pd.to_numeric(df["收盤"], errors="coerce")
    return df[["Date", "Close"]]


def save_to_csv(ticker, df):
    """存檔到 data/{ticker}.csv，並避免重複"""
    file_path = Path(DATA_DIR) / f"{ticker}.csv"
    if file_path.exists():
        old = pd.read_csv(file_path, parse_dates=["Date"])
        df = pd.concat([old, df], ignore_index=True)
        df = df.drop_duplicates(subset=["Date"]).sort_values("Date")
    df.to_csv(file_path, index=False, encoding="utf-8-sig")
    print(f"{ticker} 儲存 {len(df)} 筆資料")


def main():
    # 讀取 company_info.csv
    companies = pd.read_csv("company_info.csv")
    today = datetime.today()
    year, month = today.year, today.month

    for _, row in companies.iterrows():
        ticker = row["Ticker"]
        stock_id, market = ticker.split(".")

        if market == "TW":
            df = fetch_twse(stock_id, year, month)
        elif market == "TWO":
            df = fetch_tpex(stock_id, year, month)
        else:
            print(f"{ticker} 市場類型未知，跳過")
            continue

        if df.empty:
            print(f"{ticker} 沒有抓到資料")
        else:
            save_to_csv(ticker, df)


if __name__ == "__main__":
    main()
