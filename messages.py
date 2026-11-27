# 파일: messages.py
# 역할: 분석 결과(발음 점수, 말하기 속도, 쉼 횟수, 목표 시간 차이)별 피드백 안내 문구 생성

# ==========================================
# C5-4: 메시지 및 안내 문구 정리
# ==========================================

def score_message(score):
    if score is None:
        return "발음 점수를 계산할 수 없습니다."
    if score >= 90:
        return f"🌟 발음 점수는 **{score}점**입니다. 모델이 매우 또박또박하고 명확하게 인식했습니다."
    elif score >= 75:
        return f"👍 발음 점수는 **{score}점**입니다. 전반적으로 모델이 잘 들어 이해하기 양호합니다."
    else:
        return f"💡 발음 점수는 **{score}점**입니다. 아래 빨간색으로 표시된 음절 위주로 천천히 다시 연습해 보세요."

def speed_message(syl_per_s):
    if syl_per_s is None:
        return "말하기 속도를 계산할 수 없습니다."
    
    # 한국어 낭독 적정 속도: 초당 5.0 ~ 7.0 음절
    if 5.0 <= syl_per_s <= 7.0:
        return "⏱️ 일반적인 적정 속도(5~7음절/초)에 잘 맞추어 이야기하고 계십니다."
    elif syl_per_s < 5.0:
        return "⏱️ 편안하게 전달하기에는 조금 천천히 말씀하시는 편입니다."
    else:
        return "⏱️ 들으시는 분에 따라 조금 빠르게 느껴질 수 있습니다."

def pause_message(pause_count, pause_total_s):
    if pause_count is None or pause_count == 0:
        return "⏸️ 쉬는 구간 없이 자연스럽게 이어서 말씀하셨습니다."
    return f"⏸️ 말하는 동안 총 **{pause_count}회** 쉬어간 구간이 감지되었으며, 총 쉬어간 시간은 **{pause_total_s}초**입니다."

def target_gap_message(duration_s, target_sec):
    if target_sec is None or target_sec <= 0:
        return ""
    diff = round(duration_s - target_sec, 1)
    if diff > 0:
        return f"⏱️ **목표 시간 결과:** 목표({target_sec}초)보다 **{diff}초 초과**되었습니다."
    elif diff < 0:
        return f"⏱️ **목표 시간 결과:** 목표({target_sec}초)보다 **{abs(diff)}초 단축**되었습니다."
    else:
        return f"⏱️ **목표 시간 결과:** 목표 시간({target_sec}초)에 정확히 도달했습니다!"

# C5-4: NOTES 내의 단정적 표현 수정 및 유연한 설명으로 교체
NOTES = [
    "💡 발음 점수는 정답을 판가름하는 점수가 아니며, 스피치 연습 도움용 점수입니다.",
    "💡 발음 점수는 음성 인식 모델 두 개가 대본과 다르게 들은 글자가 얼마나 되는지를 기준으로 계산합니다. ",
    "💡 알맞은 말하기 속도는 1초에 5~7글자 정도입니다. 쉬는 구간은 속도 계산 시간에서 제외됩니다.",
    "💡 빨간색 글자는 두 모델에게 대본과 다르게 들린 부분입니다. 이 부분을 천천히 다시 연습해 보세요.",
    "💡 녹음 마이크 성능이나 주변 소음에 따라 음량(dB) 측정 결과는 달라질 수 있습니다. 숫자보다 소리가 커지고 작아지는 흐름을 참고하세요."
]