# -*- coding: utf-8 -*-
"""에이전트 출력(_work/agent_out/*.out.tsv)을 translations.jsonl 로 병합.
units.jsonl 의 src 로 태그 보존 검증, 기존 done 은 비덮어쓰기, 커버리지/불일치 리포트."""
import os, re, json, glob

# 작업 폴더(_work/ 가 있는 곳). 기본값은 저장소 폴더.
ROOT = os.environ.get("WTA_WORKSPACE") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UNITS = os.path.join(ROOT, "_work", "units.jsonl")
TR   = os.path.join(ROOT, "_work", "translations.jsonl")
OUTD = os.path.join(ROOT, "_work", "agent_out")
TAG_RE = re.compile(r'\[[^\]]*\]')
ID_RE = re.compile(r'^\S+\.ks:\d+(:\d+)?$')
CJK = re.compile(r'[一-鿿㐀-䶿]')

def main():
    units = {}
    for l in open(UNITS, encoding='utf-8'):
        if l.strip():
            u = json.loads(l); units[u['id']] = u
    done = set()
    if os.path.exists(TR):
        for l in open(TR, encoding='utf-8'):
            if l.strip(): done.add(json.loads(l)['id'])

    added = 0; tagbad = []; cjkbad = []; unknown = []; dup = 0
    seen = set()
    with open(TR, 'a', encoding='utf-8') as of:
        for fp in sorted(glob.glob(os.path.join(OUTD, "*.out.tsv"))):
            for l in open(fp, encoding='utf-8'):
                l = l.rstrip('\n')
                if not l.strip() or '\t' not in l: continue
                parts = l.split('\t')
                # 형식1: ID<TAB>TGT  /  형식2: 줄번호<TAB>ID<TAB>TGT
                if len(parts) >= 3 and parts[0].strip().isdigit() and ID_RE.match(parts[1].strip()):
                    i = parts[1].strip(); tgt = '\t'.join(parts[2:])
                else:
                    i = parts[0].strip(); tgt = '\t'.join(parts[1:])
                if i not in units:
                    unknown.append((os.path.basename(fp), i)); continue
                if i in done or i in seen:
                    dup += 1; continue
                src = units[i]['src']
                if sorted(TAG_RE.findall(src)) != sorted(TAG_RE.findall(tgt)):
                    tagbad.append(i)  # 기록만, 그래도 병합(후속 수정 대상)
                if CJK.search(tgt):
                    cjkbad.append(i)
                of.write(json.dumps({"id": i, "file": units[i]['file'], "kind": units[i]['kind'],
                                     "src": src, "tgt": tgt}, ensure_ascii=False) + "\n")
                seen.add(i); added += 1

    # 커버리지
    now_done = done | seen
    missing = [uid for uid in units if uid not in now_done]
    rep = [f"added={added} dup_skipped={dup} tag_mismatch={len(tagbad)} cjk_residual={len(cjkbad)} unknown_id={len(unknown)}",
           f"total_units={len(units)} now_done={len(now_done)} missing={len(missing)}"]
    if tagbad: rep.append("TAGBAD: " + " ".join(tagbad[:30]))
    if cjkbad: rep.append("CJKBAD: " + " ".join(cjkbad[:30]))
    if unknown: rep.append("UNKNOWN: " + " ".join(f"{a}:{b}" for a,b in unknown[:20]))
    if missing: rep.append("MISSING: " + " ".join(missing[:40]))
    print('\n'.join(rep))
    open(os.path.join(ROOT, "_work", "merge_report.txt"), 'w', encoding='utf-8').write('\n'.join(rep))

if __name__ == "__main__":
    main()
