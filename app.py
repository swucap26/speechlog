import os
import re
import shutil
import datetime
import tempfile
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from pacer import pacemaker_html

import analysis
import db  # B학생이 제공한 db.py 모듈 임포트
from messages import score_message, speed_message, pause_message, NOTES

# 1) 앱 시작 시 DB 초기화 (테이블 생성 등)
db.init_db()

# 모델 사전 워밍업
@st.cache_resource
def warm_up():
    analysis.load_models()
    return True

warm_up()

# ==========================================
# 레이아웃 및 탭 구성
# ==========================================
st.set_page_config(page_title="스피치로그 (SpeechLog)", layout="centered")
st.title("🎤 스피치로그 (SpeechLog)")

# 4) 탭 구성
tab1, tab2 = st.tabs(["🎙️ 연습", "📈 내 기록"])

# ==========================================
# TAB 1: 연습
# ==========================================
with tab1:
    st.subheader("1. 사용자 정보 및 대본 선택")

    user_case = st.text_input("스피치 종류", placeholder="종류를 입력하세요 (예: 00강의, 00회사 면접)")

    # scripts.csv에서 대본 목록 읽어오기
    script_options = {"직접 입력": ""}
    if os.path.exists("scripts.csv"):
        df_csv = None
        for enc in ["utf-8-sig", "utf-8", "cp949", "euc-kr"]:
            try:
                df_csv = pd.read_csv("scripts.csv", encoding=enc)
                break
            except Exception:
                continue

        if df_csv is not None:
            cols = list(df_csv.columns)
            if len(cols) >= 3:
                for _, r in df_csv.iterrows():
                    id_val = str(r[cols[0]]).strip()
                    title_val = str(r[cols[1]]).strip()
                    content_val = str(r[cols[2]]).strip()
                    display_label = f"{id_val}. {title_val}" if id_val.isdigit() else title_val
                    if content_val and content_val != "nan":
                        script_options[display_label] = content_val
            elif len(cols) == 2:
                for _, r in df_csv.iterrows():
                    title_val = str(r[cols[0]]).strip()
                    content_val = str(r[cols[1]]).strip()
                    if title_val and content_val and title_val != "nan":
                        script_options[title_val] = content_val

    if len(script_options) == 1:
        script_options["면접 대본 1"] = "안녕하십니까. 데이터사이언스학과 캡스톤디자인 6조 발표자입니다. 오늘 스피치로그 서비스를 소개하겠습니다."
        script_options["발표 대본 2"] = "한국어 낭독의 적정 속도는 초당 5음절에서 7음절 사이입니다. 또박또박 정확하게 발음하는 것이 중요합니다."

    selected_option = st.selectbox("대본 선택", list(script_options.keys()))

    if selected_option == "직접 입력":
        script_text = st.text_area("대본 직접 입력", placeholder="분석할 한글 대본 내용을 입력해 주세요.")
        script_title = "자유 입력 대본"
    else:
        script_text = st.text_area("대본 내용", value=script_options[selected_option], height=100)
        script_title = selected_option

    st.subheader("2. 목표 시간 설정 (선택)")
    target_time_s = st.number_input("목표 발표 시간 (초)", min_value=0.0, value=0.0, step=1.0, help="0초 설정 시 제한 없음")

    # app.py 의 목표 시간 입력(target = st.number_input(...)) 바로 아래에 붙여넣는 코드
    if target_time_s > 0 and script_text.strip():
        with st.expander("페이스메이커로 연습하기"):
            try:
                components.html(pacemaker_html(script_text, target_time_s), height=320, scrolling=True)
            except ValueError as e:
                st.warning(str(e))
    
    if target_time_s > 0 and script_text.strip():
        n_syl = analysis.count_syllables(script_text)
        required_cps = round(n_syl / target_time_s, 2) if target_time_s else 0
        st.info(f"💡 대본 전체({n_syl} 음절)를 {target_time_s}초 내에 맞추려면 **초당 약 {required_cps} 음절** 속도로 말해야 합니다.")

    st.subheader("3. 녹음하기 / 파일 올리기")
    input_type = st.radio("입력 방식 선택", ["🎤 직접 녹음하기", "📁 음성 파일 업로드하기"], horizontal=True)

    if input_type == "🎤 직접 녹음하기":
        audio_data = st.audio_input("마이크 버튼을 눌러 녹음을 진행해 주세요.")
    else:
        audio_data = st.file_uploader("음성 파일을 선택해 주세요 (wav, m4a, mp3)", type=["wav", "m4a", "mp3"])

    if st.button("🚀 분석하기", type="primary", use_container_width=True):
        if not user_case.strip():
            st.warning("⚠️ 이름을 입력해 주세요.")
            st.stop()
            
        if not script_text.strip() or len(re.findall(r"[가-힣]", script_text)) == 0:
            st.warning("⚠️ 한글 대본을 입력해 주세요.")
            st.stop()
            
        if audio_data is None:
            st.warning("⚠️ 녹음된 음성이나 선택된 파일이 없습니다.")
            st.stop()

        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_file:
            tmp_file.write(audio_data.read())
            tmp_wav_path = tmp_file.name

        try:
            with st.spinner("🔄 음성 및 발음 분석 중입니다..."):
                result = analysis.analyze(tmp_wav_path, script_text)

            if "error" in result:
                st.error(f"⚠️ {result['error']}")
                st.stop()

            # 2) recordings/ 폴더 생성 및 파일 복사 저장 (recordings/이름_시간.wav)
            os.makedirs("recordings", exist_ok=True)
            timestamp_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            saved_audio_name = f"{user_case}_{timestamp_str}.wav"
            saved_audio_path = os.path.join("recordings", saved_audio_name)
            
            with open(saved_audio_path, "wb") as f:
                f.write(audio_data.getvalue())

            # 3) 결과가 나온 직후 db.save_attempt(...) 호출로 DB 저장
            db.save_attempt(user_case, script_title, result, saved_audio_path)

            st.success("✅ 분석 완료 및 기록 저장 성공!")
            st.divider()

            # 결과 화면
            st.header(f"📊 {user_case} 의 분석 결과")

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("발음 점수", f"{result.get('score')}점")
            with col2:
                st.metric("말하기 속도", f"{result.get('syl_per_s')} 음절/초")
            with col3:
                st.metric("쉼 횟수", f"{result.get('pause_count')} 회")

            st.write(score_message(result.get("score")))
            st.write(speed_message(result.get("syl_per_s")))
            st.write(pause_message(result.get("pause_count"), result.get("pause_total_s")))

            actual_dur = result.get("duration_s", 0)
            if target_time_s > 0:
                diff = round(actual_dur - target_time_s, 1)
                if diff > 0:
                    st.warning(f"⏱️ **목표 시간 결과:** 목표({target_time_s}초)보다 **{diff}초 초과**되었습니다.")
                elif diff < 0:
                    st.info(f"⏱️ **목표 시간 결과:** 목표({target_time_s}초)보다 **{abs(diff)}초 단축**되었습니다.")
                else:
                    st.success(f"⏱️ **목표 시간 결과:** 목표 시간({target_time_s}초)에 정확히 도달했습니다!")

            st.subheader("📝 대본 발음점검")
            highlighted_script = ""
            for char, is_bad in result.get('marked', []):
                if is_bad:
                    highlighted_script += f"<span style='color: red; font-weight: bold; text-decoration: underline;'>{char}</span>"
                else:
                    highlighted_script += f"<span style='color: black;'>{char}</span>"

            st.markdown(
                f"<div style='background-color: #f9f9f9; padding: 15px; border-radius: 8px;'>{highlighted_script}</div>",
                unsafe_allow_html=True
            )

            st.subheader("🔊 음량(소리 크기) 변화 그래프")
            st.line_chart(result.get('db', []))

            st.divider()
            for note in NOTES:
                st.caption(note)

        finally:
            if os.path.exists(tmp_wav_path):
                os.remove(tmp_wav_path)

