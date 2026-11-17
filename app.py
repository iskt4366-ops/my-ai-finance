import streamlit as st
import pandas as pd
import time
import json
import os
from google import genai

st.set_page_config(page_title="나만의 AI 재무 비서 & 자산 관리", page_icon="💰", layout="wide")

# ==========================================
# 파일 경로 및 기본 설정
# ==========================================
CONFIG_FILE = "api_config.json"
TRANS_FILE = "finance_data.csv"
ASSET_FILE = "asset_data.csv"

TRANS_COLUMNS = ["날짜", "구분", "카테고리", "내용", "금액"]
ASSET_COLUMNS = ["구분", "항목명", "금액(원)", "메모"]

# 기본 자산 샘플 데이터
DEFAULT_ASSETS = [
    {"구분": "자산", "항목명": "비상금 통장 / 현금", "금액(원)": 5000000, "메모": "CMA 및 입출금 통장"},
    {"구분": "자산", "항목명": "주택 및 부동산", "금액(원)": 500000000, "메모": "서울 자택 (공동명의)"},
    {"구분": "자산", "항목명": "주식 및 투자 계좌", "금액(원)": 30000000, "메모": "국내외 주식 및 ETF"},
    {"구분": "부채", "항목명": "주택담보대출", "금액(원)": 200000000, "메모": "보금자리론 / 디딤돌 등"},
]

# 1. API Key 로드 및 저장 함수
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

# 2. 거래내역 로드/저장 함수
def load_transactions():
    if os.path.exists(TRANS_FILE):
        try:
            df = pd.read_csv(TRANS_FILE, encoding="utf-8-sig")
            for col in TRANS_COLUMNS:
                if col not in df.columns:
                    df[col] = ""
            df["금액"] = pd.to_numeric(df["금액"], errors="coerce").fillna(0).astype(int)
            return df[TRANS_COLUMNS]
        except:
            return pd.DataFrame(columns=TRANS_COLUMNS)
    return pd.DataFrame(columns=TRANS_COLUMNS)

def save_transactions(df):
    df.to_csv(TRANS_FILE, index=False, encoding="utf-8-sig")

# 3. 자산/부채 목록 로드/저장 함수 (안전 장치 강화)
def load_assets():
    if os.path.exists(ASSET_FILE):
        try:
            df = pd.read_csv(ASSET_FILE, encoding="utf-8-sig")
            for col in ASSET_COLUMNS:
                if col not in df.columns:
                    df[col] = ""
            df["금액(원)"] = pd.to_numeric(df["금액(원)"], errors="coerce").fillna(0).astype(int)
            return df[ASSET_COLUMNS]
        except:
            return pd.DataFrame(DEFAULT_ASSETS)
    else:
        df_default = pd.DataFrame(DEFAULT_ASSETS)
        df_default.to_csv(ASSET_FILE, index=False, encoding="utf-8-sig")
        return df_default

def save_assets(df):
    df.to_csv(ASSET_FILE, index=False, encoding="utf-8-sig")

# 세션 상태 초기화
if "transactions" not in st.session_state:
    st.session_state.transactions = load_transactions()

if "assets" not in st.session_state:
    st.session_state.assets = load_assets()

if "saved_api_key" not in st.session_state:
    st.session_state.saved_api_key = load_saved_key()

# ==========================================
# 사이드바 설정 및 실시간 요약
# ==========================================
with st.sidebar:
    st.header("⚙️ 설정 및 요약")
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
    total_asset = df_ast[df_ast["구분"] == "자산"]["금액(원)"].sum() if not df_ast.empty else 0
    total_debt = df_ast[df_ast["구분"] == "부채"]["금액(원)"].sum() if not df_ast.empty else 0
    net_worth = total_asset - total_debt
    
    st.metric("총 순자산", f"{net_worth:,.0f}원")
    st.metric("총 자산", f"{total_asset:,.0f}원")
    st.metric("총 부채", f"{total_debt:,.0f}원")

st.title("💰 나만의 AI 재무 비서 & 자산 관리 시스템")
st.write("자산 목록, 부채, 수입/지출 내역을 통합 관리하고 AI와 대화하며 재정을 설계하세요.")

# 4개 탭 구성
tab1, tab2, tab3, tab4 = st.tabs(["📊 종합 대시보드", "🏠 자산·부채 관리", "📝 거래내역 관리", "💬 AI 재무 챗봇"])

