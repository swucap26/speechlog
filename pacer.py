"""스피치로그 가상 페이스메이커 (v3)

사용법 (app.py는 기존 코드 그대로):
    components.html(pacemaker_html(script, target), height=320, scrolling=True)

v3 변경
- 노래방식 그라데이션: 한 글자가 다 칠해지기 전에 다음 글자가 이미 물들기 시작해,
  어절 안에서는 색이 끊기지 않고 미끄러지듯 이어짐
- 자연스러운 호흡: 띄어쓰기마다 짧게, 조사·연결어미 뒤는 조금 더, 쉼표·마침표·줄바꿈은 길게 멈춤
- 사람 말투: 쉬기 직전 글자를 늘이고(말끝 끌기), 글자마다 길이를 아주 조금씩 다르게 함
- 숫자·영어도 대략 읽는 시간만큼 칠해짐
- 목표 시간에 정확히 끝나도록 전체를 자동으로 맞춤.
  목표 시간이 빠듯하면 쉼을 줄여서 글자 속도가 너무 빨라지지 않게 함
- pause=0 이면 쉼 없이 모든 글자가 같은 속도(예전 동작)
"""
import json
import re

_HANGUL = re.compile(r"[가-힣]")


def pacemaker_html(script: str, target: float, pause: float = 1.0, **_ignored) -> str:
    if not script or not _HANGUL.search(script):
        raise ValueError("대본에 한글이 없어 페이스메이커를 만들 수 없습니다.")
    try:
        target = float(target)
    except (TypeError, ValueError):
        raise ValueError("목표 시간이 숫자가 아닙니다.")
    if target <= 0:
        raise ValueError("목표 시간은 0초보다 커야 합니다.")
    try:
        pause = max(0.0, float(pause))
    except (TypeError, ValueError):
        pause = 1.0

    data = json.dumps(
        {"text": script, "target": target, "pause": pause}, ensure_ascii=False
    ).replace("</", "<\\/")
    return _TEMPLATE.replace("__DATA__", data)


