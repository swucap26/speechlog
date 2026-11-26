
import os, csv
import analysis

SCRIPTS = {
    1: "국물이 맛있어서 밥을 한 그릇 더 먹었습니다.",
    2: "신라의 역사를 설명할 수 있습니다.",
    3: "같이 해돋이를 보러 가요.",
    4: "학교에서 책을 읽다가 숙제를 했어요.",
    5: "좋고 많은 경험을 쌓았습니다.",
    6: "꽃이 핀 곳에서 만났습니다.",
    7: "값이 비싸서 닭고기를 샀습니다.",
    8: "서리가 내린 아침에 소리가 멀리 퍼졌습니다.",
    9: "안녕하십니까. 저는 데이터사이언스를 전공한 지원자입니다. 대학에서 팀 프로젝트를 여러 번 진행하며 자료를 분석하고 결과를 설명하는 일에 흥미를 느꼈습니다. 특히 사람들이 쉽게 이해할 수 있도록 그래프로 보여 주는 일을 좋아합니다. 맡은 일은 끝까지 책임지고 마무리하는 것이 제 강점입니다. 입사 후에는 데이터를 바탕으로 의사결정을 돕는 사람으로 성장하고 싶습니다. 감사합니다.",
    10: "저는 사용자의 말하기 습관을 분석하는 서비스를 만들며 데이터가 사람에게 도움이 될 수 있다는 것을 배웠습니다. 귀사는 데이터를 활용해 고객의 문제를 해결하는 일에 집중하고 있다고 알고 있습니다. 제가 가진 분석 경험과 꾸준히 배우려는 자세를 바탕으로 팀에 기여하고 싶어 지원하게 되었습니다. 입사 후에는 사용자의 목소리를 숫자로 이해해 본 경험을 살려 작은 개선도 꾸준히 만들어 가겠습니다."
}

analysis.load_models()
rows = []
for name in sorted(os.listdir("filler_data")):
    if not name.endswith(".wav"):
        continue
    _, num, tag = name[:-4].split("_")
    result = analysis.analyze(os.path.join("filler_data", name), SCRIPTS[int(num)])
    if not rows:
        print(result.keys())
    rows.append([name, tag, result.get("recognized"), result.get("bad_syllables"), result.get("score")])

with open("filler_result.csv", "w", newline="", encoding="utf-8-sig") as f:
    csv.writer(f).writerows([["파일", "추임새(o/x)", "인식문장", "틀린음절", "점수"]] + rows)