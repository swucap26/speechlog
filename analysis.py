"""
스피치로그 분석 모듈 (analysis.py)

앱(app.py)은 이 파일의 analyze() 하나만 부르면 돼요.

    from analysis import analyze, mark_script
    result = analyze("녹음.wav", "대본 문장")
    if "error" in result:
        ...   # result["error"] 문구를 화면에 보여 주세요 (예: "녹음이 너무 짧아요...")
    else:
        result["score"], result["bad_syllables"], result["syl_per_s"] ...

점수 계산(자모 분해, 정렬, match_best)은 검증 노트북 v3의 ③-3 칸에서 글자 그대로 가져왔어요.
그 부분은 노트북과 점수가 같아야 하니 고치지 마세요. (고치려면 노트북 v3부터 같이 고쳐야 해요.)
"""
import math
import re
import time

import numpy as np

SR = 16000
CTC_MODELS = {
    "kresnik": "kresnik/wav2vec2-large-xlsr-korean",
    "kkonjeong": "Kkonjeong/wav2vec2-base-korean",
}
MAIN_MODEL = "kresnik"        # 발음 점수(score)를 이 모델의 match_best로 정해요 (ADR-1: 주력 kresnik, 보조 kkonjeong)

# 시작값들: 녹음 몇 개를 직접 들으면서 조정하세요 (계획서 2주차 항목에도 "시작값"이라고 적혀 있어요)
MIN_DURATION_S = 1.0          # 이보다 짧으면 "다시 녹음해 주세요"
MIN_PEAK = 0.01               # 소리 최대 크기가 이보다 작으면 무음으로 봐요 (0~1 범위)
PAUSE_MIN_S = 0.3             # 이 시간 이상 조용하면 '쉼'
PAUSE_BELOW_PEAK_DB = 30      # 큰 소리(상위 5%)보다 이만큼(dB) 작으면 '조용함'
FRAME_S = 0.1                 # 크기(dB)를 0.1초마다 계산

_cache = {}


# =====================================================================
# 1. 검증 노트북 v3 ③-3에서 그대로 가져온 부분 (수정하지 마세요)
# =====================================================================
import re

CHO = list("ㄱㄲㄴㄷㄸㄹㅁㅂㅃㅅㅆㅇㅈㅉㅊㅋㅌㅍㅎ")
JUNG = list("ㅏㅐㅑㅒㅓㅔㅕㅖㅗㅘㅙㅚㅛㅜㅝㅞㅟㅠㅡㅢㅣ")
JONG = [""] + list("ㄱㄲㄳㄴㄵㄶㄷㄹㄺㄻㄼㄽㄾㄿㅀㅁㅂㅄㅅㅆㅇㅈㅊㅋㅌㅍㅎ")
COMPAT = set(CHO + JUNG + JONG[1:])


