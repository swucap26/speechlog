"""쉼·크기 기준 조정용 (역할 B). analysis.py와 같은 폴더에 두고 실행해요. 모델이 필요 없어서 빨라요.

    python tune_signals.py 녹음폴더            (폴더 안의 wav·m4a를 모두 봐요)
    python tune_signals.py 녹음하나.wav

파일마다 길이, 쉼 목록, 평균 크기를 보여 주고, '조용함 기준(dB)'을 25/30/35/40으로 바꿨을 때 쉼이 몇 번 잡히는지 나란히 보여 줘요.
녹음을 직접 들으면서 "실제로 쉰 횟수"와 가장 잘 맞는 기준을 고르세요.
"""
import glob
import os
import sys

import analysis as a

CANDIDATES = [25, 30, 35, 40]


def files_from(arg):
    if os.path.isdir(arg):
        out = []
        for ext in ("wav", "m4a", "mp3"):
            out += glob.glob(os.path.join(arg, "**", f"*.{ext}"), recursive=True)
        return sorted(out)
    return [arg]


def main():
    if len(sys.argv) < 2:
        print("사용법: python tune_signals.py 녹음폴더_또는_파일")
        return
    paths = files_from(sys.argv[1])
    if not paths:
        print("녹음 파일을 못 찾았어요. 경로를 확인하세요.")
        return
    print(f"{'파일':<28}{'길이(초)':>8}" + "".join(f"{'쉼@'+str(c)+'dB':>10}" for c in CANDIDATES) + f"{'평균dB':>9}")
    for p in paths:
        wav = a.load_audio(p)
        t = a.trim_silence(wav)
        row = []
        for c in CANDIDATES:
            a.PAUSE_BELOW_PEAK_DB = c
            _, pauses, mean_db, _ = a.volume_and_pauses(t)
            row.append(len(pauses))
        a.PAUSE_BELOW_PEAK_DB = 35
        _, pauses35, mean_db, _ = a.volume_and_pauses(t)
        name = os.path.basename(p)[:26]
        print(f"{name:<28}{len(t)/a.SR:>8.1f}" + "".join(f"{n:>10}" for n in row) + f"{mean_db:>9.1f}")
        if pauses35:
            print("   35dB 기준 쉼 위치(초):", ", ".join(f"{q['start']}~{q['end']}" for q in pauses35))


if __name__ == "__main__":
    main()
