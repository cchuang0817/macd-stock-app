import os
import requests
import pandas as pd
from datetime import datetime
from pathlib import Path

DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)


# ===== 抓取 TWSE（上市）資料 =====
def fetch_twse(stock_id, year, month):
    url = "https://www.twse.com.tw/exchangeReport/STOCK_DAY"
    params = {
        "response": "json",
        "date": f"{year}{month:02}01",
        "stockNo": stock_id
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/123.0.0.0 Safari/537.36"
    }

    resp = requests.get(url, params=params, headers=headers, timeout=10)

    try:
        data = resp.json()
    except Exception:
        print(f"{stock_id}.TW 回傳非 JSON（可能被擋），URL: {resp.url}")
        return pd.DataFrame()

    if "data" not in data:
        return pd.DataFrame()

    df = pd.DataFrame(data["data"], columns=data["fields"])
    df["Date"] = pd.to_datetime(df["日期"].str.replace("/", "-"), errors="coerce")
    df["Close"] = pd.to_numeric(df["收盤價"].str.replace(",", ""), errors="coerce")
    return df[["Date", "Close"]]


# ===== 抓取 TPEx（上櫃）資料 =====
def fetch_tpex(stock_id, year, month):
    roc_year = year - 1911  # 民國年
    url = "https://www.tpex.org.tw/web/stock/aftertrading/daily_trading_info/st43_result.php"
    params = {
        "l": "zh-tw",
        "d": f"{roc_year}/{month:02}",
        "stkno": stock_id,
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/123.0.0.0 Safari/537.36"
    }

    resp = requests.get(url, params=params, headers=headers, timeout=10)

    try:
        data = resp.json()
    except Exception:
        print(f"{stock_id}.TWO 回傳非 JSON（可能被擋），URL: {resp.url}")
        return pd.DataFrame()

    if "aaData" not in data:
        return pd.DataFrame()

    df = pd.DataFrame(data["aaData"], columns=data["columns"])
    df["Date"] = pd.to_datetime(df["日期"].str.replace("/", "-"), errors="coerce")
    df["Close"] = pd.to_numeric(df["收盤"].str.replace(",", ""), errors="coerce")
    return df[["Date", "Close"]]


# ===== 主程式 =====
def main():
    company_df = pd.read_csv("company_info.csv", encoding="utf-8-sig")

    for _, row in company_df.iterrows():
        ticker = row["Ticker"]
        stock_id = ticker.split(".")[0]
        market = ticker.split(".")[1]  # TW / TWO
        all_data = []

        for month in range(4, 10):  # 先抓 2025/04 ~ 2025/09
            if market == "TW":
                df = fetch_twse(stock_id, 2025, month)
            else:
                df = fetch_tpex(stock_id, 2025, month)

            if not df.empty:
                all_data.append(df)

        if all_data:
            df_all = pd.concat(all_data, ignore_index=True).drop_duplicates("Date")
            file_path = Path(DATA_DIR) / f"{ticker}.csv"
            df_all.to_csv(file_path, index=False, encoding="utf-8-sig")
            print(f"{ticker} 儲存 {len(df_all)} 筆資料（總共 {len(all_data)} 個月）")
        else:
            print(f"{ticker} 沒有抓到資料")


if __name__ == "__main__":
    main()
