# fetch_stock_data.py
import yfinance as yf
import pandas as pd

# === 讀取股票清單與公司資訊 ===
tickers = [
    t.strip() for t in open("tickers_tw.txt", encoding="utf-8").read().splitlines()
    if t.strip() and not t.startswith("#")
]
company_info = pd.read_csv("company_info.csv")

# === MACD 計算 ===
def calc_macd(df, fast=12, slow=26, signal=9):
    df["EMA_fast"] = df["Close"].ewm(span=fast, adjust=False).mean()
    df["EMA_slow"] = df["Close"].ewm(span=slow, adjust=False).mean()
    df["MACD"] = df["EMA_fast"] - df["EMA_slow"]
    df["Signal"] = df["MACD"].ewm(span=signal, adjust=False).mean()
    df["Hist"] = df["MACD"] - df["Signal"]
    return df.dropna()

# === MACD 條件檢查 ===
def check_macd_condition(df):
    # Step1: 六個月內曾穿越0軸
    if not ((df["MACD"] > 0).any() and (df["MACD"] < 0).any()):
        return False

    # Step2: 當前為綠柱
    last = df.iloc[-1]
    if last["Hist"] >= 0:
        return False

    # Step3: 綠柱期間 MACD & Signal > 0
    neg_hist = df[df["Hist"] < 0]
    recent_neg = neg_hist.tail(5)
    if (recent_neg["MACD"] < 0).any() or (recent_neg["Signal"] < 0).any():
        return False

    # Step4: 綠柱連續三天收斂且 Hist < -1
    if len(df) < 3:
        return False
    h1, h2, h3 = df["Hist"].iloc[-3:]
    if not (h1 < h2 < h3 and h3 < -1):
        return False

    return True

# === 主流程 ===
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
                print(f"✅ {tk} 符合條件")
            else:
                print(f"❌ {tk} 不符合條件")
        except Exception as e:
            print(f"{tk} error: {e}")

    df_out = pd.DataFrame(results)
    df_out.to_csv("macd_filtered.csv", index=False, encoding="utf-8-sig")
    print("\n=== 篩選完成 ===")
    print(df_out)
    print(f"\n共找到 {len(df_out)} 檔股票，結果已輸出至 macd_filtered.csv")

if __name__ == "__main__":
    main()