# ==========================================
# TAB 2: 내 기록
# ==========================================
with tab2:
    st.header("📈 내 기록 (회차별 스피치 분석)")

    user_case_search = st.text_input("조회할 스피치 종류 입력", key="search_user_input")

    if not user_case_search.strip():
        st.info("💡 스피치 종류를 입력하시면 저장된 연습 기록을 불러옵니다.")
    else:
        # 1) B학생의 db.list_scripts(name) 호출 -> 딕셔너리 리스트가 반환됨
        scripts_list = db.list_scripts(user_case_search)
        
        if not scripts_list:
            st.warning("아직 연습 기록이 없어요")
        else:
            # 드롭다운에 딕셔너리 대신 'text' 글자만 예쁘게 표시되도록 format_func 설정
            selected_script_item = st.selectbox(
                "대본 선택",
                scripts_list,
                format_func=lambda item: item.get("text", str(item)) if isinstance(item, dict) else str(item)
            )
            
            # 2) 딕셔너리에서 script_id 숫자 값 추출 (또는 문자열인 경우 그대로 사용)
            if isinstance(selected_script_item, dict):
                target_script_id = selected_script_item.get("script_id")
            else:
                target_script_id = selected_script_item

            # 3) 추출한 script_id를 get_attempts에 넘겨줌
            rows = db.get_attempts(user_case_search, target_script_id)
            
            if not rows:
                st.warning("아직 연습 기록이 없어요")
            else:
                # 4) pandas DataFrame 변환 및 회차(round) 부여
                df_attempts = pd.DataFrame(rows)
                
                if "round" not in df_attempts.columns:
                    df_attempts["round"] = range(1, len(df_attempts) + 1)

                # 5) 2회차 이상이면 직전 회차 대비 변화 문구 출력 (change_sentence)
                if len(rows) >= 2:
                    try:
                        st.success(db.change_sentence(rows[-2], rows[-1]))
                    except Exception:
                        pass

                st.subheader("📊 회차별 변화 추이")
                col_c1, col_c2 = st.columns(2)
                
                with col_c1:
                    st.markdown("**발음 점수**")
                    score_col = "score" if "score" in df_attempts.columns else df_attempts.columns[0]
                    st.line_chart(df_attempts.set_index("round")[[score_col]])
                
                with col_c2:
                    st.markdown("**말하기 속도 (음절/초)**")
                    speed_col = "syl_per_s" if "syl_per_s" in df_attempts.columns else ("speed" if "speed" in df_attempts.columns else None)
                    if speed_col:
                        st.line_chart(df_attempts.set_index("round")[[speed_col]])

                st.divider()

                # 6) 회차별 상세보기 및 녹음 다시듣기
                st.subheader("🔍 회차별 상세 보기 및 다시 듣기")
                
                attempt_labels = [f"{r.get('round', i+1)}회차 ({r.get('created_at', '')})" for i, r in enumerate(rows)]
                selected_idx = st.selectbox("회차 선택", range(len(rows)), format_func=lambda i: attempt_labels[i])
                
                selected_row = rows[selected_idx]
                
                score_val = selected_row.get("score", 0)
                speed_val = selected_row.get("syl_per_s", selected_row.get("speed", 0))
                st.write(f"**선택 회차 발음 점수:** {score_val}점 / **속도:** {speed_val} 음절/초")

                audio_path_val = selected_row.get("audio_path", selected_row.get("audio", ""))
                if audio_path_val and os.path.exists(audio_path_val):
                    st.audio(audio_path_val)
                else:
                    st.caption("🔊 녹음 파일 경로를 찾을 수 없거나 아직 저장되지 않았습니다.")