# ==========================================
# TAB 1: 종합 대시보드
# ==========================================
with tab1:
    st.header("📊 나의 재정 상태 종합 요약")
    
    df_trx = st.session_state.transactions
    incomes = df_trx[df_trx["구분"] == "수입"]["금액"].sum() if not df_trx.empty else 0
    expenses = df_trx[df_trx["구분"] == "지출"]["금액"].sum() if not df_trx.empty else 0
    monthly_flow = incomes - expenses

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("💎 순자산 (자산-부채)", f"{net_worth:,.0f}원", delta=f"총자산 {total_asset:,.0f}원")
    col2.metric("📥 누적 수입", f"{incomes:,.0f}원")
    col3.metric("📤 누적 지출", f"{expenses:,.0f}원")
    col4.metric("💵 현금 흐름 (수입-지출)", f"{monthly_flow:,.0f}원", delta_color="normal" if monthly_flow >= 0 else "inverse")

    st.markdown("---")
    c_left, c_right = st.columns(2)
    
    with c_left:
        st.subheader("🏠 자산 구성 현황")
        if not df_ast.empty and not df_ast[df_ast["구분"] == "자산"].empty:
            asset_summary = df_ast[df_ast["구분"] == "자산"].set_index("항목명")["금액(원)"]
            st.bar_chart(asset_summary)
        else:
            st.info("등록된 자산 항목이 없습니다.")

    with c_right:
        st.subheader("🛒 카테고리별 지출 분석")
        if not df_trx.empty and not df_trx[df_trx["구분"] == "지출"].empty:
            exp_summary = df_trx[df_trx["구분"] == "지출"].groupby("카테고리")["금액"].sum()
            st.bar_chart(exp_summary)
        else:
            st.info("기록된 지출 내역이 없습니다.")

# ==========================================
# TAB 2: 자산·부채 관리
# ==========================================
with tab2:
    st.header("🏠 보유 자산 및 부채(대출) 목록 관리")
    st.caption("부동산, 예적금, 주식 등의 자산과 주택담보대출 같은 부채를 자유롭게 추가·수정하고 순자산을 관리하세요.")

    edited_assets = st.data_editor(
        st.session_state.assets,
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "구분": st.column_config.SelectboxColumn("구분", options=["자산", "부채"], required=True),
            "항목명": st.column_config.TextColumn("자산/부채 항목명 (예: 주택, 주식, 주담대)", required=True),
            "금액(원)": st.column_config.NumberColumn("금액 (원)", min_value=0, step=100000, format="%d원", required=True),
            "메모": st.column_config.TextColumn("메모 또는 상세 설명"),
        },
        key="asset_editor"
    )

    if st.button("💾 자산/부채 변경사항 저장", type="primary"):
        clean_ast = edited_assets.dropna(subset=["항목명"]).copy()
        clean_ast["금액(원)"] = pd.to_numeric(clean_ast["금액(원)"], errors="coerce").fillna(0).astype(int)
        st.session_state.assets = clean_ast.reset_index(drop=True)
        save_assets(st.session_state.assets)
        st.success("자산 및 부채 목록이 안전하게 저장되었습니다!")
        st.rerun()

# ==========================================
# TAB 3: 거래내역 관리
# ==========================================
with tab3:
    st.header("📝 거래내역 (수입·지출·대출상환) 관리")
    
    with st.expander("📁 은행/카드사 명세서 파일(CSV, Excel) 일괄 업로드하기"):
        uploaded_file = st.file_uploader("명세서 파일을 업로드하세요", type=["csv", "xlsx"])
        if uploaded_file is not None:
            try:
                raw_df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith(".csv") else pd.read_excel(uploaded_file)
                st.success(f"'{uploaded_file.name}' 로드 성공! ({len(raw_df)}건)")
                cols = raw_df.columns.tolist()
                
                col_a, col_b, col_c, col_d = st.columns(4)
                with col_a:
                    date_col = st.selectbox("날짜 열", ["오늘 날짜로 일괄 적용"] + cols)
                with col_b:
                    desc_col = st.selectbox("내용(적요) 열", cols)
                with col_c:
                    amt_col = st.selectbox("금액 열", cols)
                with col_d:
                    default_type = st.selectbox("기본 구분", ["지출", "수입", "대출"])

                default_cat = st.text_input("일괄 카테고리", value="명세서일괄")

                if st.button("📥 거래내역 장부에 병합하기", type="primary"):
                    mapped_df = pd.DataFrame()
                    mapped_df["날짜"] = pd.Timestamp.now().strftime("%Y-%m-%d") if date_col == "오늘 날짜로 일괄 적용" else raw_df[date_col].astype(str).str[:10]
                    mapped_df["구분"] = default_type
                    mapped_df["카테고리"] = default_cat
                    mapped_df["내용"] = raw_df[desc_col].astype(str)
                    cleaned_amt = raw_df[amt_col].astype(str).str.replace(r"[^0-9\-]", "", regex=True)
                    mapped_df["금액"] = pd.to_numeric(cleaned_amt, errors="coerce").fillna(0).abs().astype(int)

                    st.session_state.transactions = pd.concat([st.session_state.transactions, mapped_df], ignore_index=True)
                    save_transactions(st.session_state.transactions)
                    st.success("내역이 장부에 성공적으로 반영되었습니다!")
                    st.rerun()
            except Exception as e:
                st.error(f"오류 발생: {e}")

    st.subheader("✏️ 장부 직접 편집 및 관리")
    edited_trx = st.data_editor(
        st.session_state.transactions,
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "날짜": st.column_config.TextColumn("날짜 (YYYY-MM-DD)"),
            "구분": st.column_config.SelectboxColumn("구분", options=["지출", "수입", "대출"], required=True),
            "카테고리": st.column_config.TextColumn("카테고리"),
            "내용": st.column_config.TextColumn("내용"),
            "금액": st.column_config.NumberColumn("금액 (원)", min_value=0, step=1000, format="%d원"),
        },
        key="trx_editor"
    )

    if st.button("💾 거래내역 수정사항 저장", type="primary"):
        clean_trx = edited_trx.dropna(how="all").copy()
        clean_trx["금액"] = pd.to_numeric(clean_trx["금액"], errors="coerce").fillna(0).astype(int)
        st.session_state.transactions = clean_trx.reset_index(drop=True)
        save_transactions(st.session_state.transactions)
        st.success("거래내역이 저장되었습니다!")
        st.rerun()

