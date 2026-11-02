import os
import re
import json
import datetime
import tempfile
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from pacer import pacemaker_html
import analysis
import db  # db.py 모듈 활용
import charts  # charts.py 모듈 활용
from messages import score_message, speed_message, pause_message, target_gap_message, NOTES

# 앱 시작 시 DB 초기화 (테이블 생성)
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

# 탭 구성
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
                    content_val = str(r[cols[2]]).strip()
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

    # 페이스메이커 기능
    if target_time_s > 0 and script_text.strip():
        with st.expander("페이스메이커로 연습하기"):
            st.info("💡 **사용 순서 안내:** 페이스메이커 시작 → 동시에 아래 녹음 시작")
            try:
                components.html(pacemaker_html(script_text, target_time_s), height=320, scrolling=True)
            except ValueError as e:
                st.warning(str(e))
    
    if target_time_s > 0 and script_text.strip():
        if hasattr(analysis, "speed_for_target"):
            required_cps = analysis.speed_for_target(script_text, target_time_s)
        else:
            n_syl = analysis.count_syllables(script_text)
            required_cps = round(n_syl / target_time_s, 2) if target_time_s else 0
        st.info(f"💡 대본 전체를 {target_time_s}초 내에 맞추려면 **초당 약 {required_cps} 음절** 속도로 말해야 합니다.")

    st.subheader("3. 녹음하기 / 파일 올리기")
    input_type = st.radio("입력 방식 선택", ["🎤 직접 녹음하기", "📁 음성 파일 업로드하기"], horizontal=True)

    if input_type == "🎤 직접 녹음하기":
        audio_data = st.audio_input("마이크 버튼을 눌러 녹음을 진행해 주세요.")
    else:
        audio_data = st.file_uploader("음성 파일을 선택해 주세요 (wav, m4a, mp3)", type=["wav", "m4a", "mp3"])

    # 🚀 분석하기 버튼 클릭 시
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

            # 녹음 파일 저장
            os.makedirs("recordings", exist_ok=True)
            timestamp_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            saved_audio_name = f"{user_case}_{timestamp_str}.wav"
            saved_audio_path = os.path.join("recordings", saved_audio_name)
            
            with open(saved_audio_path, "wb") as f:
                f.write(audio_data.getvalue())

            # DB 저장
            try:
                db.save_attempt(user_case, script_title, result, saved_audio_path, target_sec=target_time_s)
            except TypeError:
                db.save_attempt(user_case, script_title, result, saved_audio_path)

            # 세션에 결과 저장
            st.session_state["result"] = result
            st.session_state["user_case"] = user_case
            st.session_state["script_text"] = script_text
            st.session_state["target_time_s"] = target_time_s

            st.success("✅ 분석 완료 및 기록 저장 성공!")

        finally:
            if os.path.exists(tmp_wav_path):
                os.remove(tmp_wav_path)

    # 분석 결과 출력 영역
    if "result" in st.session_state:
        res = st.session_state["result"]
        ucase = st.session_state.get("user_case", user_case)
        stext = st.session_state.get("script_text", script_text)
        ttime = st.session_state.get("target_time_s", target_time_s)

        st.divider()
        st.header(f"📊 {ucase} 의 분석 결과")

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("발음 점수", f"{res.get('score')}점")
        with col2:
            st.metric("말하기 속도", f"{res.get('syl_per_s')} 음절/초")
        with col3:
            st.metric("쉼 횟수", f"{res.get('pause_count')} 회")

        st.write(score_message(res.get("score")))
        st.write(speed_message(res.get("syl_per_s")))
        st.write(pause_message(res.get("pause_count"), res.get("pause_total_s")))

        # ★ C5-6: 팀 평균 비교 영역 추가 ★
        ref_path = "data/reference.json" if os.path.exists("data/reference.json") else "reference.json"
        if os.path.exists(ref_path):
            try:
                with open(ref_path, "r", encoding="utf-8") as ref_f:
                    ref = json.load(ref_f)
                
                st.subheader("평균과 비교")
                
                # 발음 점수 및 속도 키(Key) 값 예외 안전 처리
                my_score = res.get("score", 0)
                mean_score = ref.get("score_mean", 0)
                
                my_rate = res.get("syl_per_s", res.get("artic_rate", 0))
                mean_rate = ref.get("rate_mean", ref.get("artic_rate_mean", 0))

                st.write(f"내 발음 점수 {my_score}점 / 평균 {mean_score:.0f}점")
                st.write(f"내 속도 {my_rate:.1f} 음절/초 / 평균 {mean_rate:.1f}, 일반 5~7")
                st.caption("※ 팀 3명이 바르게 읽은 녹음 기준입니다. 목소리 크기는 마이크마다 달라 비교하지 않습니다.")
            except Exception as e:
                pass

        if ttime > 0:
            gap_msg = target_gap_message(res.get("duration_s", 0), ttime)
            if "초과" in gap_msg:
                st.warning(gap_msg)
            elif "단축" in gap_msg:
                st.info(gap_msg)
            else:
                st.success(gap_msg)

        # 3줄 대본 비교 문구
        rec = res.get("recognized", {})
        main_text = rec.get("kresnik", "") if isinstance(rec, dict) else ""
        if main_text:
            st.markdown("**대본:** " + stext)
            st.markdown("**이렇게 들렸어요:** " + main_text)
            if "pron" in res:
                st.markdown("**발음 기준 대본:** " + str(res["pron"]))
            st.write("")

        st.subheader("📝 대본 발음점검")
        highlighted_script = ""
        for char, is_bad in res.get('marked', []):
            if is_bad:
                highlighted_script += f"<span style='color: red; font-weight: bold; text-decoration: underline;'>{char}</span>"
            else:
                highlighted_script += f"<span style='color: black;'>{char}</span>"

        st.markdown(
            f"<div style='background-color: #f9f9f9; padding: 15px; border-radius: 8px;'>{highlighted_script}</div>",
            unsafe_allow_html=True
        )

        st.subheader("🔊 음량(소리 크기) 변화 그래프")
        try:
            st.altair_chart(
                charts.volume_chart(res.get("db", []), res.get("pauses", [])), 
                use_container_width=True
            )
        except Exception:
            st.line_chart(res.get("db", []))

        st.divider()
        for note in NOTES:
            st.caption(note)

        # "다시 연습" 버튼
        st.write("")
        if st.button("🔄 다시 연습"):
            st.session_state.pop("result", None)
            st.session_state.pop("user_case", None)
            st.session_state.pop("script_text", None)
            st.session_state.pop("target_time_s", None)
            st.rerun()

