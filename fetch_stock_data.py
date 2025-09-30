import os
import requests
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta
from finmind.data import DataLoader

# ====== TWSE API (上市) ======
def fetch_twse(stock_id, date):
    """抓上市股票日收盤價"""
    url = f"https://www.twse.com.tw/exchangeReport/STOCK_DAY?response=json&date={date.strftime('%Y%m%d')}&stockNo={stock_id}"
    resp = requests.get(url)
    data = resp.json()
    if data.get("stat") != "OK":
        return pd.DataFrame()
    df = pd.DataFrame(data["data"], columns=data["fields"])
    df["Date"] = pd.to_datetime(df["日期"].str.replace("/", "-"), errors="coerce")
    df["Close"] = pd.to_numeric(df["收盤價"].str.replace(",", ""), errors="coerce")
    return df[["Date", "Close"]]

# ====== FinMind API (上市 + 上櫃) ======
def fetch_finmind(stock_id, start_date, end_date):
    """用 FinMind API 抓台股資料（上市+上櫃）"""
    api = DataLoader()
    df = api.taiwan_stock_daily(stock_id=stock_id, start_date=start_date, end_date=end_date)
    if df.empty:
        return pd.DataFrame()
    df["Date"] = pd.to_datetime(df["date"])
    df["Close"] = pd.to_numeric(df["close"], errors="coerce")
    return df[["Date", "Close"]]

# ====== 存檔 ======
def save_to_csv(ticker, df, data_dir="data"):
    os.makedirs(data_dir, exist_ok=True)
    file_path = Path(data_dir) / f"{ticker}.csv"

    if file_path.exists():
        old = pd.read_csv(file_path, parse_dates=["Date"])
        merged = pd.concat([old, df]).drop_duplicates(subset=["Date"]).sort_values("Date")
        new_count = len(merged) - len(old)
    else:
        merged = df
        new_count = len(df)
    merged.to_csv(file_path, index=False, encoding="utf-8-sig")
    print(f"{ticker} 儲存 {len(merged)} 筆資料 (本次新增 {new_count} 筆)")

# ====== 主程式 ======
def main():
    tickers = ["1101.TW", "5483.TWO"]  # 上市 + 上櫃
    today = datetime.today()
    start_date = (today - timedelta(days=200)).strftime("%Y-%m-%d")  # 抓最近200天
    end_date = today.strftime("%Y-%m-%d")

    for ticker in tickers:
        stock_id = ticker.split(".")[0]

        if ticker.endswith(".TW"):  # 上市
            df = fetch_twse(stock_id, today.replace(day=1))
            if df.empty:  # 如果 TWSE 抓不到，就用 FinMind
                print(f"{ticker} 用 FinMind 補資料")
                df = fetch_finmind(stock_id, start_date, end_date)
        else:  # 上櫃
            df = fetch_finmind(stock_id, start_date, end_date)

        if not df.empty:
            save_to_csv(ticker, df)
        else:
            print(f"{ticker} 沒有抓到資料")

if __name__ == "__main__":
    main()
