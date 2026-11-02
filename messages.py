# ==========================================
# C5-4: 메시지 및 안내 문구 정리
# ==========================================

def score_message(score):
    if score is None:
        return "발음 점수를 계산할 수 없습니다."
    if score >= 90:
        return f"🌟 연습 도움용 발음 점수는 **{score}점**입니다. 모델이 매우 또박또박하고 명확하게 인식했습니다."
    elif score >= 75:
        return f"👍 연습 도움용 발음 점수는 **{score}점**입니다. 전반적으로 모델이 잘 들어 이해하기 양호합니다."
    else:
        return f"💡 연습 도움용 발음 점수는 **{score}점**입니다. 아래 빨간색으로 표시된 음절을 위주로 천천히 다시 연습해 보세요."

def speed_message(syl_per_s):
    if syl_per_s is None:
        return "말하기 속도를 계산할 수 없습니다."
    
    # 한국어 낭독 적정 속도: 초당 5.0 ~ 7.0 음절
    if 5.0 <= syl_per_s <= 7.0:
        return f"⏱️ 말하기 속도는 **초당 {syl_per_s}음절**로, 일반적인 적정 속도(5~7음절/초)에 잘 맞추어 이야기하고 계십니다."
    elif syl_per_s < 5.0:
        return f"⏱️ 말하기 속도는 **초당 {syl_per_s}음절**로, 편안하게 전달하기에는 조금 천천히 말씀하시는 편입니다."
    else:
        return f"⏱️ 말하기 속도는 **초당 {syl_per_s}음절로**, 들으시는 분에 따라 조금 빠르게 느껴질 수 있습니다."

def pause_message(pause_count, pause_total_s):
    if pause_count is None or pause_count == 0:
        return "⏸️ 쉼(0.3초 이상 조용함) 없이 자연스럽게 이어서 말씀하셨습니다."
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
    "💡 발음 점수는 정답을 판가름하는 абсолю트 점수가 아니며, 스피치 연습 도움용 점수입니다.",
    "💡 두 음성 인식 모델(kresnik, kkonjeong)이 공통으로 음절을 다르게 들었다고 본 비율을 기준으로 계산됩니다.",
    "💡 적정 말하기 속도는 초당 5~7음절 기준이며, 쉼(0.3초 이상 조용함)은 속도 계산 시간에서 제외됩니다.",
    "💡 빨갛게 표시된 음절은 두 모델이 모두 입력 대본의 원문과 다르게 들었다고 반응한 위치입니다.",
    "💡 녹음 마이크 성능이나 주변 환경에 따라 음량(dB) 측정 결과는 다를 수 있으므로 상대적인 소리 크기 변화 위주로 참고하세요."
]