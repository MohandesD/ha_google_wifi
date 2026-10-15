"""Serve only public demo assets on loopback, with provider connections blocked."""

import argparse
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path, PurePosixPath
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]


class DemoHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def allowed_path(self):
        """Reject traversal, private files and symlinks outside the public tree."""
        path = PurePosixPath(unquote(urlsplit(self.path).path))
        allowed = path.as_posix() in {"/tools/demo.html", "/tools/demo.js"} or (
            path.as_posix().startswith(("/www/", "/custom_components/google_wifi_insights/frontend/", "/custom_components/google_wifi_insights/brand/"))
            and path.suffix in {".js", ".png", ".svg"}
        )
        resolved = (ROOT / path.as_posix().lstrip("/")).resolve()
        return ".." not in path.parts and allowed and resolved.is_relative_to(ROOT.resolve())

    def do_GET(self):
        if not self.allowed_path():
            self.send_error(404)
            return
        super().do_GET()

    def do_HEAD(self):
        if not self.allowed_path():
            self.send_error(404)
            return
        super().do_HEAD()

    def end_headers(self):
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'none'")
        self.send_header("Cache-Control", "no-store")
        super().end_headers()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8876)
    args = parser.parse_args()
    if not 1024 <= args.port <= 65535:
        parser.error("Choose a port from 1024 to 65535")
    with ThreadingHTTPServer(("127.0.0.1", args.port), DemoHandler) as server:
        print(f"Fictional demo: http://127.0.0.1:{args.port}/tools/demo.html", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
