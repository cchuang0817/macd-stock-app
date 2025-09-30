import os
import requests
import pandas as pd
from pathlib import Path

# === 抓上市 (TWSE) ===
def fetch_twse(stock_id, year, month):
    url = f"https://www.twse.com.tw/exchangeReport/STOCK_DAY"
    params = {
        "response": "json",
        "date": f"{year}{month:02}01",
        "stockNo": stock_id,
    }
    resp = requests.get(url, params=params)
    data = resp.json()

    if data["stat"] != "OK":
        return pd.DataFrame()

    df = pd.DataFrame(data["data"], columns=data["fields"])
    df["Date"] = pd.to_datetime(df["日期"].str.replace("/", "-"), errors="coerce")
    df["Close"] = pd.to_numeric(df["收盤價"].str.replace(",", ""), errors="coerce")
    return df[["Date", "Close"]]

# === 抓上櫃 (TPEx) ===
def fetch_tpex(stock_id, year, month):
    roc_year = year - 1911  # 民國年
    url = f"https://www.tpex.org.tw/web/stock/aftertrading/daily_trading_info/st43_result.php"
    params = {
        "l": "zh-tw",
        "d": f"{roc_year}/{month:02}",
        "stkno": stock_id,
    }
    resp = requests.get(url, params=params)
    data = resp.json()

    if "aaData" not in data:
        return pd.DataFrame()

    df = pd.DataFrame(data["aaData"], columns=data["columns"])
    df["Date"] = pd.to_datetime(df["日期"].str.replace("/", "-"), errors="coerce")
    df["Close"] = pd.to_numeric(df["收盤"].str.replace(",", ""), errors="coerce")
    return df[["Date", "Close"]]

# === 儲存或更新 CSV ===
def save_to_csv(ticker, new_df, data_dir="data"):
    os.makedirs(data_dir, exist_ok=True)
    file_path = Path(data_dir) / f"{ticker}.csv"

    if file_path.exists():
        old_df = pd.read_csv(file_path, parse_dates=["Date"])
        df_all = pd.concat([old_df, new_df], ignore_index=True)
        df_all.drop_duplicates(subset=["Date"], inplace=True)
        df_all.sort_values("Date", inplace=True)
    else:
        df_all = new_df

    df_all.to_csv(file_path, index=False)
    print(f"{ticker} 儲存 {len(new_df)} 筆資料 (總共 {len(df_all)} 筆)")
    return df_all

# === 主程式 ===
def main():
    # 從 company_info.csv 讀取股票清單
    company_df = pd.read_csv("company_info.csv")
    tickers = company_df["Ticker"].tolist()

    year = 2025
    for ticker in tickers:
        stock_id, market = ticker.split(".")  # e.g. 1101.TW / 5483.TWO
        all_data = pd.DataFrame()

        for month in range(4, 10):  # 測試：先抓 4~9 月
            if market == "TW":
                df = fetch_twse(stock_id, year, month)
            else:
                df = fetch_tpex(stock_id, year, month)

            if not df.empty:
                all_data = pd.concat([all_data, df], ignore_index=True)

        if not all_data.empty:
            save_to_csv(ticker, all_data)
        else:
            print(f"{ticker} 沒有抓到資料")

if __name__ == "__main__":
    main()
