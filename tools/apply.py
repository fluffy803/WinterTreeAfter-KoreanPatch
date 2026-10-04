# -*- coding: utf-8 -*-
"""번역 재삽입: translations.jsonl 을 원본 .ks 에 되돌려 넣고 #화자 태그를 치환.
결과: _work/rebuilt/data/scenario/*.ks (build_release.py 가 패치로 묶음)."""
import os, re, json, sys

# 작업 폴더(_work/ 가 있는 곳). 기본값은 저장소 폴더.
ROOT = os.environ.get("WTA_WORKSPACE") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCEN = os.path.join(ROOT, "_work", "extracted", "data", "scenario")
TR   = os.path.join(ROOT, "_work", "translations.jsonl")
OUTD = os.path.join(ROOT, "_work", "rebuilt", "data", "scenario")

# #화자 태그 치환 (태그명 부분만)
SPEAKER = {
    "言叶": "코토바", "小忆": "코이", "小亦": "코이",
    "言叶&小忆": "코토바&코이", "言叶/小忆": "코토바/코이",
    "老奶奶": "할머니", "猫咪": "고양이", "司机": "기사",
    "店员A": "점원A", "店员B": "점원B", "店员": "점원",
    "路人": "행인", "同事": "동료",
    # sensei, ？？, 빈 화자(#)는 그대로
}

def load_tr():
    m = {}
    if not os.path.exists(TR): return m
    for ln in open(TR, encoding='utf-8'):
        ln = ln.strip()
        if ln:
            d = json.loads(ln); m[d['id']] = d
    return m

def main():
    tr = load_tr()
    # 파일별 라인교체(text) / 속성교체(attr_text) 인덱스 구성
    by_file_line = {}   # (file, line) -> tgt   (text)
    attr_by_file = {}   # file -> list of (line, src, tgt)
    for d in tr.values():
        if d['kind'] == 'text':
            by_file_line[(d['file'], int(d['id'].split(':')[1]))] = d['tgt']
        elif d['kind'] == 'attr_text':
            attr_by_file.setdefault(d['file'], []).append((int(d['id'].split(':')[1]), d['src'], d['tgt']))

    files = sorted(set([f for (f, _l) in by_file_line] + list(attr_by_file.keys())))
    os.makedirs(OUTD, exist_ok=True)
    miss_total = 0
    for fn in files:
        src_path = os.path.join(SCEN, fn)
        lines = open(src_path, encoding='utf-8').read().split('\n')
        attrs = {l: [] for (l, s, t) in attr_by_file.get(fn, [])}
        for (l, s, t) in attr_by_file.get(fn, []):
            attrs.setdefault(l, []).append((s, t))
        for i, line in enumerate(lines):
            st = line.strip()
            # 1) 본문 교체
            if (fn, i) in by_file_line:
                lines[i] = by_file_line[(fn, i)]
                continue
            # 2) 속성(text=) 교체
            if i in attrs:
                for s, t in attrs[i]:
                    lines[i] = lines[i].replace(f'text="{s}"', f'text="{t}"')
                continue
            # 3) #화자 치환
            if st.startswith('#') and len(st) > 1:
                name = st[1:]
                if name in SPEAKER:
                    lines[i] = line.replace('#' + name, '#' + SPEAKER[name], 1)
        outp = os.path.join(OUTD, fn)
        with open(outp, 'w', encoding='utf-8', newline='') as o:
            o.write('\n'.join(lines))
        print(f"{fn:18} written")
    # 미번역 점검
    import glob
    from collections import Counter
    # (검증은 verify.py 로 분리)
    print("rebuilt ->", OUTD)

if __name__ == "__main__":
    main()
