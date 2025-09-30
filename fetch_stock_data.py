import os
import requests
import pandas as pd
from datetime import datetime
from pathlib import Path

DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)

# 讀取股票清單
def load_tickers(file_path="company_info.csv"):
    df = pd.read_csv(file_path, encoding="utf-8-sig")
    return df["Ticker"].dropna().tolist()

# 抓取 TWSE 單月資料
def fetch_twse(stock_no, year, month):
    url = f"https://www.twse.com.tw/exchangeReport/STOCK_DAY?response=json&date={year}{month:02d}01&stockNo={stock_no}"
    resp = requests.get(url)
    data = resp.json()
    if data.get("stat") != "OK":
        return pd.DataFrame()
    df = pd.DataFrame(data["data"], columns=data["fields"])
    df["Date"] = pd.to_datetime(df["日期"].str.replace("/", "-"), errors="coerce")
    df["Close"] = pd.to_numeric(df["收盤價"].str.replace(",", ""), errors="coerce")
    return df[["Date", "Close"]]

# 抓取 TPEx 單月資料
def fetch_tpex(stock_no, year, month):
    roc_year = year - 1911
    roc_date = f"{roc_year}/{month:02d}"
    url = f"https://www.tpex.org.tw/web/stock/aftertrading/daily_trading_info/st43_result.php?l=zh-tw&d={roc_date}&stkno={stock_no}"
    resp = requests.get(url)
    data = resp.json()
    if not data.get("aaData"):
        return pd.DataFrame()
    df = pd.DataFrame(data["aaData"])
    df["Date"] = pd.to_datetime(df[0].str.replace("/", "-"), errors="coerce")
    df["Close"] = pd.to_numeric(df[6].str.replace(",", ""), errors="coerce")
    return df[["Date", "Close"]]

# 儲存到 CSV
def save_to_csv(ticker, df_new):
    file_path = Path(DATA_DIR) / f"{ticker}.csv"
    if file_path.exists():
        df_old = pd.read_csv(file_path, parse_dates=["Date"])
        df_all = pd.concat([df_old, df_new], ignore_index=True)
        df_all.drop_duplicates(subset=["Date"], inplace=True)
    else:
        df_all = df_new
    df_all.sort_values("Date", inplace=True)
    df_all.to_csv(file_path, index=False, encoding="utf-8-sig")

def main():
    tickers = load_tickers("company_info.csv")
    today = datetime.today()
    year, month = today.year, today.month

    for ticker in tickers:
        try:
            stock_no = ticker.replace(".TW", "").replace(".TWO", "")
            all_data = []
            for m in range(4, month + 1):  # 先從 4 月抓到當月
                if ticker.endswith(".TW"):
                    df = fetch_twse(stock_no, year, m)
                else:
                    df = fetch_tpex(stock_no, year, m)
                if not df.empty:
                    all_data.append(df)
            if all_data:
                df_all = pd.concat(all_data, ignore_index=True)
                save_to_csv(ticker, df_all)
                print(f"{ticker} 更新完成，共 {len(df_all)} 筆")
            else:
                print(f"{ticker} 沒有抓到資料")
        except Exception as e:
            print(f"{ticker} 失敗: {e}")

if __name__ == "__main__":
    main()
