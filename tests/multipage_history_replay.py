"""Cold-restart and page through one synthetic multi-turn desktop history."""
from __future__ import annotations

import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import queue
import sqlite3
import subprocess
import sys
import threading
import time

backend = Path(sys.argv[1]).resolve(strict=True)
label = sys.argv[2]
if label not in {"official", "compat"}:
    raise ValueError("label must be official or compat")
root = Path(__file__).resolve().parents[1] / "replay-results" / f"multipage-4894-{label}"
if root.exists():
    raise RuntimeError("previous multi-page replay exists; inspect before retry")
home, workspace, profile = root / "home", root / "workspace", root / "profile"
for folder in (home, workspace, profile):
    folder.mkdir(parents=True)


class Handler(BaseHTTPRequestHandler):
    request_count = 0

    def log_message(self, *_args):
        pass

    def do_POST(self):
        json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))))
        Handler.request_count += 1
        index = Handler.request_count
        events = [
            {"type": "response.created", "response": {"id": f"synthetic-response-{index}"}},
            {"type": "response.output_item.done", "item": {"type": "message", "role": "assistant",
             "id": f"synthetic-message-{index}", "content": [{"type": "output_text",
             "text": f"Synthetic completion {index}."}]}},
            {"type": "response.completed", "response": {"id": f"synthetic-response-{index}",
             "usage": {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}}},
        ]
        raw = "".join("event: " + event["type"] + "\ndata: " + json.dumps(event) + "\n\n"
                      for event in events).encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)


server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
threading.Thread(target=server.serve_forever, daemon=True).start()
(home / "config.toml").write_text(
    f'''model_provider = "fixture"
model = "fixture-model"
[model_providers.fixture]
name = "Synthetic loopback"
base_url = "http://127.0.0.1:{server.server_port}/v1"
wire_api = "responses"
requires_openai_auth = false
''', encoding="utf-8")
env = {key: os.environ[key] for key in
       ("SystemRoot", "WINDIR", "PATH", "TEMP", "TMP", "COMSPEC") if key in os.environ}
env.update(CODEX_HOME=str(home), CODEX_SQLITE_HOME=str(home), USERPROFILE=str(profile))


class Client:
    def __init__(self, phase: str):
        self.stderr = (root / f"stderr-{phase}.log").open("w", encoding="utf-8")
        self.process = subprocess.Popen([str(backend), "app-server"], cwd=workspace, env=env,
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=self.stderr,
            text=True, encoding="utf-8", creationflags=0x08000000)
        self.queue = queue.Queue()
        self.deferred = []
        self.next_id = 0
        threading.Thread(target=self._read, daemon=True).start()
        self.call("initialize", {"clientInfo": {"name": "synthetic-multipage-test", "version": "1"},
                                 "capabilities": {"experimentalApi": True}})
        self.process.stdin.write('{"method":"initialized","params":{}}\n')
        self.process.stdin.flush()

    def _read(self):
        for line in self.process.stdout:
            if line.strip():
                self.queue.put(json.loads(line))

    def call(self, method, params):
        self.next_id += 1
        request_id = self.next_id
        self.process.stdin.write(json.dumps({"id": request_id, "method": method, "params": params}) + "\n")
        self.process.stdin.flush()
        deadline = time.monotonic() + 60
        while time.monotonic() < deadline:
            message = self.queue.get(timeout=max(.1, deadline - time.monotonic()))
            if message.get("id") == request_id:
                if "error" in message:
                    raise RuntimeError(f"{method}: {message['error']}")
                return message["result"]
            if message.get("method") == "turn/completed":
                self.deferred.append(message)
        raise TimeoutError(method)

    def wait_turn(self, thread_id):
        deadline = time.monotonic() + 60
        while time.monotonic() < deadline:
            for index, message in enumerate(self.deferred):
                if message.get("params", {}).get("threadId") == thread_id:
                    event = self.deferred.pop(index)
                    if event["params"]["turn"]["status"] != "completed":
                        raise RuntimeError("synthetic turn failed")
                    return
            message = self.queue.get(timeout=max(.1, deadline - time.monotonic()))
            if message.get("method") == "turn/completed":
                self.deferred.append(message)
        raise TimeoutError("turn/completed")

    def close(self):
        self.process.stdin.close()
        self.process.wait(timeout=30)
        self.stderr.close()


try:
    first = Client("write")
    try:
        started = first.call("thread/start", {"cwd": str(workspace), "approvalPolicy": "never",
            "sandbox": "read-only", "model": "fixture-model", "modelProvider": "fixture",
            "persistExtendedHistory": True})
        thread_id = started["thread"]["id"]
        for index in range(105):
            first.call("turn/start", {"threadId": thread_id, "input": [{"type": "text",
                "text": f"Synthetic turn {index}.", "textElements": []}]})
            first.wait_turn(thread_id)
    finally:
        first.close()
    before = {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in home.rglob("*.jsonl")}
    if len(before) != 1:
        raise RuntimeError("synthetic rollout count differs")
    second = Client("read")
    pages, ids, cursor = [], [], None
    try:
        for _ in range(6):
            page = second.call("thread/turns/list", {"threadId": thread_id, "cursor": cursor,
                "limit": 25, "itemsView": "full", "sortDirection": "desc"})
            data = page.get("data") or []
            pages.append(len(data))
            ids.extend(row["id"] for row in data)
            next_cursor = page.get("nextCursor")
            if next_cursor is None:
                break
            if not isinstance(next_cursor, str) or next_cursor == cursor:
                raise RuntimeError("invalid pagination cursor")
            cursor = next_cursor
        else:
            raise RuntimeError("pagination did not terminate")
    finally:
        second.close()
    after = {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in home.rglob("*.jsonl")}
    with sqlite3.connect(f"file:{(home / 'state_5.sqlite').as_posix()}?mode=ro", uri=True) as db:
        db_count = db.execute("SELECT COUNT(*) FROM threads").fetchone()[0]
    passed = (pages == [25, 25, 25, 25, 5] and len(ids) == len(set(ids)) == 105
              and before == after and Handler.request_count == 105 and db_count == 1)
    result = {"status": "passed" if passed else "failed", "backend_sha256":
        hashlib.sha256(backend.read_bytes()).hexdigest(), "synthetic_turns": 105,
        "page_lengths": pages, "unique_turns": len(set(ids)), "cold_restart": True,
        "history_bytes_unchanged_by_read": before == after, "source_database_touched": False,
        "real_credentials_used": False}
    (root / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))
    if not passed:
        raise RuntimeError("multi-page history replay failed")
finally:
    server.shutdown()
    server.server_close()
