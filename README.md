# 달달 — 외울 때까지, 달달

세 아이용 DET 어휘 앱. 단일 HTML + words.json + Firebase(로그인·저장) + GitHub Pages + GitHub Actions(디스코드 알림).
제작 Educclesia Group. 단어: NGSL/NAWL 1.2 (CC BY-SA 4.0) + Oxford 3000/5000 CEFR 등급(가정용).

## 파일
- `index.html` 앱 전체 (학생 + 관리자)
- `words.json` 단어 5,549개 (A1~C1, 한글 뜻 + 영영 뜻) + 가짜 단어 80개
- `firestore.rules` Firestore 보안 규칙
- `scripts/remind.py` + `.github/workflows/remind.yml` 매일 21:30 미학습 알림
- `e2e.py` 자동 테스트 (`python3 -m http.server 8765` 띄우고 실행) · `index.html?selftest=1` 내장 검사

## 설정 순서 (새 Firebase 프로젝트)
1. console.firebase.google.com → 프로젝트 추가 (Spark 무료면 충분)
2. 빌드 → Authentication → 시작하기 → Google 사용 설정
3. Authentication → 설정 → 승인된 도메인에 `joonkim-lab.github.io` 추가
4. 빌드 → Firestore Database → 데이터베이스 만들기 (프로덕션 모드, 서울 asia-northeast3) → 규칙 탭에 `firestore.rules` 내용 붙여넣기 → 게시
5. 프로젝트 설정 → 일반 → 내 앱 → 웹 앱 추가(</>) → `firebaseConfig` 복사 → `index.html` 맨 위 `CONFIG.firebase`에 붙여넣기
6. `CONFIG.students`에 아이 이메일 3개, `CONFIG.admins`에 부모 이메일 2개
7. (선택) `CONFIG.discordWebhook`에 결과 채널 웹훅 → 시험 결과가 바로 올라감
8. 커밋·푸시 → 저장소 Settings → Pages → main 브랜치 루트 배포

## 알림 (GitHub Actions, 서비스 계정 키 없이)
조직 정책상 서비스 계정 키를 못 만들어서, 이메일/비밀번호 '봇 계정'으로 읽는다.
1. Firebase → Authentication → 로그인 방법 → 이메일/비밀번호 사용 설정
2. Authentication → 사용자 → 사용자 추가 (예: bot@daldal.app / 긴 비밀번호)
3. 저장소 Settings → Secrets → Actions: `BOT_EMAIL`, `BOT_PASSWORD`, `DISCORD_WEBHOOK`
4. Actions 탭 → "달달 저녁 알림" → Run workflow (수동 실행은 일요일에도 돈다)

## 데이터 구조 (Firestore)
- `users/{uid}` {email, name, role}
- `progress/{uid}` {placements[], lo, hi, cefr, diag{}, days{날짜:{words[], learned, test{score,c,n,wrong[]}}}, wrong{}, settings{showEn,newPerDay}, streak}
- `tests/{id}` {title, type(mcq|spell|mix), count, words[], assignedTo[], createdByName, at, results{uid:{score,c,n,wrong[],answers[]}}}
- `events/{id}` {uid, name, kind, title, score, n, c, at}

## 학습 규칙
- 레벨 테스트 110문항(실재어 80 + 가짜 30) 최대 3회 → 유효 회차의 중앙값으로 출발점 확정 → 경계 근처(회색 구역) 단어 O/X 확인
- 월~금 하루 20단어(기본, 자동 조절 15~40): 외우기(카드, 다시/외웠다 반복) → 그날 단어로 시험(객관식·철자 반반)
- 토: 그 주 외운 단어로 복습 시험 30문제 · 일: 쉼
- 틀린 단어는 '틀린 단어' 목록에 쌓이고 맞히면 빠짐
- 관리자: 아이별 현황, 시험 만들기(객관식/철자/섞어서, 배운 단어/등급 전체/직접 입력) → 링크 `#test=ID` → 결과 기록
