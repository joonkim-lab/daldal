"""달달 디스코드 알림 (GitHub Actions에서 30분마다 실행. 웹훅 주소는 GitHub Secret에만 있음)
- 오늘의 시험 끝남 알림 (점수는 안 올림) + 연속 기록 ('시험 완료', '연속')
- 22:00~07:00에는 보내지 않음
- 정해진 시각에 독촉 (messages.json '독촉')
- 매일 21:30 오늘 현황 요약 (월~토)
봇 계정(이메일/비밀번호)으로 로그인해 Firestore REST로 읽는다.
secrets: BOT_EMAIL, BOT_PASSWORD, DISCORD_WEBHOOK"""
import os, json, datetime, urllib.request, urllib.error, time, random, pathlib

API_KEY = 'AIzaSyAAfmby4xi5AeCFyOE8UIhDJoNXT6MZmp0'
PROJECT = 'daldal-a4dcc'
BASE = f'https://firestore.googleapis.com/v1/projects/{PROJECT}/databases/(default)/documents'
KST = datetime.timezone(datetime.timedelta(hours=9))
now = datetime.datetime.now(KST); today = now.date(); key = today.isoformat(); dow = (today.weekday() + 1) % 7
MODE = os.environ.get('MODE', 'results')
M = json.load(open(pathlib.Path(__file__).resolve().parent.parent / 'messages.json', encoding='utf-8'))
IDS = {k: v for k, v in (M.get('discord_id') or {}).items() if v}

def http(url, data=None, token=None, method=None):
    h = {'Content-Type': 'application/json', 'User-Agent': 'daldal-remind'}
    if token: h['Authorization'] = 'Bearer ' + token
    req = urllib.request.Request(url, data=json.dumps(data).encode() if data is not None else None, headers=h, method=method)
    try:
        with urllib.request.urlopen(req) as r:
            b = r.read(); return json.loads(b) if b else {}
    except urllib.error.HTTPError as e:
        print('HTTP', e.code, url.split('?')[0], e.read().decode('utf-8', 'replace')[:500]); raise
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
def say(msg): http(os.environ['DISCORD_WEBHOOK'], {'content': msg[:1900], 'allowed_mentions': {'parse': ['users']}}); print(msg)
def fill(t, name, **kw):
    t = t.replace('{멘션}', f'<@{IDS[name]}>' if name in IDS else f'**{name}**').replace('{이름}', name)
    for k, v in kw.items(): t = t.replace('{' + k + '}', str(v))
    return t
def pick(lst, name, **kw): return fill(random.choice(lst), name, **kw) if lst else None

# 조용한 시간(22:00~07:00)에는 아무것도 보내지 않음. 밀린 알림은 아침 7시 이후에 나감
if (now.hour >= 22 or now.hour < 7) and not os.environ.get('FORCE'):
    print('조용한 시간 — 건너뜀'); raise SystemExit(0)

auth = http(f'https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={API_KEY}',
            {'email': os.environ['BOT_EMAIL'], 'password': os.environ['BOT_PASSWORD'], 'returnSecureToken': True})
tok, uid = auth['idToken'], auth['localId']
try: me = doc(http(f'{BASE}/users/{uid}', token=tok))
except Exception: me = {}
if me.get('role') != 'admin':
    http(f'{BASE}/users/{uid}?updateMask.fieldPaths=role&updateMask.fieldPaths=name',
         {'fields': {'role': {'stringValue': 'admin'}, 'name': {'stringValue': '알림봇'}}}, tok, 'PATCH')
last = int(me.get('lastPosted') or 0) or int(time.time() * 1000) - 30 * 60 * 1000
sent = me.get('sentSlots') or {}
sent_today = set(sent.get(key) or [])

# 학생 + 진도
q = {'structuredQuery': {'from': [{'collectionId': 'users'}],
     'where': {'fieldFilter': {'field': {'fieldPath': 'role'}, 'op': 'EQUAL', 'value': {'stringValue': 'student'}}}}}
kids = []
for r in http(f'{BASE}:runQuery', q, tok):
    if 'document' not in r: continue
    sid = r['document']['name'].split('/')[-1]; name = doc(r['document']).get('name', sid)
    try: p = doc(http(f'{BASE}/progress/{sid}', token=tok))
    except Exception: p = {}
    day = (p.get('days') or {}).get(key) or {}
    nvalid = len([x for x in (p.get('placements') or []) if x.get('valid')])
    state = '레벨 전' if nvalid < 3 else '함' if day.get('test') else '외우기만' if day.get('learned') else '안 함'
    kids.append({'id': sid, 'name': name, 'p': p, 'day': day, 'state': state})
byid = {k['id']: k for k in kids}

# 1. 오늘의 시험 끝남 알림 (점수·틀린 단어는 채널에 올리지 않음 — 관리자 화면에서만 봄)
q = {'structuredQuery': {'from': [{'collectionId': 'events'}],
     'where': {'fieldFilter': {'field': {'fieldPath': 'at'}, 'op': 'GREATER_THAN', 'value': {'integerValue': str(last)}}},
     'orderBy': [{'field': {'fieldPath': 'at'}}]}}
