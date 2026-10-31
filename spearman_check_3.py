"""
청취 평가(사람 점수)와 모델 점수의 스피어만 상관 계산 — 평가자 3명용
사용법:  python spearman_check_3.py main_results.csv 청취표.csv
- 청취표 칸: 번호, file, 평가자1, 평가자2, 평가자3 (평가자 칸은 몇 개든 '평가자'로 시작하면 모두 사용)
- 결과표 점수 칸: 'kresnik_match_best' → 없으면 이름에 'match_best'가 들어간 첫 칸
- file 이름은 확장자(.m4a/.wav)와 폴더 경로를 떼고 짝을 맞춤
"""
import sys, os
import pandas as pd
from scipy.stats import spearmanr

THRESHOLD = 0.5


def key(name):
    base = os.path.basename(str(name).strip())
    return os.path.splitext(base)[0].lower()


def main(result_path, rating_path):
    res = pd.read_csv(result_path, encoding="utf-8-sig")
    rat = pd.read_csv(rating_path, encoding="utf-8-sig")

    if "kresnik_match_best" in res.columns:
        score_col = "kresnik_match_best"
    else:
        cands = [c for c in res.columns if "match_best" in c]
        if not cands:
            sys.exit(f"[오류] 결과표에 match_best 칸이 없음. 칸 목록: {list(res.columns)}")
        score_col = cands[0]

    raters = [c for c in rat.columns if str(c).startswith("평가자")]
    if len(raters) < 2:
        sys.exit(f"[오류] 청취표에 '평가자'로 시작하는 칸이 2개 이상 필요. 칸 목록: {list(rat.columns)}")

    res["key"] = res["file"].map(key)
    rat["key"] = rat["file"].map(key)
    rat["사람_평균"] = rat[raters].mean(axis=1)

    m = rat.merge(res[["key", score_col]], on="key", how="inner").dropna(subset=[score_col])
    missing = sorted(set(rat["key"]) - set(m["key"]))

    print(f"[설정] 모델 점수 칸: {score_col} / 평가자 칸: {', '.join(raters)}")
    print(f"[짝 맞춤] 청취표 {len(rat)}개 중 {len(m)}개 짝 찾음")
    if missing:
        print(f"  짝 못 찾은 파일 {len(missing)}개 (앞 10개): {missing[:10]}")
    if len(m) < 10:
        sys.exit("[오류] 짝이 10개 미만이라 상관을 믿기 어려움. file 이름 형식을 확인할 것.")

    print("\n[평가자끼리 일치도] (스피어만)")
    for i in range(len(raters)):
        for j in range(i + 1, len(raters)):
            r = spearmanr(rat[raters[i]], rat[raters[j]]).correlation
            print(f"  {raters[i]} vs {raters[j]}: {r:.2f}")

    print("\n[모델 점수 vs 사람 점수] (스피어만)")
    for c in raters:
        r = spearmanr(m[score_col], m[c]).correlation
        print(f"  모델 vs {c}: {r:.2f}")
    rho, p = spearmanr(m[score_col], m["사람_평균"])
    print(f"  모델 vs 사람_평균: {rho:.2f} (p = {p:.4f}, n = {len(m)})")

    verdict = "합격(0.5 이상)" if rho >= THRESHOLD else "불합격(0.5 미만)"
    print(f"\n판정: {verdict} — 상관계수 {rho:.2f}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit("사용법: python spearman_check_3.py main_results.csv 청취표.csv")
    main(sys.argv[1], sys.argv[2])
