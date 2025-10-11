import os
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from datetime import datetime
import yfinance as yf

# === 基本設定 ===
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
COMPANY_FILE = os.path.join(BASE_DIR, "company_info.csv")

st.set_page_config(page_title="MACD Pro v3.1 Dashboard", layout="wide")
st.title("📊 MACD Pro v3.1 — 含Score、現價與風報比")
st.markdown("版本 v3.1｜新增分數構成分析 + 中文介面｜更新時間：" + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

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

    # 風報比
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

df["現價"] = current_prices
df["風報比"] = rr_ratios
df["操作建議"] = suggestions

# === 中文欄位對應 ===
rename_map = {
    "Ticker": "股票代號",
    "Name": "股票名稱",
    "Industry": "產業類別",
    "Date": "日期",
    "Score": "總分",
    "Pattern": "形態完美度",
    "Momentum": "動能強度",
    "Fundamental": "基本面",
    "RS": "相對強度",
    "CurrentPrice": "現價",
    "StopLoss": "停損價",
    "TakeProfit": "目標價",
    "RR_Ratio": "風報比",
    "Action": "操作建議",
    "RevenueGrowth": "營收成長率(%)"
}

df = df.rename(columns=rename_map)

# === 隱藏內部運算欄位 ===
drop_cols = [c for c in ["MACD", "Signal", "Hist", "RSI", "ATR"] if c in df.columns]
df = df.drop(columns=drop_cols, errors="ignore")

# === 排序顯示 ===
if "總分" in df.columns:
    df = df.sort_values(by="總分", ascending=False)

st.subheader("🏆 今日主策略股票（依 Score 排序）")

display_cols = [
    "股票代號", "股票名稱", "產業類別", "日期", "總分",
    "現價", "停損價", "目標價", "風報比", "操作建議", "營收成長率(%)"
]
display_cols = [c for c in display_cols if c in df.columns]
st.dataframe(df[display_cols], use_container_width=True, hide_index=True)

# === 統計摘要 ===
st.markdown("### 📊 統計摘要")
col1, col2, col3, col4 = st.columns(4)
col1.metric("符合股票數量", len(df))
col2.metric("平均總分", round(df["總分"].astype(float).mean(), 2))
if "營收成長率(%)" in df.columns:
    col3.metric("平均營收成長率(%)", round(df["營收成長率(%)"].astype(float).mean(), 2))
if "風報比" in df.columns and pd.to_numeric(df["風報比"], errors="coerce").notnull().any():
    col4.metric("平均風報比", round(pd.to_numeric(df["風報比"], errors="coerce").mean(), 2))

# === Top 10 顯示 ===
st.markdown("### 🥇 今日前10名高分股票")
top10_cols = ["股票代號", "股票名稱", "總分", "現價", "風報比", "操作建議"]
top10_cols = [c for c in top10_cols if c in df.columns]
st.table(df.head(10)[top10_cols])

# === 分數構成分析 ===
if all(c in df.columns for c in ["形態完美度", "動能強度", "基本面", "相對強度"]):
    st.markdown("### 🎯 分數構成分析")
    selected_ticker = st.selectbox("選擇股票以查看分數構成", df["股票代號"].tolist())
    row = df[df["股票代號"] == selected_ticker].iloc[0]

    st.write(pd.DataFrame({
        "評分項目": ["形態完美度", "動能強度", "基本面", "相對強度(RS)"],
        "得分": [row["形態完美度"], row["動能強度"], row["基本面"], row["相對強度"]],
        "滿分": [40, 30, 15, 15]
    }))

    # 雷達圖顯示
    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=[row["形態完美度"], row["動能強度"], row["基本面"], row["相對強度"]],
        theta=["形態完美度", "動能強度", "基本面", "相對強度(RS)"],
        fill='toself', name='分數構成'
    ))
    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 40])),
        showlegend=False,
        margin=dict(l=40, r=40, t=40, b=40)
    )
    st.plotly_chart(fig, use_container_width=True)

# === 進階篩選 ===
st.markdown("### 🔍 進階篩選")
col_a, col_b, col_c = st.columns(3)
industry_filter = col_a.selectbox(
    "選擇產業類別",
    ["全部"] + sorted(df["產業類別"].dropna().unique().tolist()) if "產業類別" in df.columns else ["全部"]
)
name_filter = col_b.text_input("股票名稱關鍵字（支援模糊搜尋）", "")
score_min = col_c.slider("最低 Score 門檻", min_value=0, max_value=100, value=70, step=5)

filtered_df = df.copy()
if industry_filter != "全部" and "產業類別" in df.columns:
    filtered_df = filtered_df[filtered_df["產業類別"] == industry_filter]
if name_filter:
    filtered_df = filtered_df[filtered_df["股票名稱"].astype(str).str.contains(name_filter, case=False, na=False)]
if "總分" in filtered_df.columns:
    filtered_df = filtered_df[filtered_df["總分"] >= score_min]

st.dataframe(filtered_df[display_cols], use_container_width=True, hide_index=True)

st.markdown("---")
st.caption("MACD Pro v3.1｜含Score構成與中文介面｜By 黃植珈")
