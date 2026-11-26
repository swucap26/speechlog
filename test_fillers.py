
import csv, ast
import analysis

hit = {'o': 0, 'x': 0}
total = {'o': 0, 'x': 0}
with open('filler_result.csv', encoding='utf-8-sig') as f:
    for row in csv.DictReader(f):
        tag = row['추임새(o/x)']
        text = ast.literal_eval(row['인식문장'])['kresnik']
        total[tag] += 1
        if analysis.find_fillers(text):
            hit[tag] += 1
print(hit, total)