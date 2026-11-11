#!/usr/bin/env python3
"""
Minimal A2A (Agent2Agent) agent for testing Kong's AI A2A Proxy.

- GET  /.well-known/agent-card.json   Agent Card (also /.well-known/agent.json)
- POST /                              JSON-RPC 2.0: message/send, message/stream,
                                      tasks/get, tasks/cancel
- POST /v1/message:send               REST binding (subset)
- GET  /v1/tasks/{id}                 REST binding (subset)

No dependencies (Python 3.9+ standard library only).

Answers come from a simple built-in "pet care advisor". If LLM_URL is set, the agent
instead asks an OpenAI-compatible chat endpoint, e.g. your Kong AI Proxy route:

    LLM_URL=https://<proxy-url>/chat/completions  LLM_APIKEY=<kong consumer key, optional>

Environment:
    PORT              listen port (default 10000)
    AGENT_PUBLIC_URL  URL advertised in the Agent Card (default http://localhost:PORT/)
    LLM_URL           optional OpenAI-compatible /chat/completions URL
    LLM_APIKEY        optional, sent as "apikey" header to LLM_URL
    LLM_MODEL         optional "model" field (default gpt-5.4-mini)
"""
import json
import os
import threading
import time
import urllib.request
import uuid
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT = int(os.environ.get("PORT", "10000"))
PUBLIC_URL = os.environ.get("AGENT_PUBLIC_URL", f"http://localhost:{PORT}/")
LLM_URL = os.environ.get("LLM_URL", "")
LLM_APIKEY = os.environ.get("LLM_APIKEY", "")
LLM_MODEL = os.environ.get("LLM_MODEL", "gpt-5.4-mini")

TASKS = {}
LOCK = threading.Lock()

AGENT_CARD = {
    "protocolVersion": "0.3.0",
    "name": "Pet Care Advisor",
    "description": "Answers questions about caring for pets: feeding, exercise, grooming, health basics.",
    "url": PUBLIC_URL,
    "preferredTransport": "JSONRPC",
    "additionalInterfaces": [
        {"url": PUBLIC_URL, "transport": "JSONRPC"},
        {"url": PUBLIC_URL.rstrip("/") + "/v1", "transport": "HTTP+JSON"},
    ],
    "version": "1.0.0",
    "capabilities": {"streaming": True, "pushNotifications": False},
    "defaultInputModes": ["text/plain"],
    "defaultOutputModes": ["text/plain"],
    "skills": [
        {
            "id": "pet-care-advice",
            "name": "Pet care advice",
            "description": "Practical advice on feeding, exercise and grooming for common pets.",
            "tags": ["pets", "advice"],
            "examples": ["How often should I walk a puppy?", "What should a cat eat?"],
        }
    ],
}

TIPS = {
    "dog": "Dogs need daily walks (puppies: short, frequent ones), a consistent feeding schedule and regular vet check-ups.",
    "puppy": "Puppies do best with several short walks a day, 3-4 small meals and lots of gentle socialisation.",
    "cat": "Cats need a protein-rich diet, fresh water, a clean litter box and daily play to stay active.",
    "fish": "Fish need a cycled tank, stable temperature, small daily feedings and partial water changes every week or two.",
    "bird": "Birds need a spacious cage, varied diet (pellets, fresh vegetables), daily out-of-cage time and social interaction.",
}


def now():
    return datetime.now(timezone.utc).isoformat()


def text_of(message):
    return " ".join(p.get("text", "") for p in message.get("parts", []) if p.get("kind") == "text").strip()


def answer(question):
    if LLM_URL:
        try:
            body = json.dumps({
                "model": LLM_MODEL,
                "messages": [
                    {"role": "system", "content": "You are a concise, friendly pet care advisor. Answer in 3 sentences or fewer."},
                    {"role": "user", "content": question},
                ],
            }).encode()
            req = urllib.request.Request(LLM_URL, data=body, method="POST",
                                         headers={"Content-Type": "application/json"})
            if LLM_APIKEY:
                req.add_header("apikey", LLM_APIKEY)
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.load(r)["choices"][0]["message"]["content"]
        except Exception as e:  # fall back to built-in tips
            return f"(LLM unavailable: {e}) " + answer_builtin(question)
    return answer_builtin(question)


def answer_builtin(question):
    q = question.lower()
    for k, tip in TIPS.items():
        if k in q:
            return tip
    return "Every pet needs the right food, clean water, exercise, and regular vet visits. Tell me which pet you have for specific advice."


def new_task(message):
    task_id = str(uuid.uuid4())
    context_id = message.get("contextId") or str(uuid.uuid4())
    user_msg = dict(message, taskId=task_id, contextId=context_id)
    task = {
        "kind": "task",
        "id": task_id,
        "contextId": context_id,
        "status": {"state": "submitted", "timestamp": now()},
        "history": [user_msg],
        "artifacts": [],
    }
    with LOCK:
        TASKS[task_id] = task
    return task


