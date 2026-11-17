import streamlit as st
import pandas as pd
import time
import json
import os
import re
from google import genai
from datetime import datetime

st.set_page_config(page_title="나만의 AI 재무 비서 & 자산 관리", page_icon="💰", layout="wide")

CONFIG_FILE = "api_config.json"
TRANS_FILE = "finance_data.csv"
ASSET_FILE = "asset_data.csv"

DEFAULT_ASSETS = [
    {"구분": "자산", "항목명": "비상금 통장 / 현금", "금액(원)": 5000000, "메모": "CMA 및 입출금 통장"},
    {"구분": "자산", "항목명": "주택 및 부동산", "금액(원)": 500000000, "메모": "서울 자택 (공동명의)"},
    {"구분": "자산", "항목명": "주식 및 투자 계좌", "금액(원)": 30000000, "메모": "국내외 주식 및 ETF"},
    {"구분": "부채", "항목명": "주택담보대출", "금액(원)": 200000000, "메모": "보금자리론 / 주담대 원리금 상환 중"},
]

def load_saved_key():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f).get("api_key", "")
        except:
            return ""
    return ""

def save_key_to_file(key):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump({"api_key": key}, f)
    except:
        pass

def load_transactions():
    if os.path.exists(TRANS_FILE):
        try:
            df = pd.read_csv(TRANS_FILE, encoding="utf-8-sig")
            df["날짜"] = df["날짜"].astype(str)
            df["구분"] = df["구분"].astype(str)
            df["카테고리"] = df["카테고리"].astype(str)
            df["내용"] = df["내용"].astype(str)
            df["금액"] = pd.to_numeric(df["금액"], errors="coerce").fillna(0).astype(int)
            return df.reset_index(drop=True)
        except:
            pass
    return pd.DataFrame(columns=["날짜", "구분", "카테고리", "내용", "금액"])

def save_transactions(df):
    df.to_csv(TRANS_FILE, index=False, encoding="utf-8-sig")

def load_assets():
    if os.path.exists(ASSET_FILE):
        try:
            df = pd.read_csv(ASSET_FILE, encoding="utf-8-sig")
            df["구분"] = df["구분"].astype(str)
            df["항목명"] = df["항목명"].astype(str)
            df["금액(원)"] = pd.to_numeric(df["금액(원)"], errors="coerce").fillna(0).astype(int)
            df["메모"] = df["메모"].fillna("").astype(str)
            if len(df) > 0:
                return df.reset_index(drop=True)
        except:
            pass
    df_default = pd.DataFrame(DEFAULT_ASSETS)
    df_default.to_csv(ASSET_FILE, index=False, encoding="utf-8-sig")
    return df_default.reset_index(drop=True)

def save_assets(df):
    df.to_csv(ASSET_FILE, index=False, encoding="utf-8-sig")

if "transactions" not in st.session_state:
    st.session_state.transactions = load_transactions()

if "assets" not in st.session_state:
    st.session_state.assets = load_assets()

if "saved_api_key" not in st.session_state:
    st.session_state.saved_api_key = load_saved_key()

now_dt = datetime.now()
current_date_str = now_dt.strftime("%Y년 %m월 %d일 (%A)")

with st.sidebar:
    st.header("⚙️ 설정 및 요약")
    st.info(f"📅 오늘 날짜:\n**{current_date_str}**")
    
    input_key = st.text_input(
        "Gemini API Key를 입력하세요",
        value=st.session_state.saved_api_key,
        type="password"
    )
    if input_key != st.session_state.saved_api_key:
        st.session_state.saved_api_key = input_key
        save_key_to_file(input_key)
        if input_key:
            st.success("🔑 API Key가 자동 저장되었습니다!")

    st.markdown("---")
    st.subheader("💡 나의 재무 건전성")
    
    df_ast = st.session_state.assets
    total_asset = df_ast[df_ast["구분"] == "자산"]["금액(원)"].sum() if not df_ast.empty and "구분" in df_ast.columns else 0
    total_debt = df_ast[df_ast["구분"] == "부채"]["금액(원)"].sum() if not df_ast.empty and "구분" in df_ast.columns else 0
    net_worth = total_asset - total_debt
    
    st.metric("총 순자산", f"{net_worth:,.0f}원")
    st.metric("총 자산", f"{total_asset:,.0f}원")
    st.metric("총 부채", f"{total_debt:,.0f}원")

