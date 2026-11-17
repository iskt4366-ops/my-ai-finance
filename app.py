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
        key="asset_editor_final"
    )

    if st.button("💾 자산 변경사항 저장", type="primary"):
        clean_ast = edited_assets.dropna(subset=["항목명"]).copy()
        clean_ast["구분"] = clean_ast["구분"].astype(str)
        clean_ast["항목명"] = clean_ast["항목명"].astype(str)
        clean_ast["금액(원)"] = pd.to_numeric(clean_ast["금액(원)"], errors="coerce").fillna(0).astype(int)
        clean_ast["메모"] = clean_ast["메모"].fillna("").astype(str)
        
        st.session_state.assets = clean_ast.reset_index(drop=True)
        save_assets(st.session_state.assets)
        st.success("자산 및 부채 목록이 성공적으로 저장되었습니다!")
        st.rerun()

with tab3:
    st.header("📝 거래내역, 매달 고정비 및 주택담보대출 원리금 관리")
    st.caption("월급 같은 수입, 고정지출, 주택담보대출 원리금 상환 내역을 추가하고 관리하세요.")

    with st.form("add_trx_form"):
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            trx_type = st.selectbox("구분", ["지출", "수입"])
        with c2:
            trx_category = st.selectbox("카테고리", ["고정지출(통신/관리비등)", "대출원리금상환(주담대)", "식비", "급여(수입)", "기타"])
        with c3:
            trx_amount = st.number_input("금액 (원)", min_value=0, step=10000, format="%d")
        with c4:
            trx_date = st.text_input("날짜", value=now_dt.strftime("%Y-%m-%d"))
        
        trx_desc = st.text_input("내용 상세 (예: XX은행 주담대 원리금 납부, 3월 관리비 등)")
        
        trx_submitted = st.form_submit_button("📥 내역 장부에 추가하기")
        if trx_submitted and trx_desc:
            new_trx = pd.DataFrame([{
                "날짜": str(trx_date),
                "구분": str(trx_type),
                "카테고리": str(trx_category),
                "내용": str(trx_desc),
                "금액": int(trx_amount)
            }])
            st.session_state.transactions = pd.concat([st.session_state.transactions, new_trx], ignore_index=True).reset_index(drop=True)
            save_transactions(st.session_state.transactions)
            st.success("장부에 성공적으로 반영되었습니다!")
            st.rerun()

    st.subheader("📋 전체 장부 목록 (직접 편집 가능)")
    edited_trx = st.data_editor(
        st.session_state.transactions.copy(),
        num_rows="dynamic",
        use_container_width=True,
        key="trx_editor_final"
    )

    if st.button("💾 거래내역 수정사항 저장", type="primary"):
        clean_trx = edited_trx.dropna(how="all").copy()
        clean_trx["날짜"] = clean_trx["날짜"].astype(str)
        clean_trx["구분"] = clean_trx["구분"].astype(str)
        clean_trx["카테고리"] = clean_trx["카테고리"].astype(str)
        clean_trx["내용"] = clean_trx["내용"].astype(str)
        clean_trx["금액"] = pd.to_numeric(clean_trx["금액"], errors="coerce").fillna(0).astype(int)
        
        st.session_state.transactions = clean_trx.reset_index(drop=True)
        save_transactions(st.session_state.transactions)
        st.success("거래내역이 저장되었습니다!")
        st.rerun()

with tab4:
    st.header("💬 AI 재무 비서 챗봇")
    st.caption("예: '이번 달 주택담보대출 원리금 85만 원 나갔어'라고 말씀하시면 자동으로 장부에 기록되며, 재무 상담도 가능합니다.")

    if "messages" not in st.session_state:
        st.session_state.messages = []

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if user_prompt := st.chat_input("예: '월급 400만 원 들어왔어' 또는 '내 고정비와 주담대 상환 부담이 어때?'"):
        st.session_state.messages.append({"role": "user", "content": user_prompt})
        with st.chat_message("user"):
            st.markdown(user_prompt)

        active_key = st.session_state.saved_api_key
        if not active_key:
            ai_response = "⚠️ 왼쪽 사이드바에 Gemini API Key를 먼저 입력해주세요!"
        else:
            ai_response = None
            client = genai.Client(api_key=active_key)
            today_str = now_dt.strftime("%Y-%m-%d")

            asset_summary_text = st.session_state.assets.to_string(index=False) if not st.session_state.assets.empty else "자산 없음"
            context_data = f"\n[현재 기준일: {today_str}]\n[현재 자산 및 부채 현황]\n{asset_summary_text}\n[현재 순자산: {net_worth:,.0f}원]"

            system_instruction = f"""
            당신은 전문적인 AI 재무 비서입니다. 오늘 날짜는 {today_str}입니다.
            사용자의 입력에 지출, 수입, 대출원리금 상환 관련 내역이 있다면 친절하게 답변한 뒤,
            답변 맨 마지막 줄에 아래 형식의 JSON 태그를 정확히 추가하세요.
            형식: [LOG]{{"날짜": "{today_str}", "구분": "지출", "카테고리": "대출원리금상환(주담대)", "내용": "주담대 원리금 납부", "금액": 850000}}[/LOG]
            - '구분'은 "지출", "수입" 중 하나로 분류하세요.
            - '카테고리'는 "고정지출(통신/관리비등)", "대출원리금상환(주담대)", "식비", "급여(수입)", "기타" 중 하나로 매칭하세요.
            - 일반 상담이나 질문일 경우 [LOG] 태그를 생략하세요.
            {context_data}
            """

            full_prompt = f"{system_instruction}\n\n사용자 입력: {user_prompt}"

            with st.spinner("🧠 AI 재무 비서가 분석 및 답변을 작성 중입니다..."):
                for attempt in range(3):
                    try:
                        response = client.models.generate_content(
                            model="gemini-3.8-flash",
                            contents=full_prompt,
                        )
                        ai_response = response.text
                        break
                    except Exception as e:
                        if "503" in str(e) and attempt < 2:
                            time.sleep(2)
                            continue
                        else:
                            ai_response = f"API 호출 중 오류 발생: {e}"

            if ai_response and "[LOG]" in ai_response:
                logs = re.findall(r"\[LOG\](.*?)\[/LOG\]", ai_response, re.DOTALL)
                added_count = 0
                new_rows = []
                for log_str in logs:
                    try:
                        log_data = json.loads(log_str.strip())
                        new_rows.append({
                            "날짜": str(log_data.get("날짜", today_str)),
                            "구분": str(log_data.get("구분", "지출")),
                            "카테고리": str(log_data.get("카테고리", "기타")),
                            "내용": str(log_data.get("내용", "내역")),
                            "금액": int(log_data.get("금액", 0))
                        })
                        added_count += 1
                    except:
                        pass

                if new_rows:
                    new_df = pd.DataFrame(new_rows)
                    st.session_state.transactions = pd.concat([st.session_state.transactions, new_df], ignore_index=True).reset_index(drop=True)
                    save_transactions(st.session_state.transactions)

                ai_response = re.sub(r"\[LOG\].*?\[/LOG\]", "", ai_response, flags=re.DOTALL).strip()
                if added_count > 0:
                    ai_response += f"\n\n✅ **({added_count}건의 내역이 고정비/대출 장부에 자동 반영되었습니다!)**"

        with st.chat_message("assistant"):
            st.markdown(ai_response)
        st.session_state.messages.append({"role": "assistant", "content": ai_response})
