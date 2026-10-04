# -*- coding: utf-8 -*-
"""겨울나무 AFTER (TyranoScript) 번역 단위 추출기.
scenario/*.ks 에서 번역 대상(지문/대사 줄, 선택지 text=, 메뉴/CG/스태프 라벨)을 뽑아
_work/units.jsonl 로 저장한다. 재삽입은 apply.py 가 같은 id 로 복원.
"""
import os, re, json, sys

# 작업 폴더(_work/ 가 있는 곳). 기본값은 저장소 폴더.
ROOT = os.environ.get("WTA_WORKSPACE") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCEN = os.path.join(ROOT, "_work", "extracted", "data", "scenario")
OUT  = os.path.join(ROOT, "_work", "units.jsonl")

# 본편 스토리 + UI 파일
STORY_FILES = ["_preview.ks", "scene1.ks", "scene2.ks", "scene3.ks", "scene4.ks", "end.ks"]
UI_FILES    = ["title_screen.ks", "cg.ks", "cgpage1.ks", "staff_screen.ks"]

CJK = re.compile(r'[一-鿿㐀-䶿]')
# text="..." 속성 (선택지/버튼/라벨)
ATTR_TEXT = re.compile(r'(text=")([^"]*)(")')

def has_cjk(s):
    return bool(CJK.search(s))

def extract_file(fn):
    path = os.path.join(SCEN, fn)
    units = []
    in_iscript = False
    with open(path, encoding='utf-8') as f:
        for i, raw in enumerate(f):
            line = raw.rstrip('\n')
            st = line.strip()
            low = st.lower()
            # iscript JS 블록 제외
            if low.startswith('[iscript'):
                in_iscript = True; continue
            if low.startswith('[endscript') or low.startswith('[endhtml'):
                in_iscript = False; continue
            if in_iscript:
                continue
            if not st:
                continue
            # 1) 태그 줄: text="중국어" 속성만 추출 (선택지/메뉴/라벨)
            if st[0] == '[':
                for m in ATTR_TEXT.finditer(line):
                    val = m.group(2)
                    if has_cjk(val):
                        units.append({
                            "id": f"{fn}:{i}:{m.start(2)}",
                            "file": fn, "line": i, "col": m.start(2),
                            "kind": "attr_text",
                            "src": val,
                        })
                continue
            # 주석/라벨/화자 제외 (화자 #은 glossary 치환으로 별도 처리)
            if st[0] in ';*@#':
                continue
            # 2) 본문 텍스트 줄 (지문/대사) — 중국어 포함시
            if has_cjk(st):
                units.append({
                    "id": f"{fn}:{i}",
                    "file": fn, "line": i,
                    "kind": "text",
                    "src": st,
                })
    return units

def main():
    allu = []
    for fn in STORY_FILES + UI_FILES:
        p = os.path.join(SCEN, fn)
        if not os.path.exists(p):
            print("MISSING", fn); continue
        u = extract_file(fn)
        allu.extend(u)
        print(f"{fn:18} {len(u):5d} units")
    with open(OUT, 'w', encoding='utf-8') as o:
        for u in allu:
            o.write(json.dumps(u, ensure_ascii=False) + "\n")
    print("TOTAL", len(allu), "->", OUT)

if __name__ == "__main__":
    main()
