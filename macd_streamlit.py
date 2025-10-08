import streamlit as st
import pandas as pd
import os
from datetime import datetime

# === 路徑設定 ===
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")

st.set_page_config(page_title="MACD 指標監控", layout="wide")

st.title("📊 MACD 選股結果瀏覽器")

# === 載入公司對照表 ===
company_file = os.path.join(DATA_DIR, "company_info.csv")
if not os.path.exists(company_file):
    st.error("找不到 company_info.csv，請確認放在 data 資料夾中。")
    st.stop()

df_company = pd.read_csv(company_file)

# === 搜尋可用日期 ===
files = sorted(
    [f for f in os.listdir(DATA_DIR) if f.startswith("macd_main_") and f.endswith(".csv")],
    reverse=True
)
if not files:
    st.warning("目前 data 資料夾中找不到任何 MACD 結果檔案。")
    st.stop()

# 取出日期清單
dates = [f.replace("macd_main_", "").replace(".csv", "") for f in files]
selected_date = st.selectbox("📅 選擇日期", dates)

# === 讀取主策略與觀察池 ===
main_file = os.path.join(DATA_DIR, f"macd_main_{selected_date}.csv")
watch_file = os.path.join(DATA_DIR, f"macd_watchlist_{selected_date}.csv")

df_main = pd.read_csv(main_file)
df_watch = pd.read_csv(watch_file)

# === 比對公司中文名稱與產業 ===
def merge_company_info(df):
    if df.empty or "Ticker" not in df.columns:
        return df
    df = pd.merge(df, df_company, on="Ticker", how="left")
    # 排序欄位順序（中文名稱、產業、MACD、Signal、Hist）
    cols = ["Ticker", "Name", "Industry", "MACD", "Signal", "Hist", "LastDate"]
    return df[[c for c in cols if c in df.columns]]

df_main_merged = merge_company_info(df_main)
df_watch_merged = merge_company_info(df_watch)

# === 顯示統計摘要 ===
col1, col2 = st.columns(2)
with col1:
    st.metric("主策略符合數", len(df_main_merged))
with col2:
    st.metric("觀察池符合數", len(df_watch_merged))

st.markdown("---")

# === 顯示主策略表格 ===
st.subheader("✅ 主策略（高勝率篩選）")
if df_main_merged.empty or df_main_merged["Ticker"].iloc[0] == "N/A":
    st.info("目前沒有符合主策略條件的股票。")
else:
    st.dataframe(df_main_merged, use_container_width=True)

# === 顯示觀察池表格 ===
st.subheader("👀 觀察池（潛在轉折候選）")
if df_watch_merged.empty or df_watch_merged["Ticker"].iloc[0] == "N/A":
    st.info("目前沒有符合觀察池條件的股票。")
else:
    st.dataframe(df_watch_merged, use_container_width=True)

# === 顯示來源說明 ===
st.markdown("---")
st.caption(f"資料來源：Yahoo Finance，自動生成日期：{selected_date}")