st.title("💰 나만의 AI 재무 비서 & 자산 관리 시스템")
st.write(f"현재 기준일: **{current_date_str}** | 자산 수정, 고정비·주담대 관리 및 AI 재무 상담을 통합 제공합니다.")

tab1, tab2, tab3, tab4 = st.tabs(["📊 종합 대시보드", "🏠 자산·부채 관리", "📝 거래내역 & 고정비 관리", "💬 AI 재무 챗봇"])

with tab1:
    st.header("📊 나의 재정 상태 종합 요약")
    
    df_trx = st.session_state.transactions
    incomes = df_trx[df_trx["구분"] == "수입"]["금액"].sum() if not df_trx.empty and "구분" in df_trx.columns else 0
    expenses = df_trx[df_trx["구분"] == "지출"]["금액"].sum() if not df_trx.empty and "구분" in df_trx.columns else 0
    monthly_flow = incomes - expenses

    if not df_trx.empty and "날짜" in df_trx.columns:
        df_trx["날짜_dt"] = pd.to_datetime(df_trx["날짜"], errors="coerce")
        current_month = now_dt.month
        current_year = now_dt.year
        
        this_month_trx = df_trx[(df_trx["날짜_dt"].dt.year == current_year) & (df_trx["날짜_dt"].dt.month == current_month)]
        m_income = this_month_trx[this_month_trx["구분"] == "수입"]["금액"].sum()
        m_expense = this_month_trx[this_month_trx["구분"] == "지출"]["금액"].sum()
        m_net_flow = m_income - m_expense
        
        growth_rate = (m_net_flow / net_worth * 100) if net_worth > 0 else 0.0
    else:
        m_income, m_expense, m_net_flow, growth_rate = 0, 0, 0, 0.0

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("💎 순자산 (자산-부채)", f"{net_worth:,.0f}원", delta=f"총자산 {total_asset:,.0f}원")
    col2.metric("📈 이번 달 순현금 흐름", f"{m_net_flow:,.0f}원", delta=f"{growth_rate:+.2f}% 변동")
    col3.metric("📥 이번 달 총 수입", f"{m_income:,.0f}원")
    col4.metric("📤 이번 달 총 지출", f"{m_expense:,.0f}원", delta_color="inverse")

    st.markdown("---")
    c_left, c_right = st.columns(2)
    
    with c_left:
        st.subheader("🏠 자산 구성 현황")
        if not df_ast.empty and "구분" in df_ast.columns and not df_ast[df_ast["구분"] == "자산"].empty:
            sub_df = df_ast[df_ast["구분"] == "자산"]
            st.bar_chart(sub_df.set_index("항목명")["금액(원)"])
        else:
            st.info("등록된 자산 항목이 없습니다.")

    with c_right:
        st.subheader("🛒 카테고리별 지출 분석 (고정비·대출 포함)")
        if not df_trx.empty and "구분" in df_trx.columns and not df_trx[df_trx["구분"] == "지출"].empty:
            sub_trx = df_trx[df_trx["구분"] == "지출"]
            st.bar_chart(sub_trx.groupby("카테고리")["금액"].sum())
        else:
            st.info("기록된 지출 내역이 없습니다.")

with tab2:
    st.header("🏠 보유 자산 및 부채(주택담보대출 등) 관리")
    st.caption("표 안에서 직접 금액, 항목명, 메모를 수정하고 [💾 자산 변경사항 저장] 버튼을 누르세요.")

    edited_assets = st.data_editor(
        st.session_state.assets.copy(),
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "구분": st.column_config.SelectboxColumn("구분", options=["자산", "부채"], required=True),
            "항목명": st.column_config.TextColumn("자산/부채 항목명", required=True),
            "금액(원)": st.column_config.NumberColumn("금액 (원)", min_value=0, step=100000, format="%d원", required=True),
            "메모": st.column_config.TextColumn("메모 또는 상세 설명"),
        },
        key="bulletproof_asset_editor_v5"
