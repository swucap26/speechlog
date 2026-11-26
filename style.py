
# 파일: style.py
# 역할: 화면 전체의 색, 카드, 알약 탭, 칩, 버튼 모양을 한곳에서 정함

import streamlit as st

GRAD = "linear-gradient(135deg, #D963FF 0%, #9141FB 55%, #5A2CFF 100%)"

_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700&display=swap');

/* ----------------------------------------------------
   전체 기본 스타일
---------------------------------------------------- */

html, body, .stApp, .stApp p, .stApp label,
.stApp input, .stApp textarea, .stApp button {
    font-family: 'Noto Sans KR', sans-serif;
}

.stApp {
    background: #F3F1F9;
    color: #1A1A2E;
}

.block-container {
    max-width: 640px;
    padding-top: 2rem;
}

h1 {
    font-size: 1.5rem !important;
    font-weight: 700 !important;
}

h2, h3 {
    font-size: 1.05rem !important;
    font-weight: 700 !important;
}


/* ----------------------------------------------------
   [알약 탭] Streamlit 1.59.0 이상 전용
   - 두 탭 50:50 분할
   - 선택된 탭 배경 꽉 채우기
   - 기본 밑줄 및 선택 표시선 완전 제거
---------------------------------------------------- */

/* 전체 알약 영역 */
[data-testid="stTabs"] [role="tablist"] {
    display: flex !important;
    flex-direction: row !important;
    justify-content: stretch !important;
    align-items: stretch !important;

    width: 100% !important;
    gap: 0 !important;
    padding: 0 !important;

    background: #FFFFFF !important;
    border: 1px solid #E7E2F3 !important;
    border-radius: 999px !important;

    box-sizing: border-box !important;
    overflow: hidden !important;

    /* Streamlit 기본 밑줄 제거 */
    border-bottom: none !important;
}

/* 탭 목록의 기본 밑줄 제거 */
[data-testid="stTabs"] [role="tablist"]::after,
[data-testid="stTabs"] [role="tablist"]::before {
    display: none !important;
    content: none !important;
    background: transparent !important;
    height: 0 !important;
    border: none !important;
}

/* 개별 탭 버튼 */
[data-testid="stTabs"] [data-testid="stTab"] {
    flex: 1 1 0% !important;
    flex-grow: 1 !important;
    flex-shrink: 1 !important;
    flex-basis: 0% !important;

    width: 0 !important;
    min-width: 0 !important;
    max-width: none !important;

    display: flex !important;
    justify-content: center !important;
    align-items: center !important;

    margin: 0 !important;
    padding: 13px 0 !important;

    border: none !important;
    border-bottom: none !important;
    border-radius: 999px !important;

    background: transparent !important;
    box-shadow: none !important;
    outline: none !important;

    box-sizing: border-box !important;
}

/* 탭 내부 텍스트 */
[data-testid="stTabs"] [data-testid="stTab"] p {
    font-family: 'Noto Sans KR', sans-serif !important;
    font-size: 1.15rem !important;
    font-weight: 700 !important;
    color: #7A7891 !important;
    margin: 0 !important;
    text-align: center !important;
    line-height: 1.2 !important;
}

/* 선택된 탭 배경 */
[data-testid="stTabs"] [data-testid="stTab"][aria-selected="true"],
[data-testid="stTabs"] [data-testid="stTab"][data-selected] {
    background: __GRAD__ !important;
    border: none !important;
    border-bottom: none !important;
    box-shadow: none !important;
}

/* 선택된 탭 텍스트 */
[data-testid="stTabs"] [data-testid="stTab"][aria-selected="true"] p,
[data-testid="stTabs"] [data-testid="stTab"][data-selected] p {
    color: #FFFFFF !important;
}

/* 핵심: Streamlit 1.59.0 React Aria 선택 표시선 제거 */
[data-testid="stTabs"] .react-aria-SelectionIndicator {
    display: none !important;
    visibility: hidden !important;
    opacity: 0 !important;
    height: 0 !important;
    width: 0 !important;
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
}

