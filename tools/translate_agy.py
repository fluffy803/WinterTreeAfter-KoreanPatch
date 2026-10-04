# -*- coding: utf-8 -*-
"""agy(Antigravity CLI) 위임 번역 드라이버.
units.jsonl -> (배치) -> agy -> 검증 -> translations.jsonl (재개 가능).
사용: python translate_agy.py [batch=45] [--limit N배치] [--model ID]
"""
import os, re, json, sys, subprocess, tempfile, time

# 작업 폴더(_work/ 가 있는 곳). 기본값은 저장소 폴더.
ROOT = os.environ.get("WTA_WORKSPACE") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UNITS = os.path.join(ROOT, "_work", "units.jsonl")
OUTF  = os.path.join(ROOT, "_work", "translations.jsonl")
AGY   = os.environ.get("AGY_EXE") or "agy"
MODEL = "claude-opus-4-6-thinking"

GLOSSARY = """[고유명사] 言叶=코토바 / 小忆=코이 / 小亦=코이 / 言叶&小忆=코토바&코이 / 安深=안선 / sensei=sensei(로마자 그대로) / 小白=샤오바이 / 白=바이 / 黑=헤이 / 裕=위 / 绫=링 / 老徐=라오쉬 / 天使=천사 / 猫·猫咪=고양이 / 医生=의사 / 护士=간호사 / 老奶奶=할머니 / 司机=기사 / 店员=점원
[스타일] 久琉霧 제작 비주얼노벨 AFTER편. 성인물 아님(로맨스·드라마·판타지). 문학적이고 자연스러운 한국어. 지문은 과거형 평서체(나는 ~했다), 대사는 캐릭터 말투. 코토바·코이는 어린 소녀처럼 귀엽고 발랄한 반말. 주인공(나)은 차분한 성인 남성. 1인칭 我=나. 대사 속 sensei는 로마자 유지. 吾(코이의 예스러운 1인칭)=나.
[규칙] 중국어 인용부호 " " 『 』 【 】 유지. 태그 [p] [emb exp="..."] [l] [r] 등은 위치·형태 그대로 보존(번역은 태그 사이 중국어만). 줄 1:1 유지. URL·인명/회사명(久琉霧,MagicaLuv,yoe awa 등)은 음역 말고 원문 유지."""

PROMPT_HEAD = GLOSSARY + """

★인명은 위 표기만 사용(강제): 言叶는 반드시 '코토바'(절대 '코토노하'·'옌예' 금지), 小忆·小亦는 반드시 '코이'(절대 '샤오이' 금지), 安深은 '안선', sensei는 로마자 'sensei' 그대로.
아래 번호별 중국어 줄을 한국어로 번역하라. 각 줄을 정확히 "번호|번역문" 형식 한 줄로만 출력(번역문 안에 | 사용 금지). 설명·머리말 없이 번역 결과만. 줄 끝의 [p] 등 태그는 원문과 동일하게 유지.

"""

TAG_RE = re.compile(r'\[[^\]]*\]')
CJK = re.compile(r'[\u4e00-\u9fff\u3400-\u4dbf]')

def load_units():
    us = []
    for ln in open(UNITS, encoding='utf-8'):
        ln = ln.strip()
        if ln: us.append(json.loads(ln))
    return us

def load_done():
    done = {}
    if os.path.exists(OUTF):
        for ln in open(OUTF, encoding='utf-8'):
            ln = ln.strip()
            if ln:
                d = json.loads(ln); done[d['id']] = d
    return done

def tags_of(s):
    return sorted(TAG_RE.findall(s))

def call_agy(prompt, model):
    with tempfile.NamedTemporaryFile('w', suffix='.txt', delete=False, encoding='utf-8') as t:
        t.write(prompt); tp = t.name
    try:
        txt = open(tp, encoding='utf-8').read()
        p = subprocess.run([AGY, "-p", txt, "--model", model],
                           capture_output=True, text=True, encoding='utf-8',
                           errors='replace', timeout=240)
        return (p.stdout or "") + "\n" + (p.stderr or "")
    except subprocess.TimeoutExpired:
        return "__TIMEOUT__"
    finally:
        try: os.unlink(tp)
        except: pass

