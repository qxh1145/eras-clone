#!/usr/bin/env python3
"""Xuất bản tĩnh để deploy (GitHub Pages): python3 build.py [base]  → dist/

Làm sẵn những gì serve.py làm lúc chạy:
- URL https://erasvietnam.vn/... có file trong mirror → đổi sang <base>/...; không có → giữ link live.
- Danh sách dự án (AJAX) → file JSON tĩnh trong <base>/portfolio/.
- Thêm noindex để bản sao không cạnh tranh SEO với site thật.
"""
import json, os, re, shutil, sys
from urllib.parse import unquote

from serve import CATS, ROOT, TEXT, portfolio_items

BASE = (sys.argv[1] if len(sys.argv) > 1 else "/eras-clone").rstrip("/") + "/"
OUT = os.path.join(ROOT, "dist")
SKIP = {"dist", ".git", ".github", ".claude", "__pycache__", "serve.py", "build.py", ".gitignore", ".DS_Store", "README.md"}
URL = re.compile(r"https?:(\\?/)\1(?:www\.)?erasvietnam\.vn((?:\\?/[^\"'\s?#)<>\\]*)*)")
AJAX = re.compile(r"type: 'POST',\s*url: '[^']*admin-ajax\.php',")


def local(m):
    path = unquote(m.group(2).replace("\\/", "/")) or "/"
    fs = os.path.join(ROOT, path.lstrip("/"))
    if os.path.isdir(fs):
        fs = os.path.join(fs, "index.html")
    if not os.path.isfile(fs):
        return m.group(0)  # không có trong mirror → giữ link live
    out = BASE + m.group(2).lstrip("\\/")
    return out.replace("/", "\\/") if m.group(1) == "\\/" else out


def convert(text, is_html):
    text = URL.sub(local, text)
    if is_html:
        text = re.sub(r"<head([^>]*)>", r'<head\1>\n<meta name="robots" content="noindex, nofollow">', text, count=1)
        text = AJAX.sub(f"type: 'GET', url: '{BASE}portfolio/' + (term || 'all') + '.json',", text)
    return text


def main():
    shutil.rmtree(OUT, ignore_errors=True)
    for d, dirs, files in os.walk(ROOT):
        rel = os.path.relpath(d, ROOT)
        dirs[:] = [x for x in dirs if x not in SKIP and not x.startswith(("Trang ch", "_mirror-report"))]
        os.makedirs(os.path.join(OUT, rel), exist_ok=True)
        for n in files:
            if n in SKIP or n.startswith("Trang ch"):
                continue
            src, dst = os.path.join(d, n), os.path.join(OUT, rel, n)
            if n.endswith(TEXT):
                with open(src, encoding="utf-8", errors="surrogateescape") as f:
                    text = convert(f.read(), n.endswith(".html"))
                with open(dst, "w", encoding="utf-8", errors="surrogateescape") as f:
                    f.write(text)
            else:
                shutil.copy2(src, dst)

    os.makedirs(os.path.join(OUT, "portfolio"))
    for term in ("all",) + CATS:
        items = portfolio_items("" if term == "all" else term, BASE)
        with open(os.path.join(OUT, "portfolio", term + ".json"), "w", encoding="utf-8") as f:
            json.dump({"items": items, "pagination": ""}, f, ensure_ascii=False)
    with open(os.path.join(OUT, "en", "index.html"), "w") as f:  # site thật redirect /en/ → /en/home/
        f.write(f'<!doctype html><meta http-equiv="refresh" content="0; url={BASE}en/home/">')
    with open(os.path.join(OUT, "robots.txt"), "w") as f:
        f.write("User-agent: *\nDisallow: /\n")
    open(os.path.join(OUT, ".nojekyll"), "w").close()


if __name__ == "__main__":
    main()
    # self-check
    home = open(os.path.join(OUT, "index.html"), encoding="utf-8").read()
    assert 'name="robots" content="noindex' in home
    assert f'href="{BASE}lien-he/' in home or "lien-he/index.html" in home
    assert "type: 'GET'" in open(os.path.join(OUT, "du-an", "index.html"), encoding="utf-8").read()
    assert json.load(open(os.path.join(OUT, "portfolio", "all.json")))["items"].count('class="col"') >= 60
    print("dist/ ok, base =", BASE)
