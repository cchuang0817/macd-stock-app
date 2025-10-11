import os
import pandas as pd
import streamlit as st
from datetime import datetime
import yfinance as yf

# === 基本設定 ===
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
COMPANY_FILE = os.path.join(BASE_DIR, "company_info.csv")

st.set_page_config(page_title="MACD Pro v3.0 Dashboard", layout="wide")
st.title("📊 MACD Pro v3.0 — 含Score、現價與風報比")
st.markdown("版本 v3.0｜新增評分系統 + 風報比分析｜更新時間：" + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

# === 檢查資料 ===
if not os.path.exists(DATA_DIR):
    st.error("❌ 找不到 data 資料夾。")
    st.stop()

files = sorted(
    [f for f in os.listdir(DATA_DIR) if f.startswith("macd_main_") and f.endswith(".csv")],
    reverse=True
)

if len(files) == 0:
    st.warning("⚠️ 尚無分析結果，請先執行 fetch_stock_data_v3.0.py")
    st.stop()

# === 日期選擇 ===
dates = [f.replace("macd_main_", "").replace(".csv", "") for f in files]
selected_date = st.selectbox("📅 選擇日期", dates, index=0)
selected_file = os.path.join(DATA_DIR, f"macd_main_{selected_date}.csv")

df = pd.read_csv(selected_file)
if df.empty or df.iloc[0]["Ticker"] == "N/A":
    st.warning("📭 當天無符合主策略的股票。")
    st.stop()

# === 公司對照表 ===
if os.path.exists(COMPANY_FILE):
    df_company = pd.read_csv(COMPANY_FILE)
    if "Ticker" in df_company.columns:
        df = df.merge(df_company, on="Ticker", how="left")

# === 新增現價與風報比 ===
st.write("⏳ 正在更新最新股價與風報比...")

current_prices = []
rr_ratios = []
suggestions = []

for tk, stop, target in zip(df["Ticker"], df["StopLoss"], df["TakeProfit"]):
    try:
        data = yf.Ticker(tk).history(period="1d")
        price = round(data["Close"].iloc[-1], 2) if not data.empty else None
    except Exception:
        price = None

    if price is None:
        current_prices.append("N/A")
        rr_ratios.append("N/A")
        suggestions.append("資料不足")
        continue

    # 風報比計算
    if (price - stop) > 0:
        rr = round((target - price) / (price - stop), 2)
    else:
        rr = None

    current_prices.append(price)
    rr_ratios.append(rr if rr else "N/A")

    if rr is None or rr == "N/A":
        suggestions.append("資料不足")
    elif rr >= 2:
        suggestions.append("✅ 可試單")
    elif rr >= 1.5:
        suggestions.append("👀 觀察中")
    else:
        suggestions.append("⚠️ 風報不足")

df["CurrentPrice"] = current_prices
df["RR_Ratio"] = rr_ratios
df["Action"] = suggestions

# === 排序與顯示 ===
st.subheader("🏆 今日主策略股票（依 Score 排序）")

# 若沒有 Score 欄位，則補為 0
if "Score" not in df.columns:
    df["Score"] = 0

df = df.sort_values(by="Score", ascending=False)

# 顯示主要欄位
main_cols = [
    "Ticker", "Name", "Industry", "Date", "Score", "MACD", "Signal", "Hist",
    "RSI", "ATR", "CurrentPrice", "StopLoss", "TakeProfit", "RR_Ratio",
    "Action", "RevenueGrowth"
]
main_cols = [c for c in main_cols if c in df.columns]

st.dataframe(df[main_cols], use_container_width=True, hide_index=True)

# === 統計摘要 ===
st.markdown("### 📊 統計摘要")
col1, col2, col3, col4 = st.columns(4)
col1.metric("符合股票數量", len(df))
col2.metric("平均 Score", round(df["Score"].astype(float).mean(), 2))
col3.metric("平均 MACD", round(df["MACD"].astype(float).mean(), 2))
if "RevenueGrowth" in df.columns and df["RevenueGrowth"].dtype != object:
    col4.metric("平均營收成長率", f"{round(df['RevenueGrowth'].astype(float).mean(),2)}%")
else:
    col4.metric("平均營收成長率", "N/A")

# === TOP 10 股票摘要 ===
st.markdown("### 🥇 今日前 10 名高分股票")
top10 = df.head(10)[["Ticker", "Name", "Score", "CurrentPrice", "RR_Ratio", "Action"]]
st.table(top10)

# === 篩選功能 ===
st.markdown("### 🔍 進階篩選")
col_a, col_b, col_c = st.columns(3)
industry_filter = col_a.selectbox(
    "選擇產業類別",
    ["全部"] + sorted(df["Industry"].dropna().unique().tolist()) if "Industry" in df.columns else ["全部"]
)
name_filter = col_b.text_input("股票名稱關鍵字（支援模糊搜尋）", "")
score_min = col_c.slider("最低 Score 門檻", min_value=0, max_value=100, value=70, step=5)

filtered_df = df.copy()
if industry_filter != "全部" and "Industry" in df.columns:
    filtered_df = filtered_df[filtered_df["Industry"] == industry_filter]
if name_filter:
    filtered_df = filtered_df[filtered_df["Name"].astype(str).str.contains(name_filter, case=False, na=False)]
filtered_df = filtered_df[filtered_df["Score"] >= score_min]

st.dataframe(filtered_df, use_container_width=True, hide_index=True)

st.markdown("---")
st.caption("MACD Pro v3.0｜含Score與風報比｜By 黃植珈")
