import os
import requests
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path

# TWSE API: 一次只能抓一個月
TWSE_API = "https://www.twse.com.tw/exchangeReport/STOCK_DAY"

# TPEx API: 一次只能抓一個月
TPEX_API = "https://www.tpex.org.tw/web/stock/aftertrading/daily_trading_info/st43_result.php"

DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)

def fetch_twse(stock_id, date):
    """從 TWSE 抓取單月資料"""
    params = {
        "response": "json",
        "date": date,
        "stockNo": stock_id
    }
    resp = requests.get(TWSE_API, params=params)
    data = resp.json()

    if "data" not in data:
        return pd.DataFrame()

    df = pd.DataFrame(data["data"], columns=data["fields"])
    df = df.rename(columns={"日期": "Date", "收盤價": "Close"})
    df["Date"] = pd.to_datetime(df["Date"].str.replace("/", "-"), errors="coerce")
    df["Close"] = pd.to_numeric(df["Close"].str.replace(",", ""), errors="coerce")
    return df[["Date", "Close"]].dropna()


def fetch_tpex(stock_id, date):
    """從 TPEx 抓取單月資料"""
    params = {
        "l": "zh-tw",
        "d": f"{int(date[:4])-1911}/{date[4:6]}",  # 民國年/月
        "stkno": stock_id
    }
    resp = requests.get(TPEX_API, params=params)
    data = resp.json()

    if "aaData" not in data:
        return pd.DataFrame()

    df = pd.DataFrame(data["aaData"])
    df = df.rename(columns={0: "Date", 2: "Close"})
    df["Date"] = pd.to_datetime(df["Date"].str.replace("/", "-"), errors="coerce")
    df["Close"] = pd.to_numeric(df["Close"].str.replace(",", ""), errors="coerce")
    return df[["Date", "Close"]].dropna()


def fetch_stock_data(ticker):
    """抓取 6 個月資料並存檔"""
    file_path = Path(DATA_DIR) / f"{ticker}.csv"

    # 判斷上市 / 上櫃
    stock_id = ticker.replace(".TW", "").replace(".TWO", "")
    is_twse = ticker.endswith(".TW")

    # 最近六個月
    today = datetime.today()
    dfs = []
    for i in range(6):
        month_date = (today - timedelta(days=i*30)).strftime("%Y%m01")  # 每月第一天
        if is_twse:
            df = fetch_twse(stock_id, month_date)
        else:
            df = fetch_tpex(stock_id, month_date)
        if not df.empty:
            dfs.append(df)

    if dfs:
        df_all = pd.concat(dfs, ignore_index=True).drop_duplicates(subset=["Date"])
        df_all = df_all.sort_values("Date")
        df_all.to_csv(file_path, index=False)
        print(f"{ticker} 下載完成，共 {len(df_all)} 筆")
    else:
        print(f"{ticker} 沒有抓到資料")


def main():
    tickers = pd.read_csv("company_info.csv")["Ticker"].dropna().tolist()
    print(f"共 {len(tickers)} 檔股票，開始下載...")

    for ticker in tickers:
        try:
            fetch_stock_data(ticker)
        except Exception as e:
            print(f"{ticker} 失敗: {e}")


if __name__ == "__main__":
    main()
