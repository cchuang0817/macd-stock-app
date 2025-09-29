import streamlit as st
import pandas as pd
import requests
import time
from datetime import date, datetime, timedelta, time as dtime
from pathlib import Path

# ------------------ Yahoo Chart API ------------------
def _to_unix(d: date) -> int:
    return int(datetime.combine(d, dtime(0, 0)).timestamp())

def fetch_chart_api(ticker: str, years: int = 2) -> pd.DataFrame:
    end_d = date.today()
    start_d = end_d - timedelta(days=365*years)
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
    params = {
        "period1": _to_unix(start_d),
        "period2": _to_unix(end_d + timedelta(days=1)),
        "interval": "1d",
        "events": "div,splits",
        "includeAdjustedClose": "true"
    }
    headers = {"User-Agent": "Mozilla/5.0"}
    r = requests.get(url, params=params, headers=headers, timeout=30)
    if r.status_code != 200:
        return pd.DataFrame()
    result = r.json().get("chart", {}).get("result")
    if not result:
        return pd.DataFrame()

    res = result[0]
    ts = res.get("timestamp")
    quote = (res.get("indicators", {}).get("quote") or [{}])[0]
    adj = (res.get("indicators", {}).get("adjclose") or [{}])[0]

    if not ts or not quote:
        return pd.DataFrame()

    df = pd.DataFrame({
        "Open": quote.get("open"),
        "High": quote.get("high"),
        "Low": quote.get("low"),
        "Close": quote.get("close"),
        "Adj Close": adj.get("adjclose"),
        "Volume": quote.get("volume"),
    }, index=pd.to_datetime(ts, unit="s").tz_localize("UTC").tz_convert("Asia/Taipei"))
    df.index = df.index.tz_localize(None)
    return df.dropna(how="all")

# ------------------ MACD 計算 ------------------
def compute_macd(df: pd.DataFrame, fast=12, slow=26, signal=9) -> pd.DataFrame:
    price = df["Adj Close"] if "Adj Close" in df.columns else df["Close"]
    ema_fast = price.ewm(span=fast, adjust=False).mean()
    ema_slow = price.ewm(span=slow, adjust=False).mean()
    macd = ema_fast - ema_slow
    sig = macd.ewm(span=signal, adjust=False).mean()
    hist = macd - sig
    return pd.DataFrame({
        "Close": price,
        "MACD": macd,
        "Signal": sig,
        "Hist": hist
    }, index=df.index)

# ------------------ 策略判斷 ------------------
def passed_strategy(df: pd.DataFrame) -> bool:
    if len(df) < 60:
        return False

    macd = df["MACD"]
    signal = df["Signal"]
    hist = df["Hist"]

    # 1. MACD 曾經上穿 0 軸
    crossed = ((macd.shift(1) <= 0) & (macd > 0)).any()

    # 2. 最近 5 天 MACD / Signal 都 > 0
    recent = df.tail(5)
    positive_zone = (recent["MACD"] > 0).all() and (recent["Signal"] > 0).all()

    # 3. 柱狀綠棒且連續 3 天縮短
    recent_hist = hist.tail(3)
    if len(recent_hist) < 3:
        return False
    negative = (recent_hist < 0).all()
    shrinking = all(recent_hist.iloc[i] < recent_hist.iloc[i+1] for i in range(2))

    # 4. 第三天的柱狀值介於 -1 和 0 之間
    last_hist = recent_hist.iloc[-1]
    near_zero = (-1 < last_hist < 0)

    return crossed and positive_zone and negative and shrinking and near_zero

# ------------------ 公司基本資料 ------------------
def fetch_company_info(ticker: str) -> dict:
    url = f"https://query1.finance.yahoo.com/v10/finance/quoteSummary/{ticker}"
    params = {"modules": "price,summaryProfile"}
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        r = requests.get(url, params=params, headers=headers, timeout=10)
        if r.status_code != 200:
            return {"Name": "N/A", "Industry": "N/A", "MarketCap": "N/A"}
        result = r.json().get("quoteSummary", {}).get("result")
        if not result:
            return {"Name": "N/A", "Industry": "N/A", "MarketCap": "N/A"}
        data = result[0]

        name = (
            data.get("price", {}).get("longName")
            or data.get("price", {}).get("shortName")
            or "N/A"
        )
        marketcap = data.get("price", {}).get("marketCap", {}).get("raw")
        if marketcap:
            marketcap = f"{marketcap/1e9:.1f}B"
        else:
            marketcap = "N/A"

        industry = data.get("summaryProfile", {}).get("industry", "N/A")

        return {"Name": name, "Industry": industry, "MarketCap": marketcap}
    except Exception:
        return {"Name": "N/A", "Industry": "N/A", "MarketCap": "N/A"}

# ------------------ 股票清單讀取 ------------------
def load_tickers(file_path="tickers_tw.txt") -> list[str]:
    path = Path(file_path)
    if not path.exists():
        return []
    tickers = []
    for line in path.read_text(encoding="utf-8").splitlines():
        t = line.strip()
        if not t or t.startswith("#"):
            continue
        tickers.append(t)
    return tickers

# ------------------ Streamlit 介面 ------------------
st.title("📈 台股 MACD 篩選策略")

tickers = load_tickers()
if not tickers:
    st.error("⚠️ 找不到 tickers_tw.txt 或檔案內容是空的，請建立股票代號清單")
    st.stop()

results = []

with st.spinner("正在篩選股票，請稍候..."):
    for t in tickers:
        df = fetch_chart_api(t, years=2)
        if df.empty:
            results.append({"Ticker": t, "Match": False, "Reason": "no_data"})
            continue
        macd_df = compute_macd(df)
        ok = passed_strategy(macd_df)
        last = macd_df.tail(1).iloc[0]

        info = fetch_company_info(t)

        results.append({
            "Ticker": t,
            "Name": info["Name"],
            "Industry": info["Industry"],
            "MarketCap": info["MarketCap"],
            "Match": ok,
            "Close": round(float(last["Close"]), 2),
            "MACD": round(float(last["MACD"]), 4),
            "Signal": round(float(last["Signal"]), 4),
            "Hist": round(float(last["Hist"]), 4),
            "LastDate": macd_df.index[-1].strftime("%Y-%m-%d")
        })
        time.sleep(1)

df_result = pd.DataFrame(results)

st.subheader("篩選結果")
st.dataframe(df_result, use_container_width=True)  # 自動滿版
