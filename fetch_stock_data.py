import os
import requests
import pandas as pd
from datetime import datetime
from pathlib import Path

# TWSE API
def fetch_twse(stock_id, year, month):
    date = f"{year}{month:02d}01"
    url = f"https://www.twse.com.tw/exchangeReport/STOCK_DAY?response=json&date={date}&stockNo={stock_id}"
    resp = requests.get(url)
    resp.encoding = "utf-8"
    try:
        data = resp.json()
    except ValueError:
        print(f"{stock_id}.TW: TWSE API 無回應 → {url}")
        return pd.DataFrame()

    if "data" not in data:
        print(f"{stock_id}.TW: TWSE API 無資料 → {url}")
        return pd.DataFrame()

    df = pd.DataFrame(data["data"], columns=data["fields"])
    df["Date"] = pd.to_datetime(df["日期"].str.replace("/", "-"), errors="coerce")
    df["Close"] = pd.to_numeric(df["收盤價"].str.replace(",", ""), errors="coerce")
    return df[["Date", "Close"]]

# TPEx API
def fetch_tpex(stock_id, year, month):
    roc_year = year - 1911
    roc_date = f"{roc_year}/{month:02d}"
    url = f"https://www.tpex.org.tw/web/stock/aftertrading/daily_trading_info/st43_result.php?l=zh-tw&d={roc_date}&stkno={stock_id}"
    resp = requests.get(url)
    resp.encoding = "utf-8"
    try:
        data = resp.json()
    except ValueError:
        print(f"{stock_id}.TWO: TPEx API 無回應 → {url}")
        return pd.DataFrame()

    if "aaData" not in data:
        print(f"{stock_id}.TWO: TPEx API 無資料 → {url}")
        return pd.DataFrame()

    df = pd.DataFrame(data["aaData"], columns=[
        "日期", "成交股數", "成交金額", "開盤價", "最高價", "最低價", "收盤價", "漲跌價差", "成交筆數"
    ])
    df["Date"] = pd.to_datetime(df["日期"].str.replace("/", "-"), errors="coerce")
    df["Close"] = pd.to_numeric(df["收盤價"].str.replace(",", ""), errors="coerce")
    return df[["Date", "Close"]]

# 更新或建立 CSV
def update_stock_data(ticker, data_dir="data"):
    os.makedirs(data_dir, exist_ok=True)
    file_path = Path(data_dir) / f"{ticker}.csv"

    # 拆分 ID 和 Market
    stock_id, market = ticker.split(".")

    # 讀取舊資料
    if file_path.exists():
        df_all = pd.read_csv(file_path, parse_dates=["Date"])
    else:
        df_all = pd.DataFrame(columns=["Date", "Close"])

    # 2025/04 ~ 2025/09
    for month in range(4, 10):
        if market == "TW":
            df_new = fetch_twse(stock_id, 2025, month)
        elif market == "TWO":
            df_new = fetch_tpex(stock_id, 2025, month)
        else:
            print(f"{ticker}: 市場別 {market} 不支援")
            continue

        if not df_new.empty:
            df_all = pd.concat([df_all, df_new], ignore_index=True)

    # 去重、排序、存檔
    if not df_all.empty:
        df_all.drop_duplicates(subset=["Date"], inplace=True)
        df_all.sort_values("Date", inplace=True)
        df_all.to_csv(file_path, index=False)
        print(f"{ticker} 儲存 {len(df_all)} 筆資料")
    else:
        print(f"{ticker} 沒有資料")

def main():
    df = pd.read_csv("company_info.csv", encoding="utf-8-sig")
    tickers = df["Ticker"].dropna().tolist()

    print(f"共 {len(tickers)} 檔股票，開始下載/更新...")
    for ticker in tickers:
        try:
            update_stock_data(ticker)
        except Exception as e:
            print(f"{ticker} 失敗: {e}")

if __name__ == "__main__":
    main()
