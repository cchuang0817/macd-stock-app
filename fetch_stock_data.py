# fetch_stock_data.py
import yfinance as yf
import pandas as pd
import os
from datetime import datetime

tickers = [
    t.strip() for t in open("tickers_tw.txt", encoding="utf-8").read().splitlines()
    if t.strip() and not t.startswith("#")
]
company_info = pd.read_csv("company_info.csv")

def calc_macd(df, fast=12, slow=26, signal=9):
    df["EMA_fast"] = df["Close"].ewm(span=fast, adjust=False).mean()
    df["EMA_slow"] = df["Close"].ewm(span=slow, adjust=False).mean()
    df["MACD"] = df["EMA_fast"] - df["EMA_slow"]
    df["Signal"] = df["MACD"].ewm(span=signal, adjust=False).mean()
    df["Hist"] = df["MACD"] - df["Signal"]
    return df.dropna()

def check_macd_condition(df):
    if not ((df["MACD"] > 0).any() and (df["MACD"] < 0).any()):
        return False
    last = df.iloc[-1]
    if last["Hist"] >= 0:
        return False
    neg_hist = df[df["Hist"] < 0]
    recent_neg = neg_hist.tail(5)
    if (recent_neg["MACD"] < 0).any() or (recent_neg["Signal"] < 0).any():
        return False
    if len(df) < 3:
        return False
    h1, h2, h3 = df["Hist"].iloc[-3:]
    if not (h1 < h2 < h3 and h3 < -1):
        return False
    return True

def main():
    results = []
    for tk in tickers:
        try:
            df = yf.Ticker(tk).history(period="6mo", interval="1d")
            if df.empty:
                continue
            df = calc_macd(df)
            if check_macd_condition(df):
                last = df.iloc[-1]
                info = company_info[company_info["Ticker"] == tk]
                name = info.iloc[0]["Name"] if not info.empty else "N/A"
                industry = info.iloc[0]["Industry"] if not info.empty else "N/A"

                results.append({
                    "Ticker": tk,
                    "Name": name,
                    "Industry": industry,
                    "LastDate": df.index[-1].strftime("%Y-%m-%d"),
                    "MACD": round(last["MACD"], 2),
                    "Signal": round(last["Signal"], 2),
                    "Hist": round(last["Hist"], 2)
                })
        except Exception as e:
            print(f"{tk} error: {e}")

    os.makedirs("data", exist_ok=True)
    date_str = datetime.now().strftime("%Y-%m-%d")
    file_path = f"data/macd_filtered_{date_str}.csv"

    # === 若無資料，也輸出 N/A 一列 ===
    if len(results) == 0:
        print("\n⚠️ 沒有任何股票符合 MACD 條件，輸出空白表格。")
        df_out = pd.DataFrame([{
            "Ticker": "N/A",
            "Name": "N/A",
            "Industry": "N/A",
            "LastDate": "N/A",
            "MACD": "N/A",
            "Signal": "N/A",
            "Hist": "N/A"
        }])
    else:
        df_out = pd.DataFrame(results)

    df_out.to_csv(file_path, index=False, encoding="utf-8-sig")
    print(f"\n共找到 {len(results)} 檔股票，結果已輸出至 {file_path}")

if __name__ == "__main__":
    main()