for r in http(f'{BASE}:runQuery', q, tok):
    if 'document' not in r: continue
    e = doc(r['document']); name = e.get('name'); last = max(last, int(e.get('at') or 0))
    if e.get('kind') != 'daily': continue          # 다시 풀기·결과지·지정 시험 등은 채널에 안 올림
    lines = [pick(M.get('시험 완료') or ['✅ {멘션} 오늘 단어 시험 끝! 👏'], name)]
    k = byid.get(e.get('uid')); st = (k['p'].get('streak') if k else 0) or 0
    if st in (M.get('연속', {}).get('날짜') or []):
        lines.append(pick(M['연속'].get('문구'), name, 연속=st))
    say('\n'.join(x for x in lines if x))

# 1-2. 레벨 테스트 다음 회차 열림 / 3회 완료 알림
GAP = 3 * 60 * 60 * 1000; nowms = int(time.time() * 1000)
place_sent = set(me.get('placeNotified') or [])
LT = M.get('레벨 테스트', {})
for k in kids:
    pl = k['p'].get('placements') or []; valid = [x for x in pl if x.get('valid')]; n = len(valid)
    if not pl: continue
    if n >= 3:
        tag = f'{k["id"]}:done'
        if tag not in place_sent:
            say(pick(LT.get('완료') or ['{멘션} 레벨 테스트 3번 끝!'], k['name'])); place_sent.add(tag)
        continue
    lastp = pl[-1]
    if lastp.get('valid') and nowms >= int(lastp.get('at') or 0) + GAP:
        tag = f'{k["id"]}:{n + 1}'
        if tag not in place_sent:
            say(pick(LT.get('열림') or ['{멘션} 레벨 테스트 {회차}회차가 열렸어!'], k['name'], 회차=n + 1)); place_sent.add(tag)

# 1-3. 레벨 테스트 독촉 (회차가 열려 있는 아이, 정해진 시각, 일요일 포함). 시작 48시간 넘으면 더 세게
LD = LT.get('독촉') or {}
for t_str in LD.get('시각', []):
    hh, mm = map(int, t_str.split(':')); t0 = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
    tag = f'place@{t_str}'
    if not (t0 <= now < t0 + datetime.timedelta(minutes=60)) or tag in sent_today: continue
    for k in kids:
        pl = k['p'].get('placements') or []; valid = [x for x in pl if x.get('valid')]; n = len(valid)
        if n >= 3: continue
        if pl and pl[-1].get('valid') and nowms < int(pl[-1].get('at') or 0) + GAP: continue   # 아직 잠김
        first = int(pl[0].get('at') or 0) if pl else 0
        late = first and nowms - first > 48 * 3600 * 1000
        say(pick(LD.get('이틀 지남') if late else LD.get('문구'), k['name'], 회차=n + 1, 남은=3 - n))
    sent_today.add(tag)

# 2. 독촉 (일요일 제외, 시각이 지났고 1시간 안이며 오늘 아직 안 보낸 것)
if dow != 0:
    for i, rule in enumerate(M.get('독촉', [])):
        hh, mm = map(int, rule['시각'].split(':'))
        t0 = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
        tag = f'{i}@{rule["시각"]}'
        if not (t0 <= now < t0 + datetime.timedelta(minutes=60)) or tag in sent_today: continue
        for k in kids:
            if k['state'] == rule.get('대상'): say(pick(rule.get('문구'), k['name']))
        sent_today.add(tag)

# 3. 저녁 요약
if MODE == 'daily' and (dow != 0 or os.environ.get('FORCE')):
    icon = {'레벨 전': '⚪', '함': '✅', '외우기만': '🟡', '안 함': '🔴'}
    lines = []
    for k in kids:
        t = k['day'].get('test') or {}
        nv = len([x for x in (k['p'].get('placements') or []) if x.get('valid')])
        pl0 = (k['p'].get('placements') or [{}])[0].get('at') if k['p'].get('placements') else 0
        late = ' ⚠️ 시작한 지 이틀 넘음' if pl0 and int(time.time()*1000) - int(pl0) > 48*3600*1000 else ''
        detail = {'레벨 전': f'레벨 테스트 {nv}/3' + late, '외우기만': '외우기는 했는데 시험을 아직 안 봤어요', '안 함': '오늘 공부 안 함',
                  '함': f'오늘 공부 끝 · {k["p"].get("streak", 0)}일 연속'}[k['state']]
        lines.append(f'{icon[k["state"]]} **{k["name"]}** — {detail}')
    say(f'📒 **달달 {today.month}/{today.day} ({"일월화수목금토"[dow]})**\n' + ('\n'.join(lines) or '아직 로그인한 아이가 없어요'))

# 상태 저장
slots = {'mapValue': {'fields': {key: {'arrayValue': {'values': [{'stringValue': s} for s in sorted(sent_today)]}}}}}
http(f'{BASE}/users/{uid}?updateMask.fieldPaths=lastPosted&updateMask.fieldPaths=sentSlots',
     {'fields': {'lastPosted': {'integerValue': str(last)}, 'sentSlots': slots}}, tok, 'PATCH')
http(f'{BASE}/users/{uid}?updateMask.fieldPaths=placeNotified',
     {'fields': {'placeNotified': {'arrayValue': {'values': [{'stringValue': x} for x in sorted(place_sent)]}}}}, tok, 'PATCH')