def to_jamo(text):
    """한글 문자열 -> 자모 리스트, 각 자모가 몇 번째 음절에서 왔는지도 함께 반환.
    완성형 음절(가~힣), 조합형 자모(U+1100~), 호환 자모(ㄱ,ㅏ) 모두 처리.
    공백·문장부호·영어·숫자는 버림."""
    jamo, syl_idx = [], []
    s = 0
    for ch in text:
        c = ord(ch)
        if 0xAC00 <= c <= 0xD7A3:
            k = c - 0xAC00
            parts = [CHO[k // 588], JUNG[(k % 588) // 28], JONG[k % 28]]
            for p in parts:
                if p:
                    jamo.append(p); syl_idx.append(s)
            s += 1
        elif 0x1100 <= c <= 0x1112:
            jamo.append(CHO[c - 0x1100]); syl_idx.append(s)
        elif 0x1161 <= c <= 0x1175:
            jamo.append(JUNG[c - 0x1161]); syl_idx.append(s)
        elif 0x11A8 <= c <= 0x11C2:
            jamo.append(JONG[c - 0x11A8 + 1]); syl_idx.append(s)
        elif ch in COMPAT:
            jamo.append(ch); syl_idx.append(s)
    return jamo, syl_idx


def align(ref, hyp):
    """편집거리 정렬. (op, ref_i, hyp_j) 목록 반환. op: '=' 일치, 'S' 바뀜, 'D' 빠짐, 'I' 끼어듦"""
    n, m = len(ref), len(hyp)
    d = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n + 1):
        d[i][0] = i
    for j in range(m + 1):
        d[0][j] = j
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            cost = 0 if ref[i - 1] == hyp[j - 1] else 1
            d[i][j] = min(d[i - 1][j] + 1, d[i][j - 1] + 1, d[i - 1][j - 1] + cost)
    ops, i, j = [], n, m
    while i > 0 or j > 0:
        if i > 0 and j > 0 and d[i][j] == d[i - 1][j - 1] + (ref[i - 1] != hyp[j - 1]):
            ops.append(("=" if ref[i - 1] == hyp[j - 1] else "S", i - 1, j - 1)); i -= 1; j -= 1
        elif i > 0 and d[i][j] == d[i - 1][j] + 1:
            ops.append(("D", i - 1, None)); i -= 1
        else:
            ops.append(("I", None, j - 1)); j -= 1
    return ops[::-1]


def match_score(ref_text, hyp_text):
    """대본 대비 일치율(0~100). 1 - (바뀜+빠짐+끼어듦)/대본자모수, 0 미만은 0."""
    ref, _ = to_jamo(ref_text)
    hyp, _ = to_jamo(hyp_text)
    if not ref:
        return None
    errs = sum(1 for op, _, _ in align(ref, hyp) if op != "=")
    return round(max(0.0, 1 - errs / len(ref)) * 100, 1)


def error_syllables(ref_text, hyp_text):
    """대본의 몇 번째 음절(공백 제외)에서 어긋났는지 집합으로 반환."""
    ref, idx = to_jamo(ref_text)
    hyp, _ = to_jamo(hyp_text)
    bad = set()
    ops = align(ref, hyp)
    for k, (op, i, j) in enumerate(ops):
        if op in ("S", "D"):
            bad.add(idx[i])
        elif op == "I":
            # 끼어든 자모는 바로 앞(없으면 뒤) 대본 음절에 표시
            prev = next((ops[t][1] for t in range(k - 1, -1, -1) if ops[t][1] is not None), None)
            nxt = next((ops[t][1] for t in range(k + 1, len(ops)) if ops[t][1] is not None), None)
            ref_i = prev if prev is not None else nxt
            if ref_i is not None:
                bad.add(idx[ref_i])
    return bad


def highlight(ref_text, hyp_text):
    """어긋난 음절을 [ ]로 감싼 대본 문자열."""
    bad = error_syllables(ref_text, hyp_text)
    out, s = [], 0
    for ch in ref_text:
        if 0xAC00 <= ord(ch) <= 0xD7A3:
            out.append(f"[{ch}]" if s in bad else ch); s += 1
        else:
            out.append(ch)
    return "".join(out)

"""설치 없이 쓰는 간단한 한국어 발음 변환기 (g2pK 대체용).
표준 발음법의 주요 규칙만 구현: 겹받침, ㅎ 축약·탈락, 구개음화, 연음,
받침 대표음, 비음화, 유음화, 경음화. 띄어쓰기 단위(어절) 안에서만 적용.
형태소 분석이 필요한 규칙(예: '줄게요'→[줄께요], ㄴ 첨가)은 처리하지 않음."""
import re

CHO = list("ㄱㄲㄴㄷㄸㄹㅁㅂㅃㅅㅆㅇㅈㅉㅊㅋㅌㅍㅎ")
JUNG = list("ㅏㅐㅑㅒㅓㅔㅕㅖㅗㅘㅙㅚㅛㅜㅝㅞㅟㅠㅡㅢㅣ")
JONG = [""] + list("ㄱㄲㄳㄴㄵㄶㄷㄹㄺㄻㄼㄽㄾㄿㅀㅁㅂㅄㅅㅆㅇㅈㅊㅋㅌㅍㅎ")

# 겹받침: (모음 앞에서 남는 받침, 넘어가는 자음), 자음 앞/끝에서의 대표음
CLUSTER = {"ㄳ": ("ㄱ", "ㅅ", "ㄱ"), "ㄵ": ("ㄴ", "ㅈ", "ㄴ"), "ㄶ": ("ㄴ", "ㅎ", "ㄴ"),
           "ㄺ": ("ㄹ", "ㄱ", "ㄱ"), "ㄻ": ("ㄹ", "ㅁ", "ㅁ"), "ㄼ": ("ㄹ", "ㅂ", "ㄹ"),
           "ㄽ": ("ㄹ", "ㅅ", "ㄹ"), "ㄾ": ("ㄹ", "ㅌ", "ㄹ"), "ㄿ": ("ㄹ", "ㅍ", "ㅂ"),
           "ㅀ": ("ㄹ", "ㅎ", "ㄹ"), "ㅄ": ("ㅂ", "ㅅ", "ㅂ")}
NEUTRAL = {"ㄲ": "ㄱ", "ㅋ": "ㄱ", "ㅅ": "ㄷ", "ㅆ": "ㄷ", "ㅈ": "ㄷ", "ㅊ": "ㄷ",
           "ㅌ": "ㄷ", "ㅎ": "ㄷ", "ㅍ": "ㅂ"}
ASPIRATE = {"ㄱ": "ㅋ", "ㄷ": "ㅌ", "ㅂ": "ㅍ", "ㅈ": "ㅊ"}
TENSE = {"ㄱ": "ㄲ", "ㄷ": "ㄸ", "ㅂ": "ㅃ", "ㅅ": "ㅆ", "ㅈ": "ㅉ"}
NASAL = {"ㄱ": "ㅇ", "ㄷ": "ㄴ", "ㅂ": "ㅁ"}


def _split(word):
    out = []
    for ch in word:
        k = ord(ch) - 0xAC00
        out.append([CHO[k // 588], JUNG[(k % 588) // 28], JONG[k % 28]])
    return out


def _join(sy):
    return "".join(chr(0xAC00 + (CHO.index(c) * 21 + JUNG.index(v)) * 28 + JONG.index(j)) for c, v, j in sy)


def _word(word):
    s = _split(word)
    n = len(s)
    # 1단계: 모음 앞 (ㅎ 탈락, 구개음화, 연음)
    for i in range(n - 1):
        j, nc, nv = s[i][2], s[i + 1][0], s[i + 1][1]
        if nc == "ㅇ" and j:
            if j in ("ㅎ",):
                s[i][2] = ""
            elif j in ("ㄶ", "ㅀ"):
                s[i][2] = ""; s[i + 1][0] = CLUSTER[j][0]
            elif j in CLUSTER:
                s[i][2], s[i + 1][0] = CLUSTER[j][0], CLUSTER[j][1]
                if s[i + 1][0] == "ㅅ" and s[i][2] in ("ㄱ", "ㅂ"):
                    s[i + 1][0] = "ㅆ"
            elif j == "ㅇ":
                pass
            elif j in ("ㄷ", "ㅌ") and nv == "ㅣ":
                s[i][2] = ""; s[i + 1][0] = "ㅈ" if j == "ㄷ" else "ㅊ"
            else:
                s[i][2] = ""; s[i + 1][0] = j
    # 2단계: ㅎ 축약 (거센소리)
    for i in range(n - 1):
        j, nc = s[i][2], s[i + 1][0]
        if j in ("ㅎ", "ㄶ", "ㅀ") and nc in ASPIRATE:
            s[i][2] = "" if j == "ㅎ" else CLUSTER[j][0]; s[i + 1][0] = ASPIRATE[nc]
        elif j in ("ㅎ", "ㄶ", "ㅀ") and nc == "ㅅ":
            s[i][2] = "" if j == "ㅎ" else CLUSTER[j][0]; s[i + 1][0] = "ㅆ"
        elif j == "ㅎ" and nc == "ㄴ":
            s[i][2] = "ㄴ"
        elif nc == "ㅎ":
            base = CLUSTER[j][2] if j in CLUSTER else NEUTRAL.get(j, j)
            if base in ASPIRATE:
                if j in ("ㄷ", "ㅌ") and s[i + 1][1] == "ㅣ":
                    s[i][2] = ""; s[i + 1][0] = "ㅊ"
                else:
                    s[i][2] = CLUSTER[j][0] if j in CLUSTER and CLUSTER[j][2] != base else ""
                    s[i + 1][0] = ASPIRATE[base]
    # 3단계: 받침 대표음
    for i in range(n):
        j = s[i][2]
        if j in CLUSTER:
            s[i][2] = CLUSTER[j][2]
        elif j in NEUTRAL:
            s[i][2] = NEUTRAL[j]
    # 4단계: 비음화, 유음화, 경음화
    for i in range(n - 1):
        j, nc = s[i][2], s[i + 1][0]
        if j in ("ㅁ", "ㅇ") and nc == "ㄹ":
            s[i + 1][0] = "ㄴ"
        elif j in NASAL and nc == "ㄹ":
            s[i][2] = NASAL[j]; s[i + 1][0] = "ㄴ"
        elif j in NASAL and nc in ("ㄴ", "ㅁ"):
            s[i][2] = NASAL[j]
        elif j == "ㄴ" and nc == "ㄹ":
            s[i][2] = "ㄹ"
        elif j == "ㄹ" and nc == "ㄴ":
            s[i + 1][0] = "ㄹ"
        elif j in ("ㄱ", "ㄷ", "ㅂ") and nc in TENSE:
            s[i + 1][0] = TENSE[nc]
    return _join(s)


def pron_ko(text):
    """문장 → 발음 표기. 한글 이외 문자와 공백은 그대로 둠."""
    return re.sub(r"[가-힣]+", lambda m: _word(m.group()), text)


def bad_syllables(script, pron, hyp):
    # 철자 기준으로도, 발음 기준으로도 틀린 음절만 (둘 중 하나와 맞으면 정답)
    return error_syllables(script, hyp) & error_syllables(pron, hyp)


def match_best(script, pron, hyp):
    n = len(re.findall(r"[가-힣]", script))
    return round(100 * (1 - len(bad_syllables(script, pron, hyp)) / n), 1) if n else None


def highlight_two(script, pron, hyp_a, hyp_b):
    # 두 모델이 모두 틀렸다고 본 음절만 [ ]로 표시
    bad = bad_syllables(script, pron, hyp_a) & bad_syllables(script, pron, hyp_b)
    out, s = [], 0
    for ch in script:
        if 0xAC00 <= ord(ch) <= 0xD7A3:
            out.append(f"[{ch}]" if s in bad else ch); s += 1
        else:
            out.append(ch)
    return "".join(out)


# =====================================================================
# 2. 발음 표기 변환 (g2pk2가 되면 g2pk2, 안 되면 위의 pron_ko로 자동 대체)
# =====================================================================
def _get_g2p():
    if "g2p" not in _cache:
        try:
            from pecab import PeCab
            from g2pk2 import G2p
            g = G2p()
            g.mecab = PeCab()          # 설치가 안 되는 mecab 대신 PeCab을 끼워 넣기
            _cache["g2p"], _cache["g2p_name"] = g, "g2pk2"
        except Exception as e:
            print("g2pk2 사용 불가 → 직접 만든 함수(pron_ko) 사용:", e)
            _cache["g2p"], _cache["g2p_name"] = pron_ko, "pron_ko"
    return _cache["g2p"]


def g2p_name():
    _get_g2p()
    return _cache["g2p_name"]


def to_pron(text):
    return _get_g2p()(text)


# =====================================================================
# 3. 소리 파일 읽기, 앞뒤 무음 자르기, 입력 검사
# =====================================================================
def load_audio(path):
    """파일 → 16kHz 모노 소리 배열(float32, -1~1)."""
    try:
        import librosa
        wav, _ = librosa.load(path, sr=SR, mono=True)
    except ImportError:                     # 시험용: librosa가 없으면 16kHz wav만 읽어요
        from scipy.io import wavfile
        sr, data = wavfile.read(path)
        if sr != SR:
            raise ValueError("librosa가 없으면 16kHz wav만 읽을 수 있어요")
        wav = data.astype(np.float32) / (32768.0 if data.dtype == np.int16 else 1.0)
        if wav.ndim > 1:
            wav = wav.mean(axis=1)
    return wav.astype(np.float32)


def trim_silence(wav, top_db=30):
    """앞뒤 무음을 잘라요. 노트북 v3와 같은 librosa 방식(top_db=30)을 써요."""
    try:
        import librosa
        trimmed, _ = librosa.effects.trim(wav, top_db=top_db)
        return trimmed
    except ImportError:                     # 시험용 근사 (librosa가 있으면 쓰이지 않아요)
        frame, hop = 2048, 512
        if len(wav) < frame:
            return wav
        n = 1 + (len(wav) - frame) // hop
        rms = np.array([np.sqrt(np.mean(wav[i * hop:i * hop + frame] ** 2)) for i in range(n)])
        db = 20 * np.log10(np.maximum(rms, 1e-10) / max(rms.max(), 1e-10))
        keep = np.where(db > -top_db)[0]
        if len(keep) == 0:
            return wav
        return wav[keep[0] * hop: min(len(wav), keep[-1] * hop + frame)]


def count_syllables(script):
    return len(re.findall(r"[가-힣]", script))


def check_input(wav, script):
    """문제가 있으면 화면에 보여 줄 문구를, 괜찮으면 None을 돌려줘요."""
    if count_syllables(script) == 0:
        return "한글 대본을 입력해 주세요."
    if len(wav) / SR < MIN_DURATION_S:
        return "녹음이 너무 짧아요. 다시 녹음해 주세요."
    if float(np.max(np.abs(wav))) < MIN_PEAK:
        return "소리가 거의 들리지 않아요. 마이크를 확인하고 다시 녹음해 주세요."
    return None


# =====================================================================
# 4. 속도 · 쉼 · 크기 (소리 에너지로만 계산해요. 위스퍼가 필요 없어서 빨라요)
# =====================================================================
def volume_and_pauses(trimmed):
    """0.1초마다 크기(dB)를 재고, 0.3초 넘게 조용한 구간을 '쉼'으로 봐요.
    dB는 마이크마다 달라서 '같은 기기 안에서의 비교'만 의미가 있어요."""
    hop = int(FRAME_S * SR)
    n = len(trimmed) // hop
    if n == 0:
        return [], [], 0.0, 0.0
    frames = trimmed[: n * hop].reshape(n, hop)
    rms = np.sqrt((frames ** 2).mean(axis=1))
    db = 20 * np.log10(np.maximum(rms, 1e-10))
    thr = np.percentile(db, 95) - PAUSE_BELOW_PEAK_DB
    quiet = db < thr

    need = int(round(PAUSE_MIN_S / FRAME_S))        # 쉼이 되려면 연속 몇 칸이 조용해야 하나 (0.3초 → 3칸)
    pauses, i = [], 0
    while i < n:
        if quiet[i]:
            j = i
            while j < n and quiet[j]:
                j += 1
            if j - i >= need:
                pauses.append({"start": round(i * FRAME_S, 2), "end": round(j * FRAME_S, 2)})
            i = j
        else:
            i += 1
    voiced = db[~quiet]
    mean_db = float(voiced.mean()) if len(voiced) else float(db.mean())
    std_db = float(voiced.std()) if len(voiced) else float(db.std())
    return [round(float(x), 1) for x in db], pauses, mean_db, std_db


# =====================================================================
# 5. 모델로 받아 적기 (wav2vec2 두 개)
# =====================================================================
def load_models(models=("kresnik", "kkonjeong")):
    """모델은 처음 한 번만 불러오고 다음부터는 재사용해요. (앱에서는 @st.cache_resource로 한 번 더 감싸세요)"""
    import torch
    from transformers import Wav2Vec2Processor, AutoProcessor, AutoModelForCTC
    device = "cuda" if torch.cuda.is_available() else "cpu"
    loaded = _cache.setdefault("ctc", {})
    for key in models:
        if key in loaded:
            continue
        name = CTC_MODELS[key]
        try:
            try:
                proc = Wav2Vec2Processor.from_pretrained(name)
            except Exception:
                proc = AutoProcessor.from_pretrained(name)
            model = AutoModelForCTC.from_pretrained(name).to(device).eval()
            loaded[key] = (proc, model, device)
        except Exception as e:
            print(f"{key} 불러오기 실패, 이 모델은 건너뜀: {e}")
    return {k: loaded[k] for k in models if k in loaded}


def recognize(wav, models=("kresnik", "kkonjeong")):
    """소리 배열 → {모델이름: 받아 적은 글}. (노트북 v3의 run_ctc에서 대본 가능도만 뺀 것)"""
    import torch
    out = {}
    for key, (proc, model, device) in load_models(models).items():
        inputs = proc(wav, sampling_rate=SR, return_tensors="pt")
        with torch.no_grad():
            logits = model(inputs.input_values.to(device)).logits[0].float().cpu()
        ids = logits.argmax(-1)
        out[key] = proc.batch_decode(ids.unsqueeze(0))[0]
    return out


# =====================================================================
# 6. 점수 계산 (모델 없이 글만으로) 와 화면 표시용 도우미
# =====================================================================
def score_texts(script, pron, texts):
    """texts = {모델이름: 받아 적은 글}.
    score: MAIN_MODEL의 match_best (없으면 있는 모델 중 첫 번째)
    bad_syllables: 모든 모델이 '틀렸다'고 본 음절 번호 (대본에서 공백을 뺀 0번부터의 순서)"""
    per_model, bads = {}, {}
    for key, t in texts.items():
        per_model[key] = match_best(script, pron, t)
        bads[key] = bad_syllables(script, pron, t)
    if not per_model:
        return None, [], {}
    main = MAIN_MODEL if MAIN_MODEL in per_model else next(iter(per_model))
    both = set.intersection(*bads.values())
    return per_model[main], sorted(both), per_model


def mark_script(script, bad_syllables_list):
    """화면 표시용. [(글자, 틀렸나?), ...] 를 돌려줘요. 한글이 아닌 글자(공백 등)는 항상 False."""
    bad, out, s = set(bad_syllables_list), [], 0
    for ch in script:
        if 0xAC00 <= ord(ch) <= 0xD7A3:
            out.append((ch, s in bad))
            s += 1
        else:
            out.append((ch, False))
    return out


# =====================================================================
# 7. 앱이 부르는 함수
# =====================================================================
def analyze(wav_path, script, models=("kresnik", "kkonjeong")):
    """녹음 파일과 대본을 받아 결과를 dict로 돌려줘요.
    문제가 있으면 {"error": "화면에 보여 줄 문구"} 만 돌려줘요."""
    t0 = time.time()
    wav = load_audio(wav_path)
    err = check_input(wav, script)
    if err:
        return {"error": err}

    trimmed = trim_silence(wav)
    dur = len(trimmed) / SR
    n_syl = count_syllables(script)
    db, pauses, mean_db, std_db = volume_and_pauses(trimmed)
    pause_total = round(sum(p["end"] - p["start"] for p in pauses), 2)
    speak_time = dur - pause_total

    texts = recognize(wav, models)
    pron = to_pron(script)
    score, bad, per_model = score_texts(script, pron, texts)

    return {
        "score": score,                                   # 발음 점수 0~100 (match_best)
        "bad_syllables": bad,                             # 두 모델이 모두 틀렸다고 본 음절 번호
        "marked": mark_script(script, bad),               # [(글자, 틀렸나?)] 화면에 빨갛게 칠할 때 쓰세요
        "recognized": texts,                              # 모델별 받아 적은 글
        "score_by_model": per_model,
        "pron": pron,
        "g2p_name": g2p_name(),
        "duration_s": round(dur, 2),
        "n_syllables": n_syl,
        "syl_per_s": round(n_syl / dur, 2) if dur else None,                       # 발화 속도 (쉼 포함)
        "artic_rate": round(n_syl / speak_time, 2) if speak_time > 0 else None,   # 조음 속도 (쉼 뺀 시간)
        "pauses": pauses,
        "pause_count": len(pauses),
        "pause_total_s": pause_total,
        "db": db,                                         # 0.1초마다의 크기 (그래프용)
        "mean_db": round(mean_db, 1),
        "db_std": round(std_db, 1),
        "elapsed_s": round(time.time() - t0, 1),          # 분석에 걸린 시간 (30초 안이어야 해요)
    }

import re
RULE_NAMES = ["비음화", "유음화", "구개음화", "경음화", "ㅎ 축약·탈락", "연음", "겹받침", "ㅓ/ㅗ 구분"]   # 대본 01~08 순서


def weakest_rules(scores_by_rule, n=2):
    """scores_by_rule = {"비음화": 85.7, ...} → 점수가 가장 낮은 규칙 n개 [(규칙, 점수)]"""
    return sorted(scores_by_rule.items(), key=lambda kv: (kv[1], kv[0]))[:n]

def speed_for_target(script, target_sec):
    """목표 시간 안에 읽으려면 필요한 초당 음절 수."""
    return round(count_syllables(script) / target_sec, 1)

def target_gap_message(duration_s, target_sec):
    gap = round(duration_s - target_sec)
    if gap > 0:
        return f"목표보다 {gap}초 초과"
    if gap < 0:
        return f"목표보다 {-gap}초 미달"
    return "목표 시간과 거의 같아요"
    
if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print('사용법: python analysis.py 녹음.wav "대본 문장"')
        raise SystemExit(1)
    res = analyze(sys.argv[1], sys.argv[2])
    for k, v in res.items():
        if k in ("db", "marked"):
            continue
        print(f"{k}: {v}")
    if "marked" in res:
        print("틀린 음절 표시:", "".join(f"[{c}]" if b else c for c, b in res["marked"]))
