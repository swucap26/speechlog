"""스피치로그 그래프 모듈 (charts.py): 축 이름과 뜻이 보이는 그래프를 만들어요.
app.py에서:
    import charts
    st.altair_chart(charts.volume_chart(result["db"], result["pauses"]), use_container_width=True)
    st.altair_chart(charts.history_chart(df, "회차", "score", "발음 점수 (점)", band=None), use_container_width=True)
altair는 streamlit을 설치하면 같이 설치돼요. (이 파일의 altair 부분은 시험 전, 자료 가공 부분은 시험함)
"""
import pandas as pd

FRAME_S = 0.1          # analysis.py의 FRAME_S와 같아야 해요
RANGE_DB = 60          # 가장 큰 소리보다 60dB 작은 소리를 0으로 봐요


def volume_frame(db, pauses, frame_s=FRAME_S):
    """db(0.1초마다 dBFS, 음수) → 시간(초)과 '상대 크기(0~100)' 표. 100 = 이 녹음에서 가장 큰 소리."""
    if not db:
        return pd.DataFrame({"시간(초)": [], "목소리 크기": []}), pd.DataFrame({"시작": [], "끝": []})
    peak = max(db)
    level = [max(0.0, min(100.0, (d - (peak - RANGE_DB)) / RANGE_DB * 100)) for d in db]
    df = pd.DataFrame({"시간(초)": [round(i * frame_s, 2) for i in range(len(db))], "목소리 크기": [round(x, 1) for x in level]})
    pz = pd.DataFrame({"시작": [p["start"] for p in pauses], "끝": [p["end"] for p in pauses]})
    return df, pz


def volume_chart(db, pauses, frame_s=FRAME_S):
    import altair as alt
    df, pz = volume_frame(db, pauses, frame_s)
    line = alt.Chart(df).mark_line(color="#d6336c").encode(
        x=alt.X("시간(초):Q", title="녹음 시간 (초)"),
        y=alt.Y("목소리 크기:Q", title="목소리 크기 (이 녹음에서 가장 큰 소리 = 100)", scale=alt.Scale(domain=[0, 100])),
        tooltip=["시간(초)", "목소리 크기"])
    if len(pz):
        rects = alt.Chart(pz).mark_rect(color="#4dabf7", opacity=0.25).encode(x="시작:Q", x2="끝:Q")
        chart = rects + line
    else:
        chart = line
    return chart.properties(height=260, title="시간에 따른 목소리 크기 (파란 칸 = 쉼)")


def history_chart(df, x, y, y_title, band=None, title=None):
    """회차별 꺾은선. band=(낮음, 높음)이면 적정 범위를 연한 띠로 보여 줘요 (예: 속도 5~7)."""
    import altair as alt
    base = alt.Chart(df).mark_line(point=True, color="#d6336c").encode(
        x=alt.X(f"{x}:O", title="연습 회차 (몇 번째 연습인지)"),
        y=alt.Y(f"{y}:Q", title=y_title),
        tooltip=[x, y])
    if band:
        b = alt.Chart(pd.DataFrame({"lo": [band[0]], "hi": [band[1]]})).mark_rect(color="#69db7c", opacity=0.25).encode(
            y="lo:Q", y2="hi:Q")
        base = b + base
    return base.properties(height=240, title=title or y_title)
