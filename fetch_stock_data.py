import os
import requests
import pandas as pd
from pathlib import Path

# 民國 → 西元
def roc_to_ad(date_str):
    parts = date_str.split("/")
    if len(parts) == 3:
        year = int(parts[0]) + 1911
        return f"{year}-{parts[1]}-{parts[2]}"
    return None

# 下載單一股票某月份的資料
def fetch_monthly(stock_no, year, month):
    url = f"https://www.twse.com.tw/exchangeReport/STOCK_DAY?response=json&date={year}{month:02d}01&stockNo={stock_no}"
    resp = requests.get(url)
    if resp.status_code != 200:
        print(f"{stock_no}: TWSE 回應失敗 ({resp.status_code})")
        return None

    data = resp.json()
    if data.get("stat") != "OK":
        print(f"{stock_no}: 沒有找到資料 ({year}-{month:02d})")
        return None

    df = pd.DataFrame(data["data"], columns=data["fields"])

    # 民國 → 西元日期
    df["Date"] = df["日期"].apply(roc_to_ad)
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")

    # 收盤價 → 數字
    df["Close"] = pd.to_numeric(df["收盤價"].str.replace(",", ""), errors="coerce")

    return df[["Date", "Close"]]

# 確保 CSV 存在
def ensure_csv_exists(ticker, data_dir="data"):
    os.makedirs(data_dir, exist_ok=True)
    file_path = Path(data_dir) / f"{ticker}.csv"
    if not file_path.exists():
        pd.DataFrame(columns=["Date", "Close"]).to_csv(file_path, index=False, encoding="utf-8-sig")
        print(f"{ticker}: 建立空檔案")
    return file_path

# 主程式：針對 1101.TW，逐月更新
def main():
    ticker = "1101.TW"
    stock_no = "1101"
    file_path = ensure_csv_exists(ticker)

    for month in range(4, 10):  # 2025/04 ~ 2025/09
        df_new = fetch_monthly(stock_no, 2025, month)
        if df_new is None or df_new.empty:
            continue

        # 讀取舊資料
        df_old = pd.read_csv(file_path, parse_dates=["Date"]) if file_path.exists() else pd.DataFrame(columns=["Date", "Close"])

        # 合併去重
        df_all = pd.concat([df_old, df_new], ignore_index=True).drop_duplicates(subset=["Date"])
        df_all = df_all.sort_values("Date")

        # 回存
        df_all.to_csv(file_path, index=False, encoding="utf-8-sig")
        print(f"{ticker}: {month} 月完成，累計 {len(df_all)} 筆")

if __name__ == "__main__":
    main()
