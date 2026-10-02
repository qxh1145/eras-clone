#!/usr/bin/env python3
"""Chạy bản mirror erasvietnam.vn trên máy: python3 serve.py [port]  → http://localhost:8000

- Phục vụ file tĩnh từ thư mục này (không sửa file gốc).
- URL tuyệt đối https://erasvietnam.vn/... trong HTML/CSS/JS được đổi thành đường dẫn local khi trả về.
- File không có trong mirror (404 khi tải, wp-json, ...) → chuyển hướng sang bản live.
"""
import json, os, re, sys
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

ROOT = os.path.dirname(os.path.abspath(__file__))
LIVE = "https://erasvietnam.vn"
ALIASES = {"/en/": "/en/home/", "/en": "/en/home/"}  # bản live redirect /en/ → /en/home/
ABS = re.compile(rb"https?:(\\?/){2}(www\.)?erasvietnam\.vn(?=\\?/)")
ABS_ROOT = re.compile(rb"https?:(\\?/){2}(www\.)?erasvietnam\.vn(?=[\"'\s?#)<])")
TEXT = (".html", ".css", ".js", ".json", ".xml", ".svg")
CATS = ("website", "branding", "mobile-app")
CARD = re.compile(r'<div class="col" data-terms=.*?</a>\s*</div>\s*</div>', re.S)


def portfolio_items(term, prefix="/"):
    """Thay cho AJAX load_portfolio_items của WordPress: lấy thẻ dự án từ trang danh mục đã mirror."""
    cards = []
    for cat in [term] if term in CATS else CATS:
        with open(os.path.join(ROOT, "featured_item_category", cat, "index.html"), encoding="utf-8") as f:
            cards += [c for c in CARD.findall(f.read().replace("../../", prefix)) if c not in cards]
    return "".join(cards)


class Handler(SimpleHTTPRequestHandler):
    def do_GET(self):
        path = urlsplit(self.path).path
        if path in ALIASES:
            return self._redirect(ALIASES[path])
        fs = self.translate_path(self.path)
        if os.path.isdir(fs) and path.endswith("/"):
            fs = os.path.join(fs, "index.html")
        if not os.path.exists(fs):
            self.log_message("[live] %s", self.path)
            return self._redirect(LIVE + self.path)
        if os.path.isdir(fs) or not fs.endswith(TEXT):  # thư mục thiếu "/" → stdlib redirect
            return super().do_GET()
        with open(fs, "rb") as f:
            body = ABS_ROOT.sub(b"/", ABS.sub(b"", f.read()))  # https://erasvietnam.vn/x → /x
        self.send_response(200)
        self.send_header("Content-Type", self.guess_type(fs))
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        size = int(self.headers.get("Content-Length") or 0)
        form = parse_qs(self.rfile.read(size).decode())
        if urlsplit(self.path).path != "/wp-admin/admin-ajax.php" or form.get("action") != ["load_portfolio_items"]:
            return self.send_error(501, "Bản tĩnh không hỗ trợ gửi biểu mẫu")
        # ponytail: trả toàn bộ dự án một lần, không phân trang (~60 mục)
        body = json.dumps({"items": portfolio_items(form.get("term", [""])[0]), "pagination": ""}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _redirect(self, url):
        self.send_response(302)
        self.send_header("Location", url)
        self.end_headers()


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    print(f"Eras Việt Nam mirror: http://localhost:{port}")
    ThreadingHTTPServer(("127.0.0.1", port), partial(Handler, directory=ROOT)).serve_forever()
