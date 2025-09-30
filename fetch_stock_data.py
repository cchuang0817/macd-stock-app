import os
import requests
import pandas as pd
from datetime import datetime
from pathlib import Path

# 抓取 TWSE 資料 (上市)
def fetch_twse(stock_id, year, month):
    url = f"https://www.twse.com.tw/exchangeReport/STOCK_DAY?response=json&date={year}{month:02d}01&stockNo={stock_id}"
    resp = requests.get(url)
    data = resp.json()
    if data["stat"] != "OK":
        return pd.DataFrame()

    df = pd.DataFrame(data["data"], columns=data["fields"])

    # 日期格式：YYYY/MM/DD
    df["Date"] = pd.to_datetime(df["日期"], format="%Y/%m/%d", errors="coerce")
    df["Close"] = pd.to_numeric(df["收盤價"].str.replace(",", ""), errors="coerce")
    return df[["Date", "Close"]]

# 抓取 TPEx 資料 (上櫃)
def fetch_tpex(stock_id, year, month):
    url = f"https://www.tpex.org.tw/web/stock/aftertrading/daily_trading_info/st43_result.php?l=zh-tw&d={year-1911}/{month:02d}&stkno={stock_id}"
    resp = requests.get(url)
    data = resp.json()
    if "aaData" not in data:
        return pd.DataFrame()

    df = pd.DataFrame(data["aaData"])

    # 日期格式：民國年 → 轉西元年
    df["Date"] = df[0].apply(lambda x: datetime.strptime(
        str(int(x.split("/")[0]) + 1911) + "/" + x.split("/")[1] + "/" + x.split("/")[2],
        "%Y/%m/%d"
    ))
    df["Close"] = pd.to_numeric(df[2].str.replace(",", ""), errors="coerce")
    return df[["Date", "Close"]]

# 主程式：讀取 company_info.csv
def main():
    company_df = pd.read_csv("company_info.csv", encoding="utf-8-sig")
    os.makedirs("data", exist_ok=True)

    for _, row in company_df.iterrows():
        ticker = row["Ticker"]
        stock_id = ticker.split(".")[0]
        market = row["Market"]

        all_data = []
        for month in range(4, 10):  # 抓取 4 月到 9 月
            if market == "TW":
                df = fetch_twse(stock_id, 2025, month)
            else:
                df = fetch_tpex(stock_id, 2025, month)
            if not df.empty:
                all_data.append(df)

        if all_data:
            df_all = pd.concat(all_data, ignore_index=True)
            df_all.sort_values("Date", inplace=True)
            df_all.to_csv(f"data/{ticker}.csv", index=False)
            print(f"{ticker} 儲存 {len(df_all)} 筆資料")
        else:
            print(f"{ticker} 沒有資料")

if __name__ == "__main__":
    main()
