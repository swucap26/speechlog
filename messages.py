def score_message(score):
    if score is None:
        return "발음 점수를 계산할 수 없습니다."
    if score >= 90:
        return f"🌟 발음 점수는 {score}점입니다. 매우 또박또박하고 명확한 발음입니다!"
    elif score >= 75:
        return f"👍 발음 점수는 {score}점입니다. 전반적으로 양호하며 알아듣기 좋습니다."
    else:
        return f"💡 발음 점수는 {score}점입니다. 틀린 표시가 된 음절을 중심으로 천천히 연습해 보세요."

def speed_message(syl_per_s):
    if syl_per_s is None:
        return "말하기 속도를 계산할 수 없습니다."
    
    # 한국어 낭독 적정 속도: 5.0 ~ 7.0 음절/초
    if 5.0 <= syl_per_s <= 7.0:
        return f"⏱️ 말하기 속도는 초당 {syl_per_s}음절로, **적정 속도(5~7음절/초)** 범위 내에 있습니다."
    elif syl_per_s < 5.0:
        return f"⏱️ 말하기 속도는 초당 {syl_per_s}음절로, **보통보다 조금 느린 편**입니다."
    else:
        return f"⏱️ 말하기 속도는 초당 {syl_per_s}음절로, **보통보다 조금 빠른 편**입니다."

def pause_message(pause_count, pause_total_s):
    return f"⏸️ 총 {pause_count}회의 쉼이 감지되었으며, 쉬어간 총 시간은 {pause_total_s}초입니다."

# 기존 messages.py 내용 유지...

NOTES = [
    "💡 발음 점수는 두 음성 인식 모델(kresnik, kkonjeong)이 공통으로 어긋났다고 본 음절 비율로 계산됩니다.",
    "💡 적정 말하기 속도는 초당 5~7음절 기준이며, 쉼(0.3초 이상 조용함)은 속도 계산에서 제외됩니다.",
    "💡 빨갛게 표시된 음절은 두 모델이 모두 원문과 다르게 들었다고 판단한 위치입니다.",
    "💡 마이크와 환경에 따라 음량(dB) 측정 결과는 다를 수 있으므로 상대적인 변화 위주로 확인하세요."
]

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