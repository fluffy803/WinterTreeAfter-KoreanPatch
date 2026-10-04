# -*- coding: utf-8 -*-
"""Assemble the copy-paste patch: resources/app/{main.js,package.json,patch/...}

  python tools/build_release.py <version>            # -> dist/WinterTreeAfter_KoreanPatch_v<version>.zip
  python tools/build_release.py <version> --install  # ...and copy resources/app into the game

patch/ = every file that differs from the original app.asar (translated
scenario .ks, Korean font/css, translated UI and story images, videos).
"""
import os, sys, shutil, zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fix_tags import fix_ks

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# 번역된 rebuilt/ (data/..., tyrano/...). 작업 폴더는 WTA_WORKSPACE 로 지정.
PATCH_SRC = os.path.join(os.environ.get("WTA_WORKSPACE") or REPO, "_work", "rebuilt")
GAME = os.environ.get("WTA_GAME_DIR") or r"C:\Program Files (x86)\Steam\steamapps\common\WinterTreeAfter"


def files():
    """(zip path, source path) pairs."""
    for fn in ("main.js", "package.json"):
        yield f"resources/app/{fn}", os.path.join(REPO, "loader", fn)
    for root, _, fs in os.walk(PATCH_SRC):
        for fn in sorted(fs):
            p = os.path.join(root, fn)
            rel = os.path.relpath(p, PATCH_SRC).replace(os.sep, "/")
            yield f"resources/app/patch/{rel}", p
    for fn in sorted(os.listdir(os.path.join(REPO, "release"))):
        yield fn, os.path.join(REPO, "release", fn)


def payload(arc, src):
    """File bytes as shipped; scenario .ks go through fix_tags."""
    if arc.endswith(".ks"):
        text = open(src, encoding="utf-8").read()
        return fix_ks(os.path.basename(arc), text).encode("utf-8")
    return open(src, "rb").read()


def main():
    ver = sys.argv[1]
    out = os.path.join(REPO, "dist", f"WinterTreeAfter_KoreanPatch_v{ver}.zip")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    pairs = list(files())
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for arc, src in pairs:
            z.writestr(zipfile.ZipInfo.from_file(src, arc), payload(arc, src), zipfile.ZIP_DEFLATED)
    print(f"{out}: {len(pairs)} files, {os.path.getsize(out) / 1e6:.1f} MB")

    if "--install" in sys.argv:
        n = 0
        for arc, src in pairs:
            if not arc.startswith("resources/"):
                continue
            dst = os.path.join(GAME, *arc.split("/"))
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            with open(dst, "wb") as fo:
                fo.write(payload(arc, src))
            n += 1
        print(f"installed {n} files -> {GAME}")


if __name__ == "__main__":
    main()
