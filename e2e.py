from playwright.sync_api import sync_playwright
fails=[]
def ck(n,c,x=''): print(('PASS ' if c else 'FAIL ')+n+((' — '+str(x)) if x and not c else '')); 
def ck(n,c,x=''):
    print(('PASS ' if c else 'FAIL ')+n+((' — '+str(x)[:200]) if (x and not c) else ''))
    if not c: fails.append(n)
U='http://localhost:8765/index.html'
with sync_playwright() as pw:
    b=pw.chromium.launch(args=['--no-sandbox']); ctx=b.new_context(viewport={'width':390,'height':800}); pg=ctx.new_page()
    errs=[]; pg.on('pageerror',lambda e:errs.append(str(e)))
    pg.goto(U); pg.wait_for_timeout(1500)
    ck('로그인 화면', '달달' in pg.inner_text('#app'))
    pg.fill('#ln','E2E'); pg.click("text=학생으로 시작"); pg.wait_for_timeout(600)
    ck('홈: 레벨 테스트 안내', '레벨 테스트 3번' in pg.inner_text('#app') and '하루 20단어' in pg.inner_text('#app'))
    def run_place():
        n=0
        while pg.query_selector('.wcard .word') and n<200:
            w=pg.inner_text('.wcard .word').strip(); i=pg.evaluate("w=>BYW[w]?BYW[w].i:-1",w)
            pg.click('.pair .yes' if 0<=i<1500 else '.pair .no'); n+=1
        return n
    pg.click("text=1회차 시작"); pg.wait_for_timeout(300); pg.click("#app >> text=1회차 시작"); pg.wait_for_timeout(300)
    n=run_place(); ck('배치 110문항', n==110, n)
    t=pg.inner_text('#app'); ck('결과 화면 (레벨 숨김)', '1 / 3회 완료' in t and 'B1' not in t and 'B2' not in t, t[:100])
    R=pg.evaluate("S.placements[0].R"); ck('경계 ≈1500 (got %s)'%R, abs(R-1500)<450)
    ck('2회차 잠김(3시간)', '2회차는' in t and '부터' in t)
    pg.click("text=홈으로"); pg.wait_for_timeout(300)
    ck('홈: 공부 잠김', '1 / 3' in pg.inner_text('#app') and '오늘의' not in pg.inner_text('#app'))
    for k in (2,3):
        pg.evaluate("S.placements[S.placements.length-1].at -= 4*3600*1000; render()"); pg.wait_for_timeout(300)
        pg.click(f"text={k}회차 시작"); pg.wait_for_timeout(300); pg.click(f"#app >> text={k}회차 시작"); pg.wait_for_timeout(300)
        run_place()
        if k<3: pg.click("text=홈으로"); pg.wait_for_timeout(300)
    ck('3회차 실재어 겹침 없음', pg.evaluate("(()=>{const a=S.placements.flatMap(p=>p.items).filter(w=>BYW[w]); return new Set(a).size===a.length})()"))
    ck('3회 기록', pg.evaluate("validN()")==3)
    ck('결과지 생성', pg.evaluate("!!S.report && S.report.plan.length==2 && !S.reportReleased"))
    ck('결과 화면: 부모 확인 안내', '엄마·아빠가 먼저 확인' in pg.inner_text('#app'))
    pg.click("text=공부 시작하기"); pg.wait_for_timeout(500)
    ck('홈: 회색 구역 안내', '경계 근처 확인' in pg.inner_text('#app'))
    lo,hi=pg.evaluate("[S.lo,S.hi]"); ck('구역 lo<hi', lo<hi, (lo,hi))
    pg.click("text=확인 시작"); pg.wait_for_timeout(300)
    k=0
    while pg.query_selector('.pair .yes') and k<2000:
        pg.click('.pair .yes' if k%2 else '.pair .no'); k+=1
    ck('회색 구역 %d개 처리 후 홈'%k, k==hi-lo and '오늘의' in pg.inner_text('#app') or '쉬는 날' in pg.inner_text('#app') or '주간 복습' in pg.inner_text('#app'), pg.inner_text('#app')[:200])
    # 강제로 월요일 하루 생성
    pg.evaluate("ensureDay('2026-10-12')"); nw=pg.evaluate("S.days['2026-10-12'].words.length"); ck('월요일 20단어', nw==20, nw)
    pg.evaluate("Study.start('2026-10-12')"); pg.wait_for_timeout(300)
    ck('학습 카드', pg.query_selector('.wcard .word') is not None)
    pg.click('.wcard'); pg.wait_for_timeout(100); ck('뜻 표시(한글+영영)', pg.query_selector('.wcard .ko') and pg.query_selector('.wcard .en'))
    pg.click(".seg button:has-text('한글'):not(:has-text('영영'))"); pg.wait_for_timeout(150); ck('한글만 토글', pg.query_selector('.wcard .ko') is not None and pg.query_selector('.wcard .en') is None)
    m=0
    while pg.query_selector('.wcard') and m<100:
        if not pg.query_selector('.pair .yes'): pg.click('.wcard'); pg.wait_for_timeout(30)
        pg.click('.pair .yes'); m+=1; pg.wait_for_timeout(30)
    ck('외우기 완료 → 시험 안내', '시험 보기' in pg.inner_text('#app'))
    pg.click("text=시험 보기"); pg.wait_for_timeout(300); q=0
    while q<40:
        if pg.query_selector('.choices button:not([disabled])'):
            pg.evaluate("Test.pick(Test.qs[Test.idx].choices.indexOf(Test.qs[Test.idx].a))")
        elif pg.query_selector('#spell:not([disabled])'):
            a=pg.evaluate("Test.qs[Test.idx].a"); pg.fill('#spell', a if q%5 else 'wrong'); pg.press('#spell','Enter')
        else: break
        pg.wait_for_timeout(120)
        if not pg.query_selector("text=다음"): print('DEBUG', q, pg.inner_text('#app')[:300], pg.evaluate("Test.submitted"), errs); break
        pg.click("text=다음"); pg.wait_for_timeout(80); q+=1
    t=pg.inner_text('#app'); ck('시험 20문제 후 점수', q==20 and '점' in t, (q,t[:80]))
    sc=pg.evaluate("S.days['2026-10-12'].test.score"); ck('점수 기록 (%s)'%sc, 80<=sc<100)
    ck('오답 기록', pg.evaluate("Object.keys(S.wrong).length")>=1)
    pg.click("text=홈으로"); pg.wait_for_timeout(400)
    pg.click("nav button:has-text('단어장')"); pg.wait_for_timeout(300); pg.fill('input.field','absor'); pg.wait_for_timeout(200)
    ck('단어장 검색', 'absorb' in pg.inner_text('#app'))
    # 관리자
    pg.click("nav button:has-text('설정')"); pg.wait_for_timeout(200); pg.click("text=로그아웃"); pg.wait_for_timeout(300)
    pg.fill('#ln','Dad'); pg.click("text=관리자로 시작"); pg.wait_for_timeout(800)
    t=pg.inner_text('#app'); ck('관리: 학생 현황', 'E2E' in t and '레벨' in t, t[:200])
    ck('관리: 결과지 확인 대기', '확인 대기' in pg.inner_text('#app'))
    pg.click("#adm .btn.xs"); pg.wait_for_timeout(300)
    mt=pg.inner_text('.modal'); ck('관리: 결과지 내용', 'CEFR 등급표' in mt and '앞으로의 계획' in mt and '듀오링고' in mt, mt[:200])
    pg.click("#rel-btn"); pg.wait_for_timeout(800)
    ck('관리: 공개됨', '아이에게 공개됨' in pg.inner_text('#app'))
    pg.click("text=시험 만들기"); pg.wait_for_timeout(500); pg.fill('#t-title','E2E 시험'); pg.click("#t-type button:has-text('철자')"); pg.click("#t-src button:has-text('등급 전체')"); pg.fill('#t-count','10')
    pg.click("#adm .btn"); pg.wait_for_timeout(800)
    t=pg.inner_text('#app'); ck('시험 생성 → 결과 탭', 'E2E 시험' in t and '아직' in t, t[:200])
    tid=pg.evaluate("Admin.tests[0].id")
    pg.click("nav button:has-text('설정')"); pg.wait_for_timeout(200); pg.click("text=로그아웃"); pg.wait_for_timeout(300)
    pg.fill('#ln','E2E'); pg.click("text=학생으로 시작"); pg.wait_for_timeout(800)
    ck('홈: 지정 시험 표시', 'E2E 시험' in pg.inner_text('#app'))
    ck('홈: 결과지 도착', '결과지 도착' in pg.inner_text('#app'), (pg.inner_text('#app')[:300], pg.evaluate("[S.reportReleased, !!S.report]"), pg.evaluate("(async()=>JSON.stringify(await Store.list('events',['uid','==',USER.uid])))()")))
    pg.click("text=📄 내 결과지 도착! >> xpath=../.. >> button"); pg.wait_for_timeout(300)
    ck('학생: 결과지 보기', 'CEFR 등급표' in pg.inner_text('#app'))
    pg.click("text=닫기"); pg.wait_for_timeout(300)
    pg.goto(U+'#test='+tid); pg.wait_for_timeout(1500)
    ck('링크로 시험 열림', '#spell' and pg.query_selector('#spell') is not None, pg.inner_text('#app')[:100])
    q=0
    while pg.query_selector('#spell:not([disabled])') and q<20:
        a=pg.evaluate("Test.qs[Test.idx].a"); pg.fill('#spell',a); pg.press('#spell','Enter'); pg.wait_for_timeout(80); pg.click("text=다음"); pg.wait_for_timeout(80); q+=1
    ck('지정 시험 10문제', q==10, q)
    r=pg.evaluate("(async()=>{const t=await Store.get('tests','%s'); return t.results})()"%tid)
    ck('결과 저장 (관리자 조회용)', bool(r) and list(r.values())[0]['score']==100, r)
    ck('페이지 오류 없음', not errs, errs[:2])
    b.close()
print('\nE2E: '+('ALL PASS' if not fails else 'FAILED -> '+', '.join(fails)))