# ==========================================
# TAB 2: 내 기록
# ==========================================
with tab2:
    st.header("📈 내 기록 (회차별 스피치 분석)")

    user_case_search = st.text_input("조회할 스피치 종류 입력", key="search_user_input")

    if not user_case_search.strip():
        st.info("💡 스피치 종류를 입력하시면 저장된 연습 기록을 불러옵니다.")
    else:
        scripts_list = db.list_scripts(user_case_search)
        
        if not scripts_list:
            st.warning("아직 연습 기록이 없어요")
        else:
            selected_script_item = st.selectbox(
                "대본 선택",
                scripts_list,
                format_func=lambda item: item.get("text", str(item)) if isinstance(item, dict) else str(item)
            )
            
            if isinstance(selected_script_item, dict):
                target_script_id = selected_script_item.get("script_id")
            else:
                target_script_id = selected_script_item

            rows = db.get_attempts(user_case_search, target_script_id)
            
            if not rows:
                st.warning("아직 연습 기록이 없어요")
            else:
                df_attempts = pd.DataFrame(rows)
                
                if "round" not in df_attempts.columns:
                    df_attempts["round"] = range(1, len(df_attempts) + 1)

                if len(rows) >= 2:
                    try:
                        st.success(db.change_sentence(rows[-2], rows[-1]))
                    except Exception:
                        pass

                st.subheader("📊 회차별 변화 추이")
                col_c1, col_c2 = st.columns(2)
                
                with col_c1:
                    st.markdown("**발음 점수**")
                    try:
                        chart_score = charts.history_chart(df_attempts, x="round", y="score", y_title="발음 점수")
                        st.altair_chart(chart_score, use_container_width=True)
                    except Exception:
                        score_col = "score" if "score" in df_attempts.columns else df_attempts.columns[0]
                        st.line_chart(df_attempts.set_index("round")[[score_col]])
                
                with col_c2:
                    st.markdown("**말하기 속도 (음절/초)**")
                    speed_col = "syl_per_s" if "syl_per_s" in df_attempts.columns else ("speed" if "speed" in df_attempts.columns else None)
                    if speed_col:
                        try:
                            chart_speed = charts.history_chart(df_attempts, x="round", y=speed_col, y_title="말하기 속도")
                            st.altair_chart(chart_speed, use_container_width=True)
                        except Exception:
                            st.line_chart(df_attempts.set_index("round")[[speed_col]])

                st.divider()

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