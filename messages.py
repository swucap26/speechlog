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