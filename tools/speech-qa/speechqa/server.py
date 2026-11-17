"""Loopback-only upload UI. Audio is processed locally and temporary files deleted."""

import argparse
from email.parser import BytesParser
from email.policy import default
from http.server import BaseHTTPRequestHandler, HTTPServer
import html
from pathlib import Path
import secrets
import subprocess
import sys
import tempfile

TOKEN = secrets.token_urlsafe(32)
PAGE = """<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Signal / Import audio</title><style>body{background:#f3f2eb;color:#18352e;font:18px/1.5 system-ui;margin:7vh auto;padding:24px;max-width:760px}h1{font-size:64px;letter-spacing:-.06em;line-height:1}form{background:white;padding:28px;border:1px solid #ccd5ce;border-radius:18px}label{display:block;margin:20px 0}input,textarea,select,button{font:inherit;max-width:100%}textarea{width:100%;height:120px}button{background:#18352e;color:white;padding:15px;border:0;border-radius:8px}small{display:block}#status{padding:15px}</style><p>SIGNAL / LOCAL SPEECH QA</p><h1>Start with<br>the recording.</h1><p>Import audio. Generate a transcript and word timestamps. Find possible omissions, timing anomalies and uncertain words, then listen to the evidence.</p><form method="post" enctype="multipart/form-data"><input type="hidden" name="token" value="TOKEN"><label>Audio (up to 100 MB / 30 minutes)<br><input required type="file" name="audio" accept="audio/*"></label><label>English ASR model <select name="model"><option>tiny.en</option><option selected>base.en</option><option>small.en</option></select></label><label>Optional expected transcript<textarea name="reference" placeholder="Compare an expected script against recognized speech. This is not a verified ground truth."></textarea></label><button>Transcribe & analyze locally</button><p id="status" role="status"></p></form><p>Initial setup downloads an open-source model. After caching, inference runs on this computer. Audio is never uploaded to a third-party API. Your browser sends it only to this local server. Close the server with Ctrl+C.</p><p>No silent auto-corrections. This tool produces review candidates, not certified accuracy. The exported HTML embeds your audio: share carefully.</p><script>document.querySelector('form').onsubmit=()=>{document.querySelector('button').disabled=true;document.getElementById('status').textContent='Processing… First run may download a model. Keep this tab open; CPU transcription can take several minutes.';};</script></html>"""


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass  # Do not log input names, transcripts or tokens.

    def reply(self, status, body):
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body.encode())))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Content-Security-Policy", "frame-ancestors 'none'")
        self.end_headers()
        self.wfile.write(body.encode())

    def do_GET(self):
        if self.headers.get("Host", "") != f"127.0.0.1:{self.server.server_port}":
            return self.reply(403, "Invalid host")
        origin = self.headers.get("Origin")
        if origin and origin != f"http://127.0.0.1:{self.server.server_port}":
            return self.reply(403, "Invalid origin")
        if self.path != "/":
            return self.reply(404, "Not found")
        self.reply(200, PAGE.replace("TOKEN", TOKEN))

    def do_POST(self):
        if self.path != "/":
            return self.reply(404, "Not found")
        host = self.headers.get("Host", "")
        if host != f"127.0.0.1:{self.server.server_port}":
            return self.reply(403, "Invalid host")
        origin = self.headers.get("Origin")
        if origin and origin != "http://" + host:
            return self.reply(403, "Cross-origin requests are not allowed")
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if size <= 0 or size > 101 * 1024 * 1024:
                return self.reply(413, "Input too large or empty")
            ctype = self.headers.get("Content-Type", "")
            if not ctype.startswith("multipart/form-data;"):
                return self.reply(400, "Expected multipart file upload")
            msg = BytesParser(policy=default).parsebytes(
                ("Content-Type: " + ctype + "\r\nMIME-Version: 1.0\r\n\r\n").encode()
                + self.rfile.read(size)
            )
            fields = {
                p.get_param("name", header="content-disposition"): p.get_payload(
                    decode=True
                )
                for p in msg.iter_parts()
            }
            if not secrets.compare_digest(fields.get("token", b"").decode(), TOKEN):
                return self.reply(403, "Refresh the form before uploading")
            model = fields.get("model", b"base.en").decode()
            if model not in ("tiny.en", "base.en", "small.en"):
                return self.reply(400, "Unsupported model")
            audio = fields.get("audio", b"")
            if not audio or len(audio) > 100 * 1024 * 1024:
                return self.reply(400, "Audio missing or over 100 MB")
            reference = fields.get("reference", b"")
            if len(reference) > 1024 * 1024:
                return self.reply(400, "Reference must be under 1 MB")
            with tempfile.TemporaryDirectory(prefix="speechqa-") as directory:
                root = Path(directory)
                path = root / "input.audio"
                path.write_bytes(audio)
                command = [
                    sys.executable,
                    "-m",
                    "speechqa",
                    str(path),
                    "--model",
                    model,
                    "--out",
                    str(root / "result"),
                ]
                if reference.strip():
                    (root / "reference.txt").write_bytes(reference)
                    command += ["--reference", str(root / "reference.txt")]
                result = subprocess.run(
                    command, capture_output=True, text=True, timeout=1800
                )
                if result.returncode:
                    # Full errors are intentionally not exposed with local file paths or transcript text.
                    return self.reply(
                        422,
                        '<h1>Processing failed</h1><p>No demo transcript was substituted. Check that this is a valid audio file, dependencies are installed, the model can download, and sufficient memory is available. Try a short WAV clip.</p><a href="/">Return to import</a>',
                    )
                self.reply(200, (root / "result/index.html").read_text())
        except subprocess.TimeoutExpired:
            self.reply(
                408,
                "Processing exceeded 30 minutes. Try a shorter clip or smaller model.",
            )
        except (ValueError, UnicodeError, KeyError):
            self.reply(400, "Invalid form data; return to the import page.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    server = HTTPServer(("127.0.0.1", args.port), Handler)
    print("Open http://127.0.0.1:" + str(args.port) + " (local only)", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
