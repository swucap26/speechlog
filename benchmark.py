import time
from faster_whisper import WhisperModel

# 1. 파일럿 녹음 파일 경로 지정
audio_file = "test_speech.m4a"  # 실제 저장한 파일명으로 변경하세요

print("--- [테스트 1] faster-whisper (base) 모델 측정 시작 ---")
start_time = time.time()

# base 모델 로드 (GPU가 없을 경우 device="cpu", compute_type="int8" 설정)
model = WhisperModel("base", device="cpu", compute_type="int8")
segments, info = model.transcribe(audio_file, language="ko")

# 결과 텍스트 출력
result_text = "".join([segment.text for segment in segments])
elapsed_time = time.time() - start_time

print(f"인식 결과: {result_text}")
print(f"★ 총 소요 시간: {elapsed_time:.2f}초")