def complete_task(task, reply):
    agent_msg = {"kind": "message", "messageId": str(uuid.uuid4()), "role": "agent",
                 "parts": [{"kind": "text", "text": reply}], "taskId": task["id"], "contextId": task["contextId"]}
    with LOCK:
        task["artifacts"] = [{"artifactId": str(uuid.uuid4()), "name": "answer",
                              "parts": [{"kind": "text", "text": reply}]}]
        task["history"].append(agent_msg)
        task["status"] = {"state": "completed", "timestamp": now(), "message": agent_msg}
    return task


def rpc_result(rid, result):
    return {"jsonrpc": "2.0", "id": rid, "result": result}


def rpc_error(rid, code, message):
    return {"jsonrpc": "2.0", "id": rid, "error": {"code": code, "message": message}}


class Handler(BaseHTTPRequestHandler):
    server_version = "PetCareA2A/1.0"

    def log_message(self, fmt, *args):
        print(f"{self.address_string()} {fmt % args}", flush=True)

    def _json(self, status, obj):
        data = json.dumps(obj).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _body(self):
        n = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(n) if n else b""
        return json.loads(raw or b"{}")

    # ---------- GET ----------
    def do_GET(self):
        path = self.path.split("?")[0]
        if path.endswith("/.well-known/agent-card.json") or path.endswith("/.well-known/agent.json"):
            return self._json(200, AGENT_CARD)
        if path.startswith("/v1/tasks/"):
            tid = path.rsplit("/", 1)[-1]
            with LOCK:
                t = TASKS.get(tid)
            return self._json(200, t) if t else self._json(404, {"error": "task not found"})
        if path in ("/health", "/healthz"):
            return self._json(200, {"status": "ok"})
        return self._json(404, {"error": "not found"})

    # ---------- POST ----------
    def do_POST(self):
        path = self.path.split("?")[0]
        try:
            body = self._body()
        except json.JSONDecodeError:
            return self._json(400, rpc_error(None, -32700, "Parse error"))

        # REST binding (subset)
        if path.endswith("/v1/message:send"):
            msg = body.get("message") or {}
            task = new_task(msg)
            return self._json(200, complete_task(task, answer(text_of(msg))))

        # JSON-RPC binding
        if body.get("jsonrpc") != "2.0" or "method" not in body:
            return self._json(400, rpc_error(body.get("id"), -32600, "Invalid Request: JSON-RPC 2.0 envelope required"))
        rid, method, params = body.get("id"), body["method"], body.get("params") or {}

        if method == "message/send":
            msg = params.get("message")
            if not msg or not msg.get("parts"):
                return self._json(200, rpc_error(rid, -32602, "Invalid params: params.message.parts required"))
            task = new_task(msg)
            return self._json(200, rpc_result(rid, complete_task(task, answer(text_of(msg)))))

        if method == "message/stream":
            msg = params.get("message")
            if not msg or not msg.get("parts"):
                return self._json(200, rpc_error(rid, -32602, "Invalid params: params.message.parts required"))
            return self._stream(rid, msg)

        if method == "tasks/get":
            with LOCK:
                t = TASKS.get(params.get("id"))
            return self._json(200, rpc_result(rid, t) if t else rpc_error(rid, -32001, "Task not found"))

        if method == "tasks/cancel":
            with LOCK:
                t = TASKS.get(params.get("id"))
            if not t:
                return self._json(200, rpc_error(rid, -32001, "Task not found"))
            return self._json(200, rpc_error(rid, -32002, "Task cannot be canceled (already completed)"))

        return self._json(200, rpc_error(rid, -32601, f"Method not found: {method}"))

    def _stream(self, rid, msg):
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()

        def send(obj):
            self.wfile.write(f"data: {json.dumps(rpc_result(rid, obj))}\n\n".encode())
            self.wfile.flush()

        task = new_task(msg)
        send(task)
        with LOCK:
            task["status"] = {"state": "working", "timestamp": now()}
        send({"kind": "status-update", "taskId": task["id"], "contextId": task["contextId"],
              "status": task["status"], "final": False})
        reply = answer(text_of(msg))
        art_id = str(uuid.uuid4())
        words = reply.split(" ")
        for i in range(0, len(words), 6):  # stream the answer in chunks
            chunk = " ".join(words[i:i + 6]) + (" " if i + 6 < len(words) else "")
            send({"kind": "artifact-update", "taskId": task["id"], "contextId": task["contextId"],
                  "artifact": {"artifactId": art_id, "name": "answer", "parts": [{"kind": "text", "text": chunk}]},
                  "append": i > 0, "lastChunk": i + 6 >= len(words)})
            time.sleep(0.05)
        complete_task(task, reply)
        send({"kind": "status-update", "taskId": task["id"], "contextId": task["contextId"],
              "status": task["status"], "final": True})


if __name__ == "__main__":
    print(f"Pet Care A2A agent on :{PORT}  card url={PUBLIC_URL}  llm={'on' if LLM_URL else 'off'}", flush=True)
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