/* 탭 자체에 생성되는 가상 밑줄 제거 */
[data-testid="stTabs"] [data-testid="stTab"]::before,
[data-testid="stTabs"] [data-testid="stTab"]::after {
    display: none !important;
    content: none !important;
    border: none !important;
    box-shadow: none !important;
}

/* 탭 내부 하이라이트 및 테두리 제거 */
[data-testid="stTabs"] [data-testid="stTabHighlight"],
[data-testid="stTabs"] [data-testid="stTabBorder"],
[data-testid="stTabs"] [data-baseweb="tab-highlight"],
[data-testid="stTabs"] [data-baseweb="tab-border"] {
    display: none !important;
    border: none !important;
    box-shadow: none !important;
}


/* ----------------------------------------------------
   카드 래퍼
---------------------------------------------------- */

[class*="st-key-card_"] {
    background: #FFFFFF;
    border: 1px solid #E7E2F3;
    border-radius: 20px;
    padding: 18px 18px 8px;
    margin-bottom: 12px;
}


/* ----------------------------------------------------
   입력칸
---------------------------------------------------- */

.stTextInput input,
.stTextArea textarea,
.stNumberInput input {
    background: #F1EAFE !important;
    border: 0 !important;
    border-radius: 12px !important;
}

[data-baseweb="select"] > div {
    background: #F1EAFE !important;
    border: 0 !important;
    border-radius: 12px !important;
}


/* ----------------------------------------------------
   버튼
---------------------------------------------------- */

.stButton > button {
    border-radius: 14px;
    border: 0;
    background: #F1EAFE;
    color: #7B3FF2;
    font-weight: 600;
    padding: 0.7rem 1rem;
}

button[kind="primary"],
[data-testid="stBaseButton-primary"] {
    background: __GRAD__ !important;
    color: #FFFFFF !important;
    font-size: 1.05rem;
    padding: 0.9rem 1rem;
}


/* ----------------------------------------------------
   요약 카드 및 안내 상자
---------------------------------------------------- */

[data-testid="stMetric"] {
    background: #FFFFFF;
    border: 1px solid #E7E2F3;
    border-radius: 16px;
    padding: 12px 14px;
}

[data-testid="stMetricValue"] {
    font-size: 1.6rem;
}

[data-testid="stAlert"] {
    background: #F1EAFE;
    border-radius: 12px;
}


/* ----------------------------------------------------
   칩 및 보라색 / 파란색 콜아웃
---------------------------------------------------- */

.chip {
    display: inline-block;
    font-size: 12px;
    padding: 3px 10px;
    margin: 0 6px 6px 0;
    border-radius: 999px;
    background: #F1EAFE;
    color: #7B3FF2;
    font-weight: 500;
}

.chip.bad {
    background: #FDECEF;
    color: #E5384F;
}

.chip.warn {
    background: #FDF1DC;
    color: #C77A0A;
}

.chip.ok {
    background: #E3F6EE;
    color: #1E9E6A;
}

.muted {
    color: #7A7891;
    font-size: 13px;
    margin-top: 4px;
}

.callout {
    background: #F1EAFE;
    border-radius: 12px;
    padding: 10px 12px;
    font-size: 13px;
    color: #1A1A2E;
    margin-top: 8px;
    margin-bottom: 8px;
}

</style>
"""


def apply_style():
    st.markdown(
        _CSS.replace("__GRAD__", GRAD),
        unsafe_allow_html=True
    )


def chips(*items):
    html = "".join(
        f'<span class="chip {kind}">{text}</span>'
        for text, kind in items
    )
    st.markdown(html, unsafe_allow_html=True)


def callout(text):
    st.markdown(
        f'<div class="callout">{text}</div>',
        unsafe_allow_html=True
    )


def muted(text):
    st.markdown(
        f'<div class="muted">{text}</div>',
        unsafe_allow_html=True
    )
