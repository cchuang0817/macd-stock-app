import os
import time
import random
from datetime import datetime
import pandas as pd
import yfinance as yf

# === 基本路徑設定 ===
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CACHE_DIR = os.path.join(BASE_DIR, "data", "cache")
OUTPUT_DIR = os.path.join(BASE_DIR, "data")
LOG_DIR = os.path.join(BASE_DIR, "data", "logs")

os.makedirs(CACHE_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

print(f"建立資料夾：")
print(f"  CACHE_DIR = {CACHE_DIR}")
print(f"  OUTPUT_DIR = {OUTPUT_DIR}")
print(f"  LOG_DIR = {LOG_DIR}")

# === 股票清單讀取 ===
tickers_file = os.path.join(BASE_DIR, "tickers_test.txt")

if not os.path.exists(tickers_file):
    print(f"❌ 找不到股票清單檔案：{tickers_file}")
    exit(1)

with open(tickers_file, "r", encoding="utf-8") as f:
    tickers = [line.strip() for line in f if line.strip() and not line.startswith("#")]

if len(tickers) == 0:
    print(f"⚠️ 股票清單為空，請確認 {tickers_file} 內容")
    exit(1)

print(f"已讀取清單：{tickers_file}")
print(f"載入股票數量：{len(tickers)}")
print("股票清單：", ", ".join(tickers))


# === MACD 計算函式（修正版） ===
def calc_macd(df, fast=12, slow=26, signal=9):
    df = df.copy()
    df["EMA_fast"] = df["Close"].ewm(span=fast, adjust=False, min_periods=fast).mean()
    df["EMA_slow"] = df["Close"].ewm(span=slow, adjust=False, min_periods=slow).mean()
    df["MACD"] = df["EMA_fast"] - df["EMA_slow"]
    df["Signal"] = df["MACD"].ewm(span=signal, adjust=False, min_periods=signal).mean()
    df["Hist"] = df["MACD"] - df["Signal"]
    return df.dropna()


# === 主策略（嚴格條件） ===
def check_macd_main(df):
    df = df.sort_index(ascending=True).copy()
    # 1️⃣ 六個月內 MACD 曾穿越 0 軸
    if not ((df["MACD"] > 0).any() and (df["MACD"] < 0).any()):
        return False
    # 2️⃣ 當前為綠柱
    last = df.iloc[-1]
    if last["Hist"] >= 0:
        return False
    # 3️⃣ 綠柱期間 MACD 與 Signal 不低於 0
    neg_hist = df[df["Hist"] < 0]
    recent_neg = neg_hist.tail(5)
    if (recent_neg["MACD"] < 0).any() or (recent_neg["Signal"] < 0).any():
        return False
    # 4️⃣ 綠柱絕對值連續三天收斂，且最後一根在 -1~0 之間
    if len(df) < 3:
        return False
    h1, h2, h3 = df["Hist"].iloc[-3:]
    if not (abs(h1) > abs(h2) > abs(h3) and -1 <= h3 < 0):
        return False
    return True


# === 觀察池（放寬條件） ===
def check_macd_watchlist(df):
    df = df.sort_index(ascending=True).copy()
    # 1️⃣ 六個月內 MACD 曾穿越 0 軸
    if not ((df["MACD"] > 0).any() and (df["MACD"] < 0).any()):
        return False
    # 2️⃣ 當前為綠柱
    last = df.iloc[-1]
    if last["Hist"] >= 0:
        return False
    # 3️⃣ MACD 與 Signal 不低於 -1（放寬）
    neg_hist = df[df["Hist"] < 0]
    recent_neg = neg_hist.tail(5)
    if (recent_neg["MACD"] < -1).any() or (recent_neg["Signal"] < -1).any():
        return False
    # 4️⃣ 綠柱絕對值連續三天收斂，且最後一根在 -3~0 之間（放寬）
    if len(df) < 3:
        return False
    h1, h2, h3 = df["Hist"].iloc[-3:]
    if not (abs(h1) > abs(h2) > abs(h3) and -3 <= h3 < 0):
        return False
    return True


# === 主流程 ===
def main():
    start_time = time.time()
    main_results = []
    watch_results = []
    failed = []

    print(f"\n開始抓取 {len(tickers)} 檔股票...\n")

    for i, tk in enumerate(tickers, start=1):
        print(f"[{i}/{len(tickers)}] 抓取 {tk} ...")
        try:
            df = yf.Ticker(tk).history(period="6mo", interval="1d")
            if df.empty:
                print(f"⚠️ {tk} 無資料，可能暫停交易或下市")
                failed.append((tk, "Empty DataFrame"))
                continue

            # 儲存快取
            cache_file = os.path.join(CACHE_DIR, f"{tk}.csv")
            df.to_csv(cache_file)
            print(f"  ↳ 已更新快取: {cache_file}")

            # 計算 MACD 並判斷
            df = calc_macd(df)
            if df.empty:
                continue

            if check_macd_main(df):
                last = df.iloc[-1]
                main_results.append({
                    "Ticker": tk,
                    "LastDate": df.index[-1].strftime("%Y-%m-%d"),
                    "MACD": round(last["MACD"], 2),
                    "Signal": round(last["Signal"], 2),
                    "Hist": round(last["Hist"], 2)
                })
                print(f"  ✅ {tk} 符合【主策略】")

            elif check_macd_watchlist(df):
                last = df.iloc[-1]
                watch_results.append({
                    "Ticker": tk,
                    "LastDate": df.index[-1].strftime("%Y-%m-%d"),
                    "MACD": round(last["MACD"], 2),
                    "Signal": round(last["Signal"], 2),
                    "Hist": round(last["Hist"], 2)
                })
                print(f"  👀 {tk} 符合【觀察池】")

            else:
                print(f"  ℹ️ {tk} 不符合條件")

        except Exception as e:
            print(f"❌ {tk} 抓取錯誤: {e}")
            failed.append((tk, str(e)))

        # 避免被 Yahoo 封鎖
        time.sleep(random.uniform(0.8, 1.2))

    # === 輸出結果 ===
    date_str = datetime.now().strftime("%Y-%m-%d")
    main_csv = os.path.join(OUTPUT_DIR, f"macd_main_{date_str}.csv")
    watch_csv = os.path.join(OUTPUT_DIR, f"macd_watchlist_{date_str}.csv")
    log_file = os.path.join(LOG_DIR, f"fetch_log_{date_str}.txt")

    def write_csv(file_path, data_list, tag):
        if len(data_list) == 0:
            df_out = pd.DataFrame([{
                "Ticker": "N/A", "LastDate": "N/A",
                "MACD": "N/A", "Signal": "N/A", "Hist": "N/A"
            }])
        else:
            df_out = pd.DataFrame(data_list)
        df_out.to_csv(file_path, index=False, encoding="utf-8-sig")
        print(f"📄 已輸出 {tag}: {file_path}")

    write_csv(main_csv, main_results, "主策略結果")
    write_csv(watch_csv, watch_results, "觀察池結果")

    # === Log Summary ===
    duration = round((time.time() - start_time) / 60, 2)
    summary = [
        f"=== MACD 抓取任務完成 {date_str} ===",
        f"總股票數: {len(tickers)}",
        f"成功更新: {len(tickers) - len(failed)}",
        f"抓取失敗: {len(failed)}",
        f"符合主策略: {len(main_results)}",
        f"符合觀察池: {len(watch_results)}",
        f"總執行時間: {duration} 分鐘",
        "",
        "=== 抓取失敗清單 ==="
    ]
    for tk, reason in failed:
        summary.append(f"- {tk} → {reason}")

    with open(log_file, "w", encoding="utf-8") as f:
        f.write("\n".join(summary))

    print("\n".join(summary))
    print(f"\n📘 Log 已儲存：{log_file}")
    print(f"📄 主策略結果：{main_csv}")
    print(f"📄 觀察池結果：{watch_csv}")


if __name__ == "__main__":
    main()
