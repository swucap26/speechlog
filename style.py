# 파일: style.py
# 역할: 화면 전체의 색, 카드, 알약 탭, 칩, 버튼 모양을 한곳에서 정함
import streamlit as st

GRAD = "linear-gradient(135deg, #D963FF 0%, #9141FB 55%, #5A2CFF 100%)"

_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700&display=swap');

html, body, .stApp, .stApp p, .stApp label, .stApp input, .stApp textarea, .stApp button {
  font-family: 'Noto Sans KR', sans-serif;
}
.stApp { background: #F3F1F9; color: #1A1A2E; }
.block-container { max-width: 640px; padding-top: 2rem; }
h1 { font-size: 1.5rem !important; font-weight: 700 !important; }
h2, h3 { font-size: 1.05rem !important; font-weight: 700 !important; }

/* ----------------------------------
   알약 탭 (C8 + U5-1: 반반 50% 분할 및 글자/칸 확정)
---------------------------------- */
.stTabs [data-baseweb="tab-list"], [role="tablist"] { 
  width: 100% !important;
  gap: 6px; 
  background: #fff; 
  border: 1px solid #E7E2F3; 
  border-radius: 999px; 
  padding: 4px; 
}
.stTabs [data-baseweb="tab"], button[role="tab"] { 
  flex: 1 !important; 
  justify-content: center !important;
  text-align: center !important;
  height: auto; 
  padding: 12px 0 !important; 
  border-radius: 999px; 
  background: transparent; 
}
.stTabs [data-baseweb="tab"] p, button[role="tab"] p { 
  font-size: 1.1rem !important; 
  font-weight: 700 !important; 
  color: #7A7891; 
}
.stTabs [aria-selected="true"], button[role="tab"][aria-selected="true"] { 
  background: __GRAD__ !important; 
}
.stTabs [aria-selected="true"] p, button[role="tab"][aria-selected="true"] p { 
  color: #fff !important; 
}
[data-baseweb="tab-highlight"], [data-baseweb="tab-border"] { 
  display: none !important; 
}

/* 카드: st.container(key="card_이름") 으로 만든 상자 (U5-2) */
[class*="st-key-card_"] { 
  background: #fff; 
  border: 1px solid #E7E2F3; 
  border-radius: 20px; 
  padding: 18px 18px 8px; 
  margin-bottom: 12px;
}

/* 입력칸 디자인 */
.stTextInput input, .stTextArea textarea, .stNumberInput input {
  background: #F1EAFE !important; border: 0 !important; border-radius: 12px !important; }
[data-baseweb="select"] > div { background: #F1EAFE !important; border: 0 !important; border-radius: 12px !important; }

/* 버튼 디자인 */
.stButton > button { border-radius: 14px; border: 0; background: #F1EAFE; color: #7B3FF2; font-weight: 600; padding: 0.7rem 1rem; }
button[kind="primary"], [data-testid="stBaseButton-primary"] {
  background: __GRAD__ !important; color: #fff !important; font-size: 1.05rem; padding: 0.9rem 1rem; }

/* 요약 카드 및 안내 상자 */
[data-testid="stMetric"] { background: #fff; border: 1px solid #E7E2F3; border-radius: 16px; padding: 12px 14px; }
[data-testid="stMetricValue"] { font-size: 1.6rem; }
[data-testid="stAlert"] { background: #F1EAFE; border-radius: 12px; }

/* 칩 및 파란/보라 콜아웃 */
.chip { display: inline-block; font-size: 12px; padding: 3px 10px; margin: 0 6px 6px 0; border-radius: 999px; background: #F1EAFE; color: #7B3FF2; font-weight: 500; }
.chip.bad { background: #FDECEF; color: #E5384F; }
.chip.warn { background: #FDF1DC; color: #C77A0A; }
.chip.ok { background: #E3F6EE; color: #1E9E6A; }
.muted { color: #7A7891; font-size: 13px; }
.callout { background: #F1EAFE; border-radius: 12px; padding: 10px 12px; font-size: 13px; color: #1A1A2E; margin-top: 8px; }
</style>
"""

def apply_style():
    st.markdown(_CSS.replace("__GRAD__", GRAD), unsafe_allow_html=True)

def chips(*items):
    html = "".join(f'<span class="chip {kind}">{text}</span>' for text, kind in items)
    st.markdown(html, unsafe_allow_html=True)

def callout(text):
    st.markdown(f'<div class="callout">{text}</div>', unsafe_allow_html=True)

def muted(text):
    st.markdown(f'<div class="muted">{text}</div>', unsafe_allow_html=True)