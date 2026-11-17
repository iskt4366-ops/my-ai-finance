import streamlit as st
import pandas as pd
import time
import json
import os
from google import genai

st.set_page_config(page_title="나만의 AI 재무 비서 & 자산 관리", page_icon="💰", layout="wide")

CONFIG_FILE = "api_config.json"
TRANS_FILE = "finance_data.csv"
ASSET_FILE = "asset_data.csv"

DEFAULT_ASSETS = [
    {"구분": "자산", "항목명": "비상금 통장 / 현금", "금액(원)": 5000000, "메모": "CMA 및 입출금 통장"},
    {"구분": "자산", "항목명": "주택 및 부동산", "금액(원)": 500000000, "메모": "서울 자택 (공동명의)"},
    {"구분": "자산", "항목명": "주식 및 투자 계좌", "금액(원)": 30000000, "메모": "국내외 주식 및 ETF"},
    {"구분": "부채", "항목명": "주택담보대출", "금액(원)": 200000000, "메모": "보금자리론 / 디딤돌 등"},
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
            if "금액" in df.columns:
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
            if "금액(원)" in df.columns:
                df["금액(원)"] = pd.to_numeric(df["금액(원)"], errors="coerce").fillna(0).astype(int)
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
    total_asset = df_ast[df_ast["구분"] == "자산"]["금액(원)"].sum() if not df_ast.empty and "구분" in df_ast.columns else 0
    total_debt = df_ast[df_ast["구분"] == "부채"]["금액(원)"].sum() if not df_ast.empty and "구분" in df_ast.columns else 0
    net_worth = total_asset - total_debt
    
    st.metric("총 순자산", f"{net_worth:,.0f}원")
    st.metric("총 자산", f"{total_asset:,.0f}원")
    st.metric("총 부채", f"{total_debt:,.0f}원")

st.title("💰 나만의 AI 재무 비서 & 자산 관리 시스템")
st.write("자산 목록, 부채, 수입/지출 내역을 통합 관리하고 AI와 대화하며 재정을 설계하세요.")

tab1, tab2, tab3, tab4 = st.tabs(["📊 종합 대시보드", "🏠 자산·부채 관리", "📝 거래내역 관리", "💬 AI 재무 챗봇"])

with tab1:
    st.header("📊 나의 재정 상태 종합 요약")
    
    df_trx = st.session_state.transactions
    incomes = df_trx[df_trx["구분"] == "수입"]["금액"].sum() if not df_trx.empty and "구분" in df_trx.columns else 0
    expenses = df_trx[df_trx["구분"] == "지출"]["금액"].sum() if not df_trx.empty and "구분" in df_trx.columns else 0
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
        if not df_ast.empty and "구분" in df_ast.columns and not df_ast[df_ast["구분"] == "자산"].empty:
            sub_df = df_ast[df_ast["구분"] == "자산"]
            st.bar_chart(sub_df.set_index("항목명")["금액(원)"])
        else:
            st.info("등록된 자산 항목이 없습니다.")

    with c_right:
        st.subheader("🛒 카테고리별 지출 분석")
        if not df_trx.empty and "구분" in df_trx.columns and not df_trx[df_trx["구분"] == "지출"].empty:
            sub_trx = df_trx[df_trx["구분"] == "지출"]
            st.bar_chart(sub_trx.groupby("카테고리")["금액"].sum())
        else:
            st.info("기록된 지출 내역이 없습니다.")

with tab2:
    st.header("🏠 보유 자산 및 부채(대출) 목록 관리")
    st.caption("등록된 자산과 부채 목록을 확인하고, 항목을 추가하거나 삭제할 수 있습니다.")

    # 현재 등록된 자산 목록 안전하게 표로 출력
    st.dataframe(st.session_state.assets, use_container_width=True)

    st.markdown("### ➕ 새로운 자산/부채 추가하기")
    with st.form("add_asset_form"):
        c1, c2, c3 = st.columns(3)
        with c1:
            new_type = st.selectbox("구분", ["자산", "부채"])
        with c2:
            new_name = st.text_input("항목명 (예: 예금, 주식, 대출)")
        with c3:
            new_amt = st.number_input("금액 (원)", min_value=0, step=100000, format="%d")
        new_memo = st.text_input("메모 (선택사항)")
        
        submitted = st.form_submit_button("➕ 항목 추가하기")
        if submitted and new_name:
            new_row = pd.DataFrame([{"구분": new_type, "항목명": new_name, "금액(원)": int(new_amt), "메모": new_memo}])
            st.session_state.assets = pd.concat([st.session_state.assets, new_row], ignore_index=True)
            save_assets(st.session_state.assets)
            st.success(f"'{new_name}' 항목이 추가되었습니다!")
            st.rerun()

    st.markdown("### 🗑️ 자산/부채 항목 삭제하기")
    if not st.session_state.assets.empty:
        asset_names = st.session_state.assets["항목명"].tolist()
        target_to_delete = st.selectbox("삭제할 항목 선택", asset_names)
        if st.button("🗑️ 선택한 항목 삭제", type="secondary"):
            st.session_state.assets = st.session_state.assets[st.session_state.assets["항목명"] != target_to_delete].reset_index(drop=True)
            save_assets(st.session_state.assets)
            st.success(f"'{target_to_delete}' 항목이 삭제되었습니다!")
            st.rerun()

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
                    mapped_rows = []
                    for _, r in raw_df.iterrows():
                        dt = pd.Timestamp.now().strftime("%Y-%m-%d") if date_col == "오늘 날짜로 일괄 적용" else str(r[date_col])[:10]
                        desc = str(r[desc_col])
                        raw_amt = str(r[amt_col])
                        clean_amt = int(''.join(filter(str.isdigit, raw_amt.replace('-', ''))) or 0)
                        
                        mapped_rows.append({
                            "날짜": dt,
                            "구분": default_type,
                            "카테고리": default_cat,
                            "내용": desc,
                            "금액": clean_amt
                        })
                    new_df = pd.DataFrame(mapped_rows)
                    st.session_state.transactions = pd.concat([st.session_state.transactions, new_df], ignore_index=True).reset_index(drop=True)
                    save_transactions(st.session_state.transactions)
                    st.success("내역이 장부에 성공적으로 반영되었습니다!")
                    st.rerun()
            except Exception as e:
                st.error(f"오류 발생: {e}")

    st.subheader("📋 전체 거래내역 장부")
    st.dataframe(st.session_state.transactions, use_container_width=True)

    if not st.session_state.transactions.empty:
        if st.button("🗑️ 모든 거래내역 초기화(삭제)", type="secondary"):
            st.session_state.transactions = pd.DataFrame(columns=["날짜", "구분", "카테고리", "내용", "금액"])
            save_transactions(st.session_state.transactions)
            st.success("거래내역이 초기화되었습니다.")
            st.rerun()

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
                    ai_response += f"\n\n✅ **({added_count}건의 내역이 거래내역 장부에 자동 반영되었습니다!)**"

        with st.chat_message("assistant"):
            st.markdown(ai_response)
        st.session_state.messages.append({"role": "assistant", "content": ai_response})
