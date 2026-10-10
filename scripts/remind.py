"""달달 디스코드 알림 (GitHub Actions에서 실행, 웹훅 주소는 GitHub Secret에만 있음)
- 30분마다: 새로 본 시험 결과를 올림
- 매일 21:30: 오늘 현황 요약 (월~토)
서비스 계정 키 없이 Firebase 이메일/비밀번호 '봇 계정'으로 로그인해 Firestore REST로 읽는다.
필요한 secrets: BOT_EMAIL, BOT_PASSWORD, DISCORD_WEBHOOK"""
import os, json, datetime, urllib.request, time

API_KEY = 'AIzaSyAAfmby4xi5AeCFyOE8UIhDJoNXT6MZmp0'
PROJECT = 'daldal-a4dcc'
BASE = f'https://firestore.googleapis.com/v1/projects/{PROJECT}/databases/(default)/documents'
KST = datetime.timezone(datetime.timedelta(hours=9))
now = datetime.datetime.now(KST)
MODE = os.environ.get('MODE', 'results')       # results | daily

def http(url, data=None, token=None, method=None):
    h = {'Content-Type': 'application/json', 'User-Agent': 'daldal-remind'}
    if token: h['Authorization'] = 'Bearer ' + token
    req = urllib.request.Request(url, data=json.dumps(data).encode() if data is not None else None, headers=h, method=method)
    with urllib.request.urlopen(req) as r:
        b = r.read(); return json.loads(b) if b else {}

def val(v):
    if 'mapValue' in v: return {k: val(x) for k, x in v['mapValue'].get('fields', {}).items()}
    if 'arrayValue' in v: return [val(x) for x in v['arrayValue'].get('values', [])]
    if 'integerValue' in v: return int(v['integerValue'])
    if 'doubleValue' in v: return v['doubleValue']
    if 'nullValue' in v: return None
    for k in ('stringValue', 'booleanValue', 'timestampValue'):
        if k in v: return v[k]
    return None
def doc(d): return {k: val(x) for k, x in d.get('fields', {}).items()}
def say(msg): http(os.environ['DISCORD_WEBHOOK'], {'content': msg[:1900]}); print(msg)

auth = http(f'https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={API_KEY}',
            {'email': os.environ['BOT_EMAIL'], 'password': os.environ['BOT_PASSWORD'], 'returnSecureToken': True})
tok, uid = auth['idToken'], auth['localId']
try: me = doc(http(f'{BASE}/users/{uid}', token=tok))
except Exception: me = {}
last = int(me.get('lastPosted') or 0)
if me.get('role') != 'admin':
    http(f'{BASE}/users/{uid}?updateMask.fieldPaths=role&updateMask.fieldPaths=name',
         {'fields': {'role': {'stringValue': 'admin'}, 'name': {'stringValue': '알림봇'}}}, tok, 'PATCH')

# 1. 새 시험 결과 (지난번 이후)
if last == 0: last = int(time.time() * 1000) - 30 * 60 * 1000
q = {'structuredQuery': {'from': [{'collectionId': 'events'}],
     'where': {'fieldFilter': {'field': {'fieldPath': 'at'}, 'op': 'GREATER_THAN', 'value': {'integerValue': str(last)}}},
     'orderBy': [{'field': {'fieldPath': 'at'}}]}}
evs = [doc(r['document']) for r in http(f'{BASE}:runQuery', q, tok) if 'document' in r]
for e in evs:
    w = e.get('wrong') or []
    say(f'📘 **{e.get("name")}** · {e.get("title")} · **{e.get("score")}점** ({e.get("c")}/{e.get("n")})'
        + (f'\n틀린 단어: {", ".join(w)}' if w else ' · 전부 정답 🎉'))
    last = max(last, int(e.get('at') or 0))
http(f'{BASE}/users/{uid}?updateMask.fieldPaths=lastPosted', {'fields': {'lastPosted': {'integerValue': str(last)}}}, tok, 'PATCH')

# 2. 저녁 요약
if MODE == 'daily':
    today = now.date(); key = today.isoformat(); dow = (today.weekday() + 1) % 7
    if dow == 0 and not os.environ.get('FORCE'): raise SystemExit('일요일은 쉼')
    q = {'structuredQuery': {'from': [{'collectionId': 'users'}],
         'where': {'fieldFilter': {'field': {'fieldPath': 'role'}, 'op': 'EQUAL', 'value': {'stringValue': 'student'}}}}}
    lines = []
    for r in http(f'{BASE}:runQuery', q, tok):
        if 'document' not in r: continue
        sid = r['document']['name'].split('/')[-1]; name = doc(r['document']).get('name', sid)
        try: p = doc(http(f'{BASE}/progress/{sid}', token=tok))
        except Exception: p = {}
        day = (p.get('days') or {}).get(key) or {}; t = day.get('test')
        if p.get('lo') is None:  lines.append(f'⚪ **{name}** — 아직 레벨 테스트를 안 봤어요')
        elif t:                  lines.append(f'✅ **{name}** — {t.get("score")}점 ({t.get("c")}/{t.get("n")}) · {p.get("streak", 0)}일 연속')
        elif day.get('learned'): lines.append(f'🟡 **{name}** — 외우기는 했는데 시험을 아직 안 봤어요')
        else:                    lines.append(f'🔴 **{name}** — 오늘 공부 안 함')
    say(f'📒 **달달 {today.month}/{today.day} ({"일월화수목금토"[dow]})**\n' + ('\n'.join(lines) or '아직 로그인한 아이가 없어요'))
