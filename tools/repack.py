# -*- coding: utf-8 -*-
"""app.asar 재패킹: _work/rebuilt/ 의 번역된 .ks 로 교체한 새 app.asar 생성.
변경 파일만 새 바이트로, 나머지는 원본에서 스트리밍 복사. 헤더 오프셋 재계산.
출력: 번역본/resources/app.asar (원본은 건드리지 않음)."""
import os, struct, json, sys

# 작업 폴더(_work/ 가 있는 곳). 기본값은 저장소 폴더.
ROOT = os.environ.get("WTA_WORKSPACE") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ORIG = os.path.join(os.environ.get("WTA_GAME_DIR") or r"C:\Program Files (x86)\Steam\steamapps\common\WinterTreeAfter", "resources", "app.asar")
REBUILT = os.path.join(ROOT, "_work", "rebuilt")   # data/scenario/*.ks
OUT = os.path.join(ROOT, "번역본", "resources", "app.asar")

def read_header(f):
    f.seek(0)
    i0, i1, i2, i3 = struct.unpack('<IIII', f.read(16))
    jsonLen = i3
    meta = json.loads(f.read(jsonLen).decode('utf-8'))
    P = (4 - jsonLen % 4) % 4
    base = 16 + jsonLen + P
    return meta, base

def leaf_iter(node, prefix=''):
    """헤더 트리 순서 유지하며 리프 파일 노드 yield (path, node)."""
    if 'files' in node:
        for k, v in node['files'].items():
            p = prefix + '/' + k
            if 'files' in v:
                yield from leaf_iter(v, p)
            else:
                yield p, v

def add_node(meta, asar_path, node):
    """헤더 트리에 새 리프 노드 삽입 (중간 디렉터리 생성)."""
    parts = asar_path.strip('/').split('/')
    cur = meta
    for seg in parts[:-1]:
        cur = cur.setdefault('files', {}).setdefault(seg, {})
    cur.setdefault('files', {})[parts[-1]] = node

def main():
    # 교체 파일 집합 수집: _work/rebuilt/ 전체 순회
    repl = {}  # asar path -> local file path
    for dirpath, _dn, fns in os.walk(REBUILT):
        for fn in fns:
            lp = os.path.join(dirpath, fn)
            rel = os.path.relpath(lp, REBUILT).replace(os.sep, '/')
            repl['/' + rel] = lp
    print("replacement/new files:", len(repl))

    fin = open(ORIG, 'rb')
    meta, base = read_header(fin)

    existing = set(p for p, _n in leaf_iter(meta))
    # 신규 파일(원본에 없는 것) 노드 삽입
    for ap in repl:
        if ap not in existing:
            add_node(meta, ap, {"size": 0, "offset": "0"})
            print("  NEW file node:", ap)

    leaves = list(leaf_iter(meta))
    # 새 오프셋 순차 할당 + 노드 갱신
    cur = 0
    plan = []  # (node, src_kind, src_ref, size)
    for path, node in leaves:
        if path in repl:
            lp = repl[path]
            sz = os.path.getsize(lp)
            plan.append((node, 'file', lp, sz, None))
        else:
            sz = int(node['size'])
            oldoff = int(node['offset'])
            plan.append((node, 'orig', None, sz, oldoff))
        node['size'] = sz
        node['offset'] = str(cur)
        cur += sz

    # 헤더 직렬화
    j = json.dumps(meta, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
    jsonLen = len(j)
    P = (4 - jsonLen % 4) % 4
    i0 = 4
    i2 = 4 + jsonLen + P
    i1 = i2 + 4
    i3 = jsonLen

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'wb') as fo:
        fo.write(struct.pack('<IIII', i0, i1, i2, i3))
        fo.write(j)
        fo.write(b'\0' * P)
        # 파일 데이터 순차 기록
        for node, kind, ref, sz, oldoff in plan:
            if kind == 'file':
                with open(ref, 'rb') as rf:
                    while True:
                        b = rf.read(1 << 20)
                        if not b: break
                        fo.write(b)
            else:
                fin.seek(base + oldoff)
                left = sz
                while left > 0:
                    b = fin.read(min(1 << 20, left))
                    if not b: break
                    fo.write(b); left -= len(b)
    fin.close()
    print("wrote", OUT, os.path.getsize(OUT), "bytes (orig", os.path.getsize(ORIG), ")")

if __name__ == "__main__":
    main()
