import os
import json
import sqlite3
import datetime
import tempfile
import pandas as pd
import streamlit as st
import analysis  # analysis.py 모듈 임포트

# ==========================================
# [디렉토리 및 DB 설정]
# ==========================================
DB_PATH = "speechlog.db"
RECORDING_DIR = "recordings"

# 녹음 저장용 폴더 생성
if not os.path.exists(RECORDING_DIR):
    os.makedirs(RECORDING_DIR)

# SQLite DB 초기화 (설계안 6.3 기준: scripts, attempts)
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 1. 대본 테이블 (scripts)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS scripts (
        script_id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        content TEXT NOT NULL
    )
    """)
    
    # 2. 시도/기록 테이블 (attempts)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS attempts (
        attempt_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_name TEXT NOT NULL,
        script_title TEXT NOT NULL,
        script_content TEXT NOT NULL,
        audio_path TEXT NOT NULL,
        score REAL,
        syl_per_s REAL,
        pause_count INTEGER,
        pause_total_s REAL,
        target_time_s REAL,
        duration_s REAL,
        bad_syllables_json TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    conn.commit()
    conn.close()

init_db()

# ==========================================
# [Streamlit 기본 레이아웃]
# ==========================================
st.set_page_config(page_title="스피치로그 (SpeechLog)", layout="centered")
st.title("🎤 스피치로그 (SpeechLog)")

# 탭 구성: 1. 연습 & 분석 / 2. 내 기록
tab1, tab2 = st.tabs(["🎙️ 연습 & 분석", "📈 내 기록"])

# ==========================================
# TAB 1: 연습 & 분석 (기록 저장 및 목표시간 포함)
# ==========================================
with tab1:
    st.subheader("1. 사용자 정보 및 대본 선택")

    # (1) 이름 입력
    user_name = st.text_input("사용자 이름", placeholder="이름을 입력하세요 (예: 홍길동)")

    # (2) 대본 선택
    preset_scripts = {
        "선택 안함 (직접 입력)": "",
        "면접 대본 1": "안녕하십니까. 데이터사이언스학과 캡스톤디자인 6조 발표자입니다. 오늘 스피치로그 서비스를 소개하겠습니다.",
        "발표 대본 2": "한국어 낭독의 적정 속도는 초당 5음절에서 7음절 사이입니다. 또박또박 정확하게 발음하는 것이 중요합니다."
    }

    selected_option = st.selectbox("대본 선택", list(preset_scripts.keys()))

    if selected_option == "선택 안함 (직접 입력)":
        script_text = st.text_area("대본 직접 입력", placeholder="분석할 한글 대본 내용을 입력해 주세요.")
        script_title = "자유 입력 대본"
    else:
        script_text = st.text_area("대본 내용", value=preset_scripts[selected_option], height=100)
        script_title = selected_option

    # (3) 목표 시간 기능
    st.subheader("2. 목표 시간 설정 (선택)")
    target_time_s = st.number_input("목표 발표 시간 (초)", min_value=0.0, value=0.0, step=1.0, help="0초 설정 시 제한 없음")
    
    if target_time_s > 0 and script_text.strip():
        n_syl = analysis.count_syllables(script_text)
        required_cps = round(n_syl / target_time_s, 2) if target_time_s else 0
        st.info(f"💡 대본 전체({n_syl} 음절)를 {target_time_s}초 내에 맞추려면 **초당 약 {required_cps} 음절** 속도로 말해야 합니다.")

    # (4) 녹음 입력
    st.subheader("3. 녹음하기")
    audio_data = st.audio_input("마이크 버튼을 눌러 녹음을 진행해 주세요.")

    # (5) 분석 실행
    if st.button("🚀 분석하기", type="primary", use_container_width=True):
        if not user_name.strip():
            st.warning("⚠️ 이름을 입력해 주세요.")
            st.stop()
            
        if not script_text.strip():
            st.warning("⚠️ 대본을 입력해 주세요.")
            st.stop()
            
        if audio_data is None:
            st.warning("⚠️ 녹음된 음성이 없습니다. 녹음을 진행해 주세요.")
            st.stop()

        # 분석용 임시 파일 생성
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_file:
            tmp_file.write(audio_data.read())
            tmp_wav_path = tmp_file.name

        try:
            with st.spinner("🔄 음성 및 발음 분석 중입니다..."):
                result = analysis.analyze(tmp_wav_path, script_text)

            if "error" in result:
                st.error(f"⚠️ {result['error']}")
                st.stop()

            # 녹음 파일 고유파일명으로 recordings/ 폴더에 실제 저장
            timestamp_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            saved_audio_name = f"{user_name}_{timestamp_str}.wav"
            saved_audio_path = os.path.join(RECORDING_DIR, saved_audio_name)
            
            with open(saved_audio_path, "wb") as f:
                f.write(audio_data.getvalue())

            # DB 저장 (attempts 테이블)
            bad_json = json.dumps(result.get("bad_syllables", []))
            
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO attempts (
                user_name, script_title, script_content, audio_path,
                score, syl_per_s, pause_count, pause_total_s,
                target_time_s, duration_s, bad_syllables_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                user_name, script_title, script_text, saved_audio_path,
                result.get("score"), result.get("syl_per_s"), result.get("pause_count"),
                result.get("pause_total_s"), target_time_s, result.get("duration_s"), bad_json
            ))
            conn.commit()
            conn.close()

            st.success("✅ 분석이 완료되고 기록에 자동 저장되었습니다!")
            st.divider()

            # --- 결과 화면 ---
            st.header(f"📊 {user_name} 님의 분석 결과")

            # 핵심 지표
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("발음 점수", f"{result.get('score')}점")
            with col2:
                st.metric("말하기 속도", f"{result.get('syl_per_s')} 음절/초")
            with col3:
                st.metric("쉼 횟수", f"{result.get('pause_count')} 회")

            # 목표 시간 결과 안내
            actual_dur = result.get("duration_s", 0)
            if target_time_s > 0:
                diff = round(actual_dur - target_time_s, 1)
                if diff > 0:
                    st.warning(f"⏱️ **목표 시간 결과:** 목표({target_time_s}초)보다 **{diff}초 초과**되었습니다.")
                elif diff < 0:
                    st.info(f"⏱️ **목표 시간 결과:** 목표({target_time_s}초)보다 **{abs(diff)}초 단축**되었습니다.")
                else:
                    st.success(f"⏱️ **목표 시간 결과:** 목표 시간({target_time_s}초)에 정확히 도달했습니다!")

            # 대본 하이라이트
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

            # 음량 그래프
            st.subheader("🔊 음량(소리 크기) 변화 그래프")
            st.line_chart(result.get('db', []))

        finally:
            if os.path.exists(tmp_wav_path):
                os.remove(tmp_wav_path)


# ==========================================
# TAB 2: 내 기록 (회차 비교 및 시각화)
# ==========================================
with tab2:
    st.header("📈 회차별 스피치 기록 비교")

    conn = sqlite3.connect(DB_PATH)
    
    # 등록된 사용자 및 대본 목록 불러오기
    df_users = pd.read_sql_query("SELECT DISTINCT user_name FROM attempts", conn)
    
    if df_users.empty:
        st.info("아직 저장된 연습 기록이 없습니다. [연습 & 분석] 탭에서 연습을 먼저 진행해 주세요.")
        conn.close()
    else:
        user_list = df_users['user_name'].tolist()
        search_user = st.selectbox("사용자 선택", user_list)

        df_scripts = pd.read_sql_query(
            "SELECT DISTINCT script_title FROM attempts WHERE user_name = ?", 
            conn, params=(search_user,)
        )
        script_list = df_scripts['script_title'].tolist()
        search_script = st.selectbox("대본 선택", script_list)

        # 해당 유저 + 대본의 전체 회차 기록 가져오기
        df_attempts = pd.read_sql_query("""
            SELECT attempt_id, score, syl_per_s, duration_s, target_time_s, audio_path, script_content, bad_syllables_json, created_at 
            FROM attempts 
            WHERE user_name = ? AND script_title = ?
            ORDER BY attempt_id ASC
        """, conn, params=(search_user, search_script))

        conn.close()

        if not df_attempts.empty:
            df_attempts['회차'] = range(1, len(df_attempts) + 1)

            # 1. 직전 회차와의 차이 문장 안내
            if len(df_attempts) >= 2:
                last_score = df_attempts.iloc[-1]['score']
                prev_score = df_attempts.iloc[-2]['score']
                score_diff = round(last_score - prev_score, 1)

                last_speed = df_attempts.iloc[-1]['syl_per_s']
                prev_speed = df_attempts.iloc[-2]['syl_per_s']
                speed_diff = round(last_speed - prev_speed, 1)

                score_str = f"+{score_diff}점 상승" if score_diff >= 0 else f"{abs(score_diff)}점 하락"
                speed_str = f"{speed_diff}음절 빨라짐" if speed_diff >= 0 else f"{abs(speed_diff)}음절 느려짐"

                st.success(f"🗣️ 지난 회차보다 **발음 점수 {score_str}**, **속도 {speed_str}**했습니다.")

            # 2. 발음 점수 & 속도 꺾은선 그래프
            st.subheader("📊 발음 점수 및 속도 변화")

            col_chart1, col_chart2 = st.columns(2)
            with col_chart1:
                st.markdown("**발음 점수 추이**")
                st.line_chart(df_attempts.set_index('회차')['score'])

            with col_chart2:
                st.markdown("**말하기 속도 (음절/초) 추이**")
                # 기준선 (5~7 음절/초) 안내
                st.line_chart(df_attempts.set_index('회차')['syl_per_s'])
                st.caption("💡 *적정 속도 기준: 5.0 ~ 7.0 음절/초*")

            st.divider()

            # 3. 회차 선택 및 상세 재확인
            st.subheader("🔍 회차별 상세 다시보기")
            
            selected_attempt_id = st.selectbox(
                "상세보기할 회차 선택",
                df_attempts['attempt_id'].tolist(),
                format_func=lambda x: f"{df_attempts[df_attempts['attempt_id'] == x]['회차'].values[0]}회차 ({df_attempts[df_attempts['attempt_id'] == x]['created_at'].values[0]})"
            )

            row = df_attempts[df_attempts['attempt_id'] == selected_attempt_id].iloc[0]

            col_detail1, col_detail2 = st.columns(2)
            with col_detail1:
                st.write(f"**발음 점수:** {row['score']}점")
                st.write(f"**말하기 속도:** {row['syl_per_s']} 음절/초")
                st.write(f"**녹음 길 이:** {row['duration_s']}초")
            with col_detail2:
                if row['target_time_s'] > 0:
                    diff_s = round(row['duration_s'] - row['target_time_s'], 1)
                    st.write(f"**목표 시간:** {row['target_time_s']}초 (차이: {diff_s}초)")

            # 오디오 다시듣기
            if os.path.exists(row['audio_path']):
                st.audio(row['audio_path'])
            else:
                st.caption("⚠️ 녹음 파일 경로를 찾을 수 없습니다.")

            # 틀린 음절 복원 및 대본 표시
            bad_indices = json.loads(row['bad_syllables_json']) if row['bad_syllables_json'] else []
            marked_data = analysis.mark_script(row['script_content'], bad_indices)

            highlighted_script = ""
            for char, is_bad in marked_data:
                if is_bad:
                    highlighted_script += f"<span style='color: red; font-weight: bold; text-decoration: underline;'>{char}</span>"
                else:
                    highlighted_script += f"<span style='color: black;'>{char}</span>"

            st.markdown(
                f"<div style='background-color: #f9f9f9; padding: 15px; border-radius: 8px;'>{highlighted_script}</div>",
                unsafe_allow_html=True
            )