def parse(out, n):
    res = {}
    for ln in out.splitlines():
        m = re.match(r'\s*(\d+)\s*\|(.*)$', ln)
        if m:
            res[int(m.group(1))] = m.group(2)
    return res

def validate(src, tgt):
    # 태그 보존 검사
    if tags_of(src) != tags_of(tgt):
        return "tag"
    if CJK.search(tgt):
        return "cjk"
    if not tgt.strip():
        return "empty"
    return None

def main():
    bs = 45; limit = None; model = MODEL
    args = sys.argv[1:]
    i = 0
    while i < len(args):
        a = args[i]
        if a == '--limit': limit = int(args[i+1]); i += 2
        elif a == '--model': model = args[i+1]; i += 2
        elif a.isdigit(): bs = int(a); i += 1
        else: i += 1

    units = load_units()
    done = load_done()
    todo = [u for u in units if u['id'] not in done]
    print(f"units={len(units)} done={len(done)} todo={len(todo)} batch={bs} model={model}")

    # 파일 순서 유지한 배치
    batches = [todo[k:k+bs] for k in range(0, len(todo), bs)]
    if limit: batches = batches[:limit]

    QUOTA_PAT = re.compile(r'\bquota\b|rate.?limit|Resets in|Too Many Requests|\bexhausted\b|unauthorized|Individual quota|Error:', re.I)
    of = open(OUTF, 'a', encoding='utf-8')
    fail_log = open(os.path.join(ROOT, "_work", "translate_fail.log"), 'a', encoding='utf-8')
    consec_fail = 0
    for bi, batch in enumerate(batches):
        prompt = PROMPT_HEAD + "\n".join(f"{j+1}. {u['src']}" for j, u in enumerate(batch))
        t0 = time.time()
        out = call_agy(prompt, model)
        # 쿼터/타임아웃 조기 감지 → 즉시 중단(백그라운드 종료→알림)
        if out == "__TIMEOUT__" or QUOTA_PAT.search(out or ""):
            reason = "TIMEOUT" if out == "__TIMEOUT__" else "QUOTA/ERROR"
            print(f"!!! ABORT at batch {bi+1}: {reason}. done={len(done)+sum(1 for _ in open(OUTF,encoding='utf-8'))}")
            print("    agy output head:", (out or "")[:300].replace('\n',' '))
            of.close(); fail_log.close()
            sys.exit(2)
        res = parse(out, len(batch))
        ok = 0; bad = []
        for j, u in enumerate(batch):
            tgt = res.get(j+1)
            if tgt is None:
                bad.append((u, "missing")); continue
            err = validate(u['src'], tgt)
            if err:
                bad.append((u, err)); continue
            of.write(json.dumps({"id": u['id'], "file": u['file'], "kind": u['kind'],
                                 "src": u['src'], "tgt": tgt}, ensure_ascii=False) + "\n")
            ok += 1
        of.flush()
        dt = time.time() - t0
        print(f"batch {bi+1}/{len(batches)} ok={ok}/{len(batch)} bad={len(bad)} {dt:.0f}s", flush=True)
        for u, why in bad:
            fail_log.write(f"{u['id']}\t{why}\t{u['src']}\n")
        fail_log.flush()
        # 전량 실패가 연속 2회면 중단(빈 응답/차단 추정)
        if ok == 0:
            consec_fail += 1
            if consec_fail >= 2:
                print(f"!!! ABORT: {consec_fail} consecutive empty batches (quota/block 추정)", flush=True)
                of.close(); fail_log.close(); sys.exit(3)
        else:
            consec_fail = 0
    of.close(); fail_log.close()
    print("done")

if __name__ == "__main__":
    main()
