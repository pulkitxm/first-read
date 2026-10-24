#!/usr/bin/env python3
import base64
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from debate import build_debate, preset_cards
from fish import load_env, speak_chunks
from readthrough import ScriptError, prepare

ROOT = Path(__file__).resolve().parent
STATIC = ROOT / "static"
EXAMPLES = ROOT / "examples"
AUDIO = ROOT / "audio"
HOST = "127.0.0.1"
PORT = int(os.environ.get("PORT", "8791"))


def example_cards():
    timing = {}
    manifest = AUDIO / "manifest.json"
    if manifest.exists():
        timing = json.loads(manifest.read_text())
    cards = []
    for path in sorted(EXAMPLES.glob("*.txt")):
        meta = timing.get(path.stem, {})
        read = prepare(path.read_text())
        file_name = meta.get("file")
        cards.append(
            {
                "id": path.stem,
                "title": meta.get("title", path.stem),
                "kind": read["kind"],
                "script": path.read_text(),
                "lines": read["lines"],
                "cast": read["cast"],
                "seconds": meta.get("seconds"),
                "audio": f"/audio/{file_name}" if file_name and (AUDIO / file_name).is_file() else None,
            }
        )
    return cards


class App(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        print("%s %s" % (self.command, self.path))

    def _json(self, status, payload):
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _file(self, path: Path, content_type: str):
        if not path.is_file():
            self._json(404, {"error": "Missing."})
            return
        body = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/":
            self._file(STATIC / "index.html", "text/html; charset=utf-8")
            return
        if path == "/api/examples":
            self._json(200, {"examples": example_cards()})
            return
        if path == "/api/debates":
            cards = []
            for card in preset_cards():
                file_name = f"debate-{card['id']}-{card['speakers']}.mp3"
                cards.append(
                    {
                        **card,
                        "audio": f"/audio/{file_name}" if (AUDIO / file_name).is_file() else None,
                    }
                )
            self._json(200, {"debates": cards})
            return
        if path.startswith("/static/"):
            name = Path(path).name
            types = {".css": "text/css; charset=utf-8", ".js": "text/javascript; charset=utf-8", ".svg": "image/svg+xml"}
            target = STATIC / name
            self._file(target, types.get(target.suffix, "application/octet-stream"))
            return
        if path.startswith("/audio/") and Path(path).name.endswith(".mp3"):
            self._file(AUDIO / Path(path).name, "audio/mpeg")
            return
        self._json(404, {"error": "Missing."})

    def _debate(self):
        length = int(self.headers.get("Content-Length", "0") or "0")
        if length > 20_000:
            self._json(413, {"error": "That topic is too long."})
            return
        try:
            payload = json.loads(self.rfile.read(length).decode() or "{}")
            debate = build_debate(
                str(payload.get("topic", "")),
                int(payload.get("speakers", 2)),
                int(payload.get("extra_rounds", 0)),
            )
        except ScriptError as error:
            self._json(400, {"error": str(error)})
            return
        except (json.JSONDecodeError, UnicodeDecodeError, TypeError, ValueError):
            self._json(400, {"error": "Send a topic and two or three voices."})
            return
        self._debate_response(debate)

    def _debate_response(self, debate):
        file_name = f"debate-{debate['id']}-{debate['speakers']}.mp3" if debate["id"] else ""
        recorded = AUDIO / file_name if file_name else None
        body = {
            "kind": "debate",
            "topic": debate["topic"],
            "lines": debate["lines"],
            "cast": debate["cast"],
            "script": debate["script"],
        }
        if debate["preset"] and recorded and recorded.is_file():
            self._json(200, {**body, "audio": f"/audio/{file_name}"})
            return
        try:
            audio = speak_chunks(debate["chunks"])
        except RuntimeError as error:
            self._json(200, {**body, "audio": None, "note": str(error)})
            return
        self._json(200, {**body, "audio_base64": base64.b64encode(audio).decode(), "mime": "audio/mpeg"})

    def do_POST(self):
        path = urlparse(self.path).path
        if path == "/api/debate":
            self._debate()
            return
        if path != "/api/read":
            self._json(404, {"error": "Missing."})
            return
        length = int(self.headers.get("Content-Length", "0") or "0")
        if length > 80_000:
            self._json(413, {"error": "That script is too long."})
            return
        try:
            payload = json.loads(self.rfile.read(length).decode() or "{}")
            read = prepare(str(payload.get("script", "")))
            audio = speak_chunks(read["chunks"])
        except ScriptError as error:
            self._json(400, {"error": str(error)})
            return
        except RuntimeError as error:
            self._json(503, {"error": str(error)})
            return
        except (json.JSONDecodeError, UnicodeDecodeError):
            self._json(400, {"error": "Send the script as JSON."})
            return
        self._json(
            200,
            {
                "kind": read["kind"],
                "lines": read["lines"],
                "cast": read["cast"],
                "audio_base64": base64.b64encode(audio).decode(),
                "mime": "audio/mpeg",
            },
        )


def main():
    load_env(ROOT)
    AUDIO.mkdir(exist_ok=True)
    server = ThreadingHTTPServer((HOST, PORT), App)
    print(f"http://{HOST}:{PORT}")
    server.serve_forever()


if __name__ == "__main__":
    main()
