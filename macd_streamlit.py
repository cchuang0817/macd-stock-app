# macd_streamlit.py
import streamlit as st
import pandas as pd
import os
import subprocess

st.set_page_config(page_title="MACD 篩選系統", layout="wide")

st.title("📈 MACD 股票追蹤系統")

# === 按鈕：重新分析 ===
if st.button("🔄 重新執行 MACD 分析"):
    with st.spinner("正在從 Yahoo Finance 抓取股價並計算 MACD，請稍候..."):
        result = subprocess.run(["python", "fetch_stock_data.py"], capture_output=True, text=True)
        st.text(result.stdout)

# === 顯示結果 ===
if os.path.exists("macd_filtered.csv"):
    df = pd.read_csv("macd_filtered.csv")
    if df.empty:
        st.warning("目前沒有符合條件的股票。")
    else:
        st.success(f"找到 {len(df)} 檔符合條件的股票")
        st.dataframe(df, use_container_width=True)
else:
    st.info("尚未產生結果。請先執行上方的分析。")

st.markdown("---")
st.caption("© 2025 MACD Stock App — Powered by yfinance & Streamlit")
