"""매일 밤 실행: 오늘 공부(시험)를 안 한 아이를 디스코드로 알림. GitHub Actions 크론에서 돌아감.
필요한 secrets: FIREBASE_SA (서비스 계정 JSON 전체), DISCORD_WEBHOOK"""
import os, json, datetime, urllib.request
import firebase_admin
from firebase_admin import credentials, firestore

KST = datetime.timezone(datetime.timedelta(hours=9))
today = datetime.datetime.now(KST).date()
key = today.isoformat(); dow = (today.weekday() + 1) % 7   # 0 일 … 6 토
if dow == 0: raise SystemExit('일요일은 쉼')

cred = credentials.Certificate(json.loads(os.environ['FIREBASE_SA']))
firebase_admin.initialize_app(cred); db = firestore.client()
hook = os.environ['DISCORD_WEBHOOK']

lines = []
for u in db.collection('users').where('role', '==', 'student').stream():
    name = u.to_dict().get('name', u.id)
    p = db.collection('progress').document(u.id).get().to_dict() or {}
    day = (p.get('days') or {}).get(key) or {}
    if p.get('lo') is None:
        lines.append(f'⚪ **{name}** — 아직 레벨 테스트를 안 봤어요')
    elif day.get('test'):
        lines.append(f'✅ **{name}** — {day["test"]["score"]}점 ({day["test"]["c"]}/{day["test"]["n"]}) · {p.get("streak",0)}일 연속')
    elif day.get('learned'):
        lines.append(f'🟡 **{name}** — 외우기는 했는데 시험을 아직 안 봤어요')
    else:
        lines.append(f'🔴 **{name}** — 오늘 공부 안 함')

msg = f'📒 **달달 {today.month}/{today.day} ({"일월화수목금토"[dow]})**\n' + '\n'.join(lines)
req = urllib.request.Request(hook, data=json.dumps({'content': msg}).encode(), headers={'Content-Type': 'application/json'})
urllib.request.urlopen(req); print(msg)
