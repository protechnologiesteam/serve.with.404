#!/usr/bin/env python3
import http.server
import os
import sys
import socketserver
import time

ROOT = os.path.dirname(os.path.abspath(__file__))
RULES_FILE = os.path.join(ROOT, "no404.txt")
NOT_FOUND_FILE = os.path.join(ROOT, "404.html")

_rules_cache = {"mtime": None, "exact": set(), "prefixes": []}


def _load_rules():
    try:
        mtime = os.path.getmtime(RULES_FILE)
    except OSError:
        _rules_cache["mtime"] = None
        _rules_cache["exact"] = set()
        _rules_cache["prefixes"] = []
        return _rules_cache

    if _rules_cache["mtime"] == mtime:
        return _rules_cache

    exact = set()
    prefixes = []
    try:
        with open(RULES_FILE, "r", encoding="utf-8") as f:
            for raw in f:
                line = raw.strip()
                if not line or line.startswith("#"):
                    continue
                if not line.startswith("/"):
                    line = "/" + line
                if line.endswith("/*"):
                    prefix = line[:-2] or "/"
                    prefixes.append(prefix.rstrip("/") or "/")
                else:
                    exact.add(line.rstrip("/") or "/")
    except OSError:
        pass

    _rules_cache["mtime"] = mtime
    _rules_cache["exact"] = exact
    _rules_cache["prefixes"] = prefixes
    return _rules_cache


def _is_whitelisted(path):
    clean = path.split("?", 1)[0].split("#", 1)[0]
    normalized = clean.rstrip("/") or "/"
    rules = _load_rules()

    if normalized in rules["exact"]:
        return True

    for prefix in rules["prefixes"]:
        if normalized == prefix or normalized.startswith(prefix + "/"):
            return True

    return False


_PLACEHOLDER_TEMPLATE = """<!DOCTYPE html>
<html lang="tr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>404</title>
<style>
  body{{margin:0;min-height:100vh;display:flex;align-items:center;justify-content:center;
  background:#03060f;color:#eaf1ff;font-family:-apple-system,'Segoe UI',sans-serif;text-align:center;}}
  .box{{padding:32px;}}
  code{{background:rgba(61,139,255,.12);border:1px solid rgba(120,175,255,.3);
  padding:4px 10px;border-radius:8px;color:#9fc4ff;font-family:monospace;}}
  p{{color:#7f93bd;font-size:14px;margin-top:14px;}}
</style>
</head>
<body>
  <div class="box">
    <div><code>{path}</code></div>
    <p>There is a problem</p>
  </div>
</body>
</html>
"""


class NoFalse404Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=ROOT, **kwargs)

    def log_message(self, fmt, *args):
        sys.stderr.write("%s - - [%s] %s\n" % (
            self.address_string(), self.log_date_time_string(), fmt % args
        ))

    def send_error(self, code, message=None, explain=None):
        if code == 404:
            if _is_whitelisted(self.path):
                body = _PLACEHOLDER_TEMPLATE.format(path=self.path).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                if self.command != "HEAD":
                    self.wfile.write(body)
                return

            if os.path.isfile(NOT_FOUND_FILE):
                try:
                    with open(NOT_FOUND_FILE, "rb") as f:
                        body = f.read()
                    self.send_response(404)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.send_header("Content-Length", str(len(body)))
                    self.end_headers()
                    if self.command != "HEAD":
                        self.wfile.write(body)
                    return
                except OSError:
                    pass

        super().send_error(code, message, explain)


class ThreadingHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True


def main():
    port = 8000
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            print(f"Geçersiz port: {sys.argv[1]}")
            sys.exit(1)

    _load_rules()
    server = ThreadingHTTPServer(("", port), NoFalse404Handler)
    print(f"ProTech dev sunucusu: http://localhost:{port}/  (kök: {ROOT})")
    print(f"no404.txt izin listesi: {RULES_FILE}")
    print("Durdurmak için Ctrl+C")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nDurduruldu.")
        server.shutdown()


if __name__ == "__main__":
    main()
