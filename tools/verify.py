# -*- coding: utf-8 -*-
"""번역 검증: 커버리지 / 태그 보존 / 중국어 잔재 / 화자 태그 미치환 / 줄수."""
import os, re, json

# 작업 폴더(_work/ 가 있는 곳). 기본값은 저장소 폴더.
ROOT = os.environ.get("WTA_WORKSPACE") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UNITS = os.path.join(ROOT, "_work", "units.jsonl")
TR   = os.path.join(ROOT, "_work", "translations.jsonl")
REB  = os.path.join(ROOT, "_work", "rebuilt", "data", "scenario")
SCEN = os.path.join(ROOT, "_work", "extracted", "data", "scenario")

TAG_RE = re.compile(r'\[[^\]]*\]')
CJK = re.compile(r'[一-鿿㐀-䶿]')
REPORT = os.path.join(ROOT, "_work", "verify_report.txt")

def main():
    units = [json.loads(l) for l in open(UNITS, encoding='utf-8') if l.strip()]
    tr = {}
    for l in open(TR, encoding='utf-8'):
        if l.strip():
            d = json.loads(l); tr[d['id']] = d
    R = []
    # 1) 커버리지
    missing = [u for u in units if u['id'] not in tr]
    R.append(f"units={len(units)} translated={len(tr)} missing={len(missing)}")
    for u in missing[:40]:
        R.append(f"  MISSING {u['id']}  {u['src'][:50]}")
    # 2) 태그 보존 / 중국어 잔재
    tagbad = 0; cjkbad = 0
    for u in units:
        d = tr.get(u['id'])
        if not d: continue
        if sorted(TAG_RE.findall(u['src'])) != sorted(TAG_RE.findall(d['tgt'])):
            tagbad += 1
            if tagbad <= 20: R.append(f"  TAG   {u['id']}  src={u['src'][:40]} | tgt={d['tgt'][:40]}")
        if CJK.search(d['tgt']):
            cjkbad += 1
            if cjkbad <= 30: R.append(f"  CJK   {u['id']}  {d['tgt'][:60]}")
    R.append(f"tag-mismatch={tagbad} cjk-residual={cjkbad}")
    # 3) rebuilt 줄수/화자 점검
    if os.path.isdir(REB):
        for fn in sorted(os.listdir(REB)):
            if not fn.endswith('.ks'): continue
            o = open(os.path.join(SCEN, fn), encoding='utf-8').read().split('\n')
            n = open(os.path.join(REB, fn), encoding='utf-8').read().split('\n')
            flag = "" if len(o) == len(n) else f" !!LINECOUNT {len(o)}->{len(n)}"
            # 미치환 화자(중국어 남은 #)
            badspk = [ln for ln in n if ln.strip().startswith('#') and CJK.search(ln)]
            R.append(f"  {fn:16} lines {len(o)}->{len(n)}{flag}  중국어화자남음={len(badspk)}")
            for b in badspk[:5]:
                R.append(f"       speaker? {b.strip()[:30]}")
    open(REPORT, 'w', encoding='utf-8').write('\n'.join(R))
    print('\n'.join(R[:60]))
    print("... full ->", REPORT)

if __name__ == "__main__":
    main()
