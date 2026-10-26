"""스피치로그 기록 저장 모듈 (db.py) — 역할 B 담당.
C의 app.py는 이 파일의 함수만 부르면 돼요. SQL을 직접 쓸 필요가 없어요.

    import db
    db.init_db()                                              # 앱 시작 때 한 번 (이미 있으면 그대로 둬요)
    attempt_id = db.save_attempt("소현", script_text, result, audio_path)   # result = analyze()가 돌려준 dict
    rows = db.get_attempts("소현", script_id)                  # 회차 목록 (1회차부터)
    print(db.change_sentence(rows[-2], rows[-1]))              # "지난 회차보다 발음 +3점, ..."
"""
import json
import re
import sqlite3
from datetime import datetime

DB_PATH = "speechlog.db"          # 실행하는 폴더에 생겨요. .gitignore에 꼭 넣으세요 (GitHub에 올리지 않기)

SCHEMA = """
CREATE TABLE IF NOT EXISTS scripts (
    script_id  INTEGER PRIMARY KEY AUTOINCREMENT,
    text       TEXT NOT NULL UNIQUE,
    pron       TEXT,
    kind       TEXT,
    created_at TEXT
);
CREATE TABLE IF NOT EXISTS attempts (
    attempt_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    script_id       INTEGER NOT NULL REFERENCES scripts(script_id),
    user_name       TEXT NOT NULL,
    created_at      TEXT,
    is_baseline     INTEGER DEFAULT 0,
    target_sec      REAL,
    score           REAL,
    bad_syllables   TEXT,
    recognized_text TEXT,
    syl_per_s       REAL,
    artic_rate      REAL,
    pause_count     INTEGER,
    pause_total_s   REAL,
    mean_db         REAL,
    db_std          REAL,
    audio_path      TEXT
);
"""


def _conn():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con


def _now():
    return datetime.now().isoformat(timespec="seconds")


def init_db():
    with _conn() as con:
        con.executescript(SCHEMA)


def get_or_create_script(text, pron=None, kind="사용자"):
    with _conn() as con:
        row = con.execute("SELECT script_id FROM scripts WHERE text = ?", (text,)).fetchone()
        if row:
            return row["script_id"]
        cur = con.execute("INSERT INTO scripts (text, pron, kind, created_at) VALUES (?,?,?,?)",
                          (text, pron, kind, _now()))
        return cur.lastrowid


def save_attempt(user_name, script_text, result, audio_path, target_sec=None,
                 is_baseline=False, kind="사용자"):
    """analyze()의 결과 dict 한 개를 한 줄로 저장해요. 저장된 attempt_id를 돌려줘요."""
    if "error" in result:
        raise ValueError("error 결과는 저장하지 않아요: " + result["error"])
    sid = get_or_create_script(script_text, result.get("pron"), kind)
    texts = result.get("recognized") or {}
    rec = texts.get("kresnik") or (next(iter(texts.values())) if texts else "")
    with _conn() as con:
        cur = con.execute(
            """INSERT INTO attempts (script_id, user_name, created_at, is_baseline, target_sec, score,
               bad_syllables, recognized_text, syl_per_s, artic_rate, pause_count, pause_total_s,
               mean_db, db_std, audio_path) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (sid, user_name, _now(), int(is_baseline), target_sec, result["score"],
             json.dumps(result["bad_syllables"]), rec, result["syl_per_s"], result["artic_rate"],
             result["pause_count"], result["pause_total_s"], result["mean_db"], result["db_std"],
             audio_path))
        return cur.lastrowid


def list_scripts(user_name):
    """이 사용자가 연습한 대본 목록: [{script_id, text, n_attempts}]"""
    with _conn() as con:
        rows = con.execute(
            """SELECT s.script_id, s.text, COUNT(*) AS n_attempts FROM attempts a
               JOIN scripts s ON s.script_id = a.script_id
               WHERE a.user_name = ? GROUP BY s.script_id ORDER BY MAX(a.attempt_id) DESC""",
            (user_name,)).fetchall()
    return [dict(r) for r in rows]


def get_attempts(user_name, script_id):
    """회차 순서대로(오래된 것 먼저) [{round, score, bad_syllables(list), ...}]"""
    with _conn() as con:
        rows = con.execute(
            "SELECT * FROM attempts WHERE user_name = ? AND script_id = ? ORDER BY attempt_id",
            (user_name, script_id)).fetchall()
    out = []
    for i, r in enumerate(rows, 1):
        d = dict(r)
        d["round"] = i
        d["bad_syllables"] = json.loads(d["bad_syllables"] or "[]")
        out.append(d)
    return out


def change_sentence(prev, cur):
    """직전 회차(prev)와 이번 회차(cur)를 비교하는 한 줄 문장."""
    ds = round(cur["score"] - prev["score"])
    score_part = "발음 변화 없음" if ds == 0 else f"발음 {ds:+d}점"
    raw = cur["syl_per_s"] - prev["syl_per_s"]
    dv = round(raw, 1)
    if abs(raw) < 0.1:
        speed_part = "속도 비슷함"
    elif dv > 0:
        speed_part = f"속도 {abs(dv)}음절 빨라짐"
    else:
        speed_part = f"속도 {abs(dv)}음절 느려짐"
    return f"지난 회차보다 {score_part}, {speed_part}"


def _hangul_only(text):
    return [ch for ch in text if 0xAC00 <= ord(ch) <= 0xD7A3]


def frequent_bad_syllables(user_name, top=5):
    """여러 회차에서 자주 틀린 글자 [(글자, 횟수)] — FR-08. 같은 글자는 위치와 상관없이 합쳐요."""
    counts = {}
    with _conn() as con:
        rows = con.execute(
            """SELECT a.bad_syllables, s.text FROM attempts a JOIN scripts s ON s.script_id = a.script_id
               WHERE a.user_name = ?""", (user_name,)).fetchall()
    for r in rows:
        chars = _hangul_only(r["text"])
        for idx in json.loads(r["bad_syllables"] or "[]"):
            if 0 <= idx < len(chars):
                counts[chars[idx]] = counts.get(chars[idx], 0) + 1
    return sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[:top]
