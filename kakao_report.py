"""카톡으로 받은 녹음을 분석해서, 카톡에 그대로 붙여 넣을 결과 문장을 만들어 줘요.
사용법: python kakao_report.py "대본 문장" 녹음1.m4a 녹음2.m4a 녹음3.m4a
(녹음은 1회차, 2회차, 3회차 순서로 적어요. wav·m4a 모두 되지만 m4a가 안 읽히면 README 아래 ffmpeg 변환을 쓰세요)
"""
import sys
from analysis import analyze, load_models


def one_line(i, res):
    if "error" in res:
        return f"[{i}회차] 분석 못 함: {res['error']} (다시 녹음해 주세요)"
    bad = "".join(c for c, b in res["marked"] if b) or "없음"
    shown = "".join(f"[{c}]" if b else c for c, b in res["marked"])
    return (f"[{i}회차] 발음 점수 {res['score']}점 / 틀린 글자(빨간색): {bad}\n"
            f"  대본 표시: {shown}\n"
            f"  속도 초당 {res['syl_per_s']}음절 / 쉼 {res['pause_count']}번(합 {res['pause_total_s']}초)")


def main(script, files):
    load_models()
    results = [analyze(f, script) for f in files]
    lines = [one_line(i, r) for i, r in enumerate(results, 1)]
    ok = [r for r in results if "error" not in r]
    if len(ok) >= 2:
        d = round(ok[-1]["score"] - ok[0]["score"], 1)
        lines.append(f"첫 회차 대비 마지막 회차 발음 점수 변화: {d:+}점")
    print("\n".join(lines))


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(__doc__)
        raise SystemExit(1)
    main(sys.argv[1], sys.argv[2:])
