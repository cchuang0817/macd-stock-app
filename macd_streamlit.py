# macd_streamlit.py
import streamlit as st
import pandas as pd
import os
import subprocess

st.set_page_config(page_title="MACD 股票追蹤系統", layout="wide")

st.title("📈 MACD 股票追蹤系統")

DATA_FOLDER = "data"

# === 按鈕：重新分析 ===
if st.button("🔄 重新執行 MACD 分析"):
    with st.spinner("正在從 Yahoo Finance 抓取股價並計算 MACD，請稍候..."):
        result = subprocess.run(["python", "fetch_stock_data.py"], capture_output=True, text=True)
        st.text(result.stdout)

# === 掃描歷史檔案 ===
if not os.path.exists(DATA_FOLDER):
    os.makedirs(DATA_FOLDER)

files = sorted(
    [f for f in os.listdir(DATA_FOLDER) if f.startswith("macd_filtered_") and f.endswith(".csv")],
    reverse=True
)

if not files:
    st.info("目前尚無任何分析結果，請先執行上方的『重新分析』。")
else:
    # 讓使用者選擇日期
    file_dates = [f.replace("macd_filtered_", "").replace(".csv", "") for f in files]
    selected_date = st.selectbox("📅 選擇要檢視的分析日期：", file_dates)

    # 顯示選擇的檔案內容
    selected_file = os.path.join(DATA_FOLDER, f"macd_filtered_{selected_date}.csv")
    df = pd.read_csv(selected_file)

    st.subheader(f"📊 分析結果：{selected_date}")
    if df.empty:
        st.warning("該日期沒有符合條件的股票。")
    else:
        st.success(f"共找到 {len(df)} 檔股票符合條件。")
        st.dataframe(df, use_container_width=True)

st.markdown("---")
st.caption("© 2025 MACD Stock App — Powered by yfinance & Streamlit")