# ==========================================
# TAB 4: AI 재무 챗봇
# ==========================================
with tab4:
    st.header("💬 AI 재무 비서 챗봇")
    st.caption("일상 대화처럼 지출이나 수입을 말씀하시면 장부에 자동 기록되며, 재무 상담도 가능합니다.")

    if "messages" not in st.session_state:
        st.session_state.messages = []

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if user_prompt := st.chat_input("예: '오늘 점심값으로 1만 3천 원 썼어' 또는 '내 자산 구조에 대해 조언해줘'"):
        st.session_state.messages.append({"role": "user", "content": user_prompt})
        with st.chat_message("user"):
            st.markdown(user_prompt)

        active_key = st.session_state.saved_api_key
        if not active_key:
            ai_response = "⚠️ 왼쪽 사이드바에 Gemini API Key를 먼저 입력해주세요!"
        else:
            ai_response = None
            client = genai.Client(api_key=active_key)
            today_str = pd.Timestamp.now().strftime("%Y-%m-%d")

            asset_summary_text = st.session_state.assets.to_string(index=False) if not st.session_state.assets.empty else "자산 없음"
            context_data = f"\n[현재 자산 및 부채 현황]\n{asset_summary_text}\n[현재 순자산: {net_worth:,.0f}원]"

            system_instruction = f"""
            당신은 전문적인 AI 재무 비서입니다. 오늘 날짜는 {today_str}입니다.
            사용자의 입력에 지출, 수입, 대출 관련 내역이 있다면 친절하게 답변한 뒤,
            답변 맨 마지막 줄에 아래 형식의 JSON 태그를 정확히 추가하세요.
            형식: [LOG]{{"날짜": "{today_str}", "구분": "지출", "카테고리": "식비", "내용": "점심식사", "금액": 13000}}[/LOG]
            - '구분'은 "지출", "수입", "대출" 중 하나로 분류하세요.
            - 일반 상담이나 질문일 경우 [LOG] 태그를 생략하세요.
            {context_data}
            """

            full_prompt = f"{system_instruction}\n\n사용자 입력: {user_prompt}"

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
                import re
                logs = re.findall(r"\[LOG\](.*?)\[/LOG\]", ai_response, re.DOTALL)
                added_count = 0
                new_rows = []
                for log_str in logs:
                    try:
                        log_data = json.loads(log_str.strip())
                        new_rows.append({
                            "날짜": log_data.get("날짜", today_str),
                            "구분": log_data.get("구분", "지출"),
                            "카테고리": log_data.get("카테고리", "기타"),
                            "내용": log_data.get("내용", "내역"),
                            "금액": int(log_data.get("금액", 0))
                        })
                        added_count += 1
                    except:
                        pass

                if new_rows:
                    st.session_state.transactions = pd.concat(
                        [st.session_state.transactions, pd.DataFrame(new_rows)], ignore_index=True
                    )
                    save_transactions(st.session_state.transactions)

                ai_response = re.sub(r"\[LOG\].*?\[/LOG\]", "", ai_response, flags=re.DOTALL).strip()
                if added_count > 0:
                    ai_response += f"\n\n✅ **({added_count}건의 내역이 거래내역 장부에 자동 반영되었습니다!)**"

        with st.chat_message("assistant"):
            st.markdown(ai_response)
        st.session_state.messages.append({"role": "assistant", "content": ai_response})
