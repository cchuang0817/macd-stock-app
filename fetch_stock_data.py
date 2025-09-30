import os
import requests
import pandas as pd
from pathlib import Path

def fetch_twse_month(stock_no, year, month):
    """抓取 TWSE 指定股票某一個月份的日成交資料"""
    # 組合成 YYYYMM01
    date = f"{year}{month:02d}01"
    url = f"https://www.twse.com.tw/exchangeReport/STOCK_DAY?response=json&date={date}&stockNo={stock_no}"

    resp = requests.get(url)
    data = resp.json()

    if data["stat"] != "OK":
        print(f"{stock_no} 沒有抓到資料")
        return pd.DataFrame(columns=["Date", "Close"])

    # TWSE 回傳的日期格式是 民國年/xx/xx，要轉換
    rows = []
    for item in data["data"]:
        roc_date = item[0]  # 民國年格式
        close = item[6]     # 收盤價

        # 轉西元日期
        y, m, d = roc_date.split("/")
        y = int(y) + 1911
        date_str = f"{y}-{m.zfill(2)}-{d.zfill(2)}"

        rows.append([date_str, float(close.replace(",", ""))])

    df = pd.DataFrame(rows, columns=["Date", "Close"])
    return df


def main():
    os.makedirs("data", exist_ok=True)
    df_company = pd.read_csv("company_info.csv", encoding="utf-8-sig")

    year, month = 2025, 9  # 固定抓 2025 年 9 月
    for ticker in df_company["Ticker"].head(5):  # 測試先抓前 5 檔
        stock_no = ticker.replace(".TW", "").replace(".TWO", "")
        df = fetch_twse_month(stock_no, year, month)

        if not df.empty:
            path = Path("data") / f"{ticker}.csv"
            df.to_csv(path, index=False)
            print(f"{ticker} 共 {len(df)} 筆，已存到 {path}")
        else:
            print(f"{ticker} 無資料")


if __name__ == "__main__":
    main()
