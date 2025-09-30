import os
import requests
import pandas as pd
from pathlib import Path
from datetime import datetime

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
    df["Date"] = pd.to_datetime(df["日期"].str.replace("/", "-"), errors="coerce")
    df["Close"] = pd.to_numeric(df["收盤價"].str.replace(",", ""), errors="coerce")
    return df[["Date", "Close"]]


# 確保 CSV 檔案存在
def ensure_csv_exists(ticker, data_dir="data"):
    os.makedirs(data_dir, exist_ok=True)
    file_path = Path(data_dir) / f"{ticker}.csv"
    if not file_path.exists():
        df = pd.DataFrame(columns=["Date", "Close"])
        df.to_csv(file_path, index=False, encoding="utf-8-sig")
        print(f"{ticker}: 建立空檔案，避免 push 失敗")
    return file_path


# 主程式：只針對 1101.TW
def main():
    ticker = "1101.TW"
    stock_no = "1101"
    data_dir = "data"
    file_path = ensure_csv_exists(ticker, data_dir)

    # 先抓 2025/04 ~ 2025/09 六個月的資料
    frames = []
    for month in range(4, 10):
        df = fetch_monthly(stock_no, 2025, month)
        if df is not None and not df.empty:
            frames.append(df)

    if frames:
        df_all = pd.concat(frames, ignore_index=True).drop_duplicates(subset=["Date"])
        df_all = df_all.sort_values("Date")
        df_all.to_csv(file_path, index=False, encoding="utf-8-sig")
        print(f"{ticker}: 更新完成，共 {len(df_all)} 筆")
    else:
        print(f"{ticker}: 沒有任何可用資料，保留空檔案")


if __name__ == "__main__":
    main()
