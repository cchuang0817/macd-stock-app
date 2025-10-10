import os
import pandas as pd
import streamlit as st
from datetime import datetime

# === 基本設定 ===
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
COMPANY_FILE = os.path.join(BASE_DIR, "company_info.csv")

st.set_page_config(page_title="MACD Pro v2.1 Dashboard", layout="wide")

st.title("📊 MACD Pro v2.1 — 放寬條件篩選結果")
st.markdown("""
顯示每日自動分析結果（放寬條件版）  
版本：**v2.1 (Relaxed Conditions)**  
---
""")

# === 檢查資料夾 ===
if not os.path.exists(DATA_DIR):
    st.error("❌ 找不到 data 資料夾，請確認資料是否存在。")
    st.stop()

# === 讀取所有分析結果 ===
files = sorted(
    [f for f in os.listdir(DATA_DIR) if f.startswith("macd_main_") and f.endswith(".csv")],
    reverse=True
)

if len(files) == 0:
    st.warning("⚠️ 尚無分析結果，請先執行 fetch_stock_data_pro_v2.1.py")
    st.stop()

# === 日期選擇器 ===
dates = [f.replace("macd_main_", "").replace(".csv", "") for f in files]
selected_date = st.selectbox("📅 選擇日期", dates, index=0)
selected_file = os.path.join(DATA_DIR, f"macd_main_{selected_date}.csv")

st.info(f"載入分析結果：`{selected_file}`")

# === 讀取主策略資料 ===
try:
    df = pd.read_csv(selected_file)
except Exception as e:
    st.error(f"❌ 無法讀取檔案：{e}")
    st.stop()

if df.empty or df.iloc[0]["Ticker"] == "N/A":
    st.warning("📭 當天無符合主策略的股票。")
    st.stop()

# === 嘗試讀取公司對照表 ===
if os.path.exists(COMPANY_FILE):
    df_company = pd.read_csv(COMPANY_FILE)
    if "Ticker" in df_company.columns:
        df = df.merge(df_company, on="Ticker", how="left")
        if "Name" in df.columns and "Industry" in df.columns:
            df = df[["Ticker", "Name", "Industry", "LastDate", "MACD", "Signal", "Hist",
                     "ATR", "StopLoss", "TakeProfit", "RevenueGrowth"]]
else:
    st.warning("⚠️ 未找到 company_info.csv，將僅顯示代號。")

# === 資料顯示 ===
st.subheader("📈 符合主策略的股票")

st.dataframe(
    df.style.format({
        "MACD": "{:.2f}",
        "Signal": "{:.2f}",
        "Hist": "{:.2f}",
        "ATR": "{:.2f}",
        "StopLoss": "{:.2f}",
        "TakeProfit": "{:.2f}",
        "RevenueGrowth": "{:.2%}" if df["RevenueGrowth"].dtype != object else "{}"
    }),
    use_container_width=True,
    hide_index=True
)

# === 基本統計 ===
st.markdown("### 📊 統計摘要")
col1, col2, col3 = st.columns(3)
col1.metric("符合股票數量", len(df))
col2.metric("平均 MACD", round(df["MACD"].astype(float).mean(), 2))
col3.metric("平均 Revenue 成長率", f"{round(df['RevenueGrowth'].astype(float).mean()*100,2)}%" if df["RevenueGrowth"].dtype != object else "N/A")

# === 加值：篩選功能 ===
st.markdown("### 🔍 進階篩選")
col_a, col_b = st.columns(2)

with col_a:
    industry_filter = st.selectbox("選擇產業類別", ["全部"] + sorted(df["Industry"].dropna().unique().tolist()) if "Industry" in df.columns else ["全部"])
with col_b:
    name_filter = st.text_input("股票名稱關鍵字（支援模糊搜尋）", "")

filtered_df = df.copy()
if industry_filter != "全部" and "Industry" in df.columns:
    filtered_df = filtered_df[filtered_df["Industry"] == industry_filter]
if name_filter:
    filtered_df = filtered_df[filtered_df["Name"].astype(str).str.contains(name_filter, case=False, na=False)]

st.dataframe(
    filtered_df,
    use_container_width=True,
    hide_index=True
)

# === Footer ===
st.markdown("---")
st.caption(f"版本：MACD Pro v2.1 (Relaxed Conditions) ｜ 更新時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