_TEMPLATE = r"""<!doctype html>
<html lang="ko"><head><meta charset="utf-8">
<style>
:root{--ink:#31333f;--muted:#808495;--base:#c9c9d1;--hi:#e8457a;--line:#e6e6ea}
*{box-sizing:border-box}
body{margin:0;padding:8px 4px;color:var(--ink);font-family:"Source Sans Pro",-apple-system,"Apple SD Gothic Neo","Noto Sans KR",sans-serif;background:transparent}
.top{display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin-bottom:10px}
button{font:inherit;font-size:14px;padding:6px 14px;border-radius:8px;border:1px solid var(--line);background:#fff;color:var(--ink);cursor:pointer}
button.primary{background:var(--hi);border-color:var(--hi);color:#fff}
#info{font-size:12px;color:var(--muted);margin-left:auto}
#stage{font-size:26px;line-height:1.8;font-weight:600;word-break:keep-all}
.line{min-height:1.8em}
.ch{--p:-35%;background:linear-gradient(90deg,var(--hi) calc(var(--p) - 35%),var(--base) calc(var(--p) + 35%));-webkit-background-clip:text;background-clip:text;color:transparent}
.bar{height:4px;background:var(--line);border-radius:2px;margin-top:10px;overflow:hidden}
.bar i{display:block;height:100%;width:0;background:var(--hi)}
#status{height:22px;font-size:14px;color:var(--hi);margin-top:6px;font-weight:600;transition:opacity .2s}
</style></head>
<body>
<div class="top">
  <button class="primary" id="play">▶ 시작</button>
  <button id="reset">↺ 처음부터</button>
  <span id="info"></span>
</div>
<div id="stage"></div>
<div class="bar"><i id="prog"></i></div>
<div id="status"></div>
<script>
const D = __DATA__;
const $ = s => document.querySelector(s);
const stage = $('#stage'), playBtn = $('#play');

const HANGUL = /[가-힣]/, DIGIT = /[0-9]/, LATIN = /[A-Za-z]/;
const END_P = /[.!?。…]/, COMMA_P = /[,，、:;]/;
// 연결어미 뒤: 숨을 조금 쉬는 자리
const CONNECT = /(는데|지만|니까|면서|도록|려고|어서|아서|해서|여서|으며|하고|이고|되고|으면|하면|되면|이면|라면|다면)$/;
// 조사 뒤: 의미 덩어리가 끝나는 자리
const JOSA = /(에서|에게|께서|으로|부터|까지|에는|에도|처럼|보다|을|를|은|와|과)$/;

// 자연스러운 쉼(초). 기준 말 속도 초당 5.5음절일 때의 길이
const PAUSE_SEC = {word:0.15, josa:0.22, connect:0.3, comma:0.45, sentence:0.7, line:0.9};
// 쉬기 직전 글자 늘림(말끝 끌기)
const LEN = {word:1.08, josa:1.15, connect:1.25, comma:1.3, sentence:1.45, line:1.45};
const LABEL = {word:'', josa:'짧은 숨', connect:'짧은 숨', comma:'쉼표 숨', sentence:'문장 끝 호흡', line:'줄바꿈 호흡'};
const RATE = 5.5;        // 기준 말 속도(쉼 제외, 초당 음절)
const MAX_PAUSE = 0.25;  // 쉼이 전체 시간에서 차지할 수 있는 최대 비율
const OVERLAP = 0.35;    // 앞 글자가 끝나기 전에 다음 글자가 물들기 시작하는 정도
const COUNTDOWN = 3;

let chars = [], pauses = [], total = 0;
let raf = null, t0 = 0, offset = 0, playing = false, done = 0;
const setP = (el, v) => el.style.setProperty('--p', v + '%');

function weightOf(ch){
  if (HANGUL.test(ch)) return 1;
  if (DIGIT.test(ch)) return 1.3;   // 숫자 1개 ≈ 1~2음절
  if (LATIN.test(ch)) return 0.45;  // 영어 2~3글자 ≈ 1음절
  return 0;                          // 문장부호·따옴표
}
// 글자마다 아주 조금 다른 길이(±4%), 매번 같은 결과
const jitter = i => 1 + 0.04 * Math.sin(i * 12.9898 + 4.1414);

function build(){
  const units = [];
  const pushPause = (sec, kind) => {
    if (!units.length || sec <= 0) return;
    const last = units[units.length-1];
    if (last.type === 'pause') { if (sec > last.sec) { last.sec = sec; last.kind = kind; } }
    else units.push({type:'pause', sec, kind});
  };
  const lines = D.text.replace(/\r/g,'').split('\n');
  let ci = 0;
  lines.forEach((line, li) => {
    const lineEl = document.createElement('div');
    lineEl.className = 'line';
    const tokens = line.split(/(\s+)/).filter(Boolean);
    let lastWordIdx = -1;
    tokens.forEach((w, i) => { if (!/^\s+$/.test(w)) lastWordIdx = i; });

    tokens.forEach((w, ti) => {
      if (/^\s+$/.test(w)) { lineEl.appendChild(document.createTextNode(' ')); return; }
      const cs = [...w];
      let lastSp = -1;
      cs.forEach((ch, i) => { if (weightOf(ch) > 0) lastSp = i; });
      const tail = cs.slice(lastSp + 1).join('');
      const core = cs.slice(0, lastSp + 1).join('');
      let kind = END_P.test(tail) ? 'sentence'
               : COMMA_P.test(tail) ? 'comma'
               : CONNECT.test(core) ? 'connect'
               : JOSA.test(core) ? 'josa' : 'word';
      const isLineEnd = ti === lastWordIdx && li < lines.length - 1;
      const lenKey = (isLineEnd && !['sentence','comma'].includes(kind)) ? 'line' : kind;

      let first = true;
      cs.forEach((ch, i) => {
        const span = document.createElement('span');
        span.className = 'ch'; span.textContent = ch;
        lineEl.appendChild(span);
        let w1 = weightOf(ch);
        if (w1 > 0) {
          if (HANGUL.test(ch) && (ch.charCodeAt(0) - 0xAC00) % 28 !== 0) w1 *= 1.08; // 받침
          if (i === lastSp && D.pause > 0) w1 *= LEN[lenKey];
          w1 *= jitter(ci++);
        }
        units.push({type:'ch', el:span, w:w1, hangul:HANGUL.test(ch), wordStart:first && w1 > 0});
        if (w1 > 0) first = false;
      });
      pushPause(PAUSE_SEC[kind] * D.pause, kind);
    });
    if (!tokens.length) lineEl.innerHTML = '&nbsp;';
    stage.appendChild(lineEl);
    if (li < lines.length - 1) pushPause(PAUSE_SEC.line * D.pause, 'line');
  });
  while (units.length && units[units.length-1].type === 'pause') units.pop();

  // 목표 시간에 맞추기
  const speakNat = units.filter(u => u.type === 'ch').reduce((s, u) => s + u.w, 0) / RATE;
  let pauseNat = units.filter(u => u.type === 'pause').reduce((s, u) => s + u.sec, 0);
  let pScale = 1;
  if (pauseNat / (speakNat + pauseNat) > MAX_PAUSE) {               // 쉼이 너무 많으면 줄임
    pScale = (MAX_PAUSE * speakNat) / ((1 - MAX_PAUSE) * pauseNat);
  }
  const k = D.target / (speakNat + pauseNat * pScale);

  let t = 0, speak = 0, n = 0;
  units.forEach(u => {
    u.dur = u.type === 'ch' ? (u.w / RATE) * k : u.sec * pScale * k;
    u.start = t; t += u.dur;
    if (u.type === 'ch') { if (u.hangul) n++; speak += u.dur; chars.push(u); }
    else pauses.push(u);
  });
  total = t;

  // 그라데이션 구간: 어절 안에서는 앞 글자 끝과 다음 글자 시작이 겹치게
  chars.forEach(u => {
    const a = u.dur * OVERLAP;
    u.from = u.wordStart || u.dur === 0 ? u.start : u.start - a;
    u.to = Math.min(total, u.start + u.dur + a);
    if (u.to <= u.from) u.to = u.from + 1e-6;
  });

  $('#info').textContent =
    `${n}음절 · 목표 ${D.target}초 · 평균 초당 ${(n/D.target).toFixed(1)}음절` +
    (D.pause > 0 ? ` (쉼 빼고 읽는 속도 ${(n/speak).toFixed(1)})` : '');
}

function render(t){
  // 다 칠해진 글자는 건너뜀
  while (done < chars.length && t >= chars[done].to) { setP(chars[done].el, 135); done++; }
  for (let j = done; j < chars.length && chars[j].from <= t; j++) {
    const u = chars[j];
    setP(u.el, -35 + 170 * Math.min(1, (t - u.from) / (u.to - u.from)));
  }
  $('#prog').style.width = Math.max(0, Math.min(100, t / total * 100)) + '%';
  const p = pauses.find(u => t >= u.start && t < u.start + u.dur);
  $('#status').textContent = p && LABEL[p.kind] ? `● ${LABEL[p.kind]}` : '';
}

function frame(now){
  const t = offset + (now - t0) / 1000;
  if (t < 0) { $('#status').textContent = `${Math.ceil(-t)}...`; raf = requestAnimationFrame(frame); return; }
  render(t);
  if (t >= total) { finish(); return; }
  raf = requestAnimationFrame(frame);
}

function play(){
  if (!chars.length) return;
  if (done >= chars.length) reset();
  if (offset === 0 && done === 0) offset = -COUNTDOWN;   // 처음 시작이면 3초 카운트다운
  t0 = performance.now(); playing = true;
  playBtn.textContent = '❚❚ 일시정지';
  raf = requestAnimationFrame(frame);
}
function pause(){
  offset += (performance.now() - t0) / 1000;
  cancelAnimationFrame(raf); playing = false;
  playBtn.textContent = '▶ 이어서';
}
function reset(){
  cancelAnimationFrame(raf); playing = false; offset = 0; done = 0;
  chars.forEach(u => setP(u.el, -35));
  $('#prog').style.width = '0%'; $('#status').textContent = '';
  playBtn.textContent = '▶ 시작';
}
function finish(){
  cancelAnimationFrame(raf); playing = false;
  chars.forEach(u => setP(u.el, 135)); done = chars.length;
  $('#status').textContent = '끝';
  playBtn.textContent = '▶ 다시';
}

playBtn.onclick = () => playing ? pause() : play();
$('#reset').onclick = reset;
build();
</script>
</body></html>
"""
