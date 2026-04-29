import json
import os
import subprocess
import threading
from datetime import date, timedelta
from pathlib import Path

import yaml
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

load_dotenv()

ROOT = Path(__file__).parent.parent
RESULTS_DIR = ROOT / "results"
INTEREST_PROFILE_PATH = ROOT / "scanner" / "interest_profile.yaml"
AGENT_INSTRUCTIONS = ROOT / "agent" / "CLAUDE.md"
STATIC_DIR = Path(__file__).parent / "static"

BEARER_TOKEN = os.environ.get("RIZHI_BEARER_TOKEN", "")
CLAUDE_BIN = os.environ.get("CLAUDE_BIN", "claude")

app = FastAPI(title="rizhi", docs_url=None, redoc_url=None)


# --- auth ---

def require_auth(request: Request) -> None:
    if not BEARER_TOKEN:
        raise HTTPException(status_code=500, detail="RIZHI_BEARER_TOKEN not set")
    auth = request.headers.get("Authorization", "")
    if auth != f"Bearer {BEARER_TOKEN}":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)


# --- scan state (in-process, single-user) ---

class _ScanState:
    def __init__(self) -> None:
        self.running = False
        self.last_run: str | None = None
        self.last_result: str | None = None
        self._lock = threading.Lock()

    def start(self) -> bool:
        with self._lock:
            if self.running:
                return False
            self.running = True
            return True

    def finish(self, result: str) -> None:
        with self._lock:
            self.running = False
            self.last_run = date.today().isoformat()
            self.last_result = result


_scan = _ScanState()


# --- helpers ---

def _read_results(path: Path) -> list[dict]:
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []


def _latest_results() -> list[dict]:
    today = RESULTS_DIR / f"{date.today().isoformat()}.json"
    if today.exists():
        return _read_results(today)
    return _read_results(RESULTS_DIR / "latest.json")


def _history_results(days: int = 7) -> list[dict]:
    out = []
    for i in range(days):
        d = (date.today() - timedelta(days=i)).isoformat()
        papers = _read_results(RESULTS_DIR / f"{d}.json")
        if papers:
            out.append({"date": d, "papers": papers})
    return out


# --- results ---

@app.get("/api/results/latest", dependencies=[Depends(require_auth)])
def get_latest():
    return _latest_results()


@app.get("/api/results/history", dependencies=[Depends(require_auth)])
def get_history():
    return _history_results()


# --- config ---

@app.get("/api/config", dependencies=[Depends(require_auth)])
def get_config():
    with open(INTEREST_PROFILE_PATH) as f:
        return yaml.safe_load(f)


@app.post("/api/config", dependencies=[Depends(require_auth)])
async def update_config(request: Request):
    body = await request.json()
    with open(INTEREST_PROFILE_PATH, "w", encoding="utf-8") as f:
        yaml.dump(body, f, default_flow_style=False, allow_unicode=True)
    return {"ok": True}


@app.post("/api/config/keywords", dependencies=[Depends(require_auth)])
async def update_keywords(request: Request):
    body = await request.json()
    action = body.get("action")    # "add" | "remove"
    keyword = body.get("keyword", "").strip()
    if not keyword:
        raise HTTPException(status_code=400, detail="keyword required")

    with open(INTEREST_PROFILE_PATH, encoding="utf-8") as f:
        profile = yaml.safe_load(f)

    keywords: list = profile.setdefault("keywords", [])
    if action == "add" and keyword not in keywords:
        keywords.append(keyword)
    elif action == "remove" and keyword in keywords:
        keywords.remove(keyword)

    with open(INTEREST_PROFILE_PATH, "w", encoding="utf-8") as f:
        yaml.dump(profile, f, default_flow_style=False, allow_unicode=True)

    return {"ok": True, "keywords": keywords}


# --- scan ---

@app.post("/api/scan", dependencies=[Depends(require_auth)])
def trigger_scan():
    if not _scan.start():
        return {"ok": False, "status": "already_running"}

    def _run() -> None:
        try:
            result = subprocess.run(
                [CLAUDE_BIN, "--print"],
                input=AGENT_INSTRUCTIONS.read_text(encoding="utf-8"),
                cwd=ROOT,
                capture_output=True,
                text=True,
                timeout=600,
            )
            _scan.finish("done" if result.returncode == 0 else f"error: {result.stderr[:200]}")
        except Exception as e:
            _scan.finish(f"error: {e}")

    threading.Thread(target=_run, daemon=True).start()
    return {"ok": True, "status": "started"}


@app.get("/api/scan/status", dependencies=[Depends(require_auth)])
def get_scan_status():
    return {
        "running": _scan.running,
        "last_run": _scan.last_run,
        "last_result": _scan.last_result,
    }


# --- push subscriptions ---

@app.get("/api/push/vapid-public-key")
def get_vapid_public_key():
    from server.push import VAPID_PUBLIC_KEY
    return {"publicKey": VAPID_PUBLIC_KEY}


@app.post("/api/push/subscribe", dependencies=[Depends(require_auth)])
async def subscribe(request: Request):
    from server.push import add_subscription
    add_subscription(await request.json())
    return {"ok": True}


@app.post("/api/push/unsubscribe", dependencies=[Depends(require_auth)])
async def unsubscribe(request: Request):
    from server.push import remove_subscription
    body = await request.json()
    remove_subscription(body.get("endpoint", ""))
    return {"ok": True}


# --- internal trigger (localhost only) ---

@app.post("/internal/notify")
async def internal_notify(request: Request):
    client_host = request.client.host if request.client else ""
    if client_host not in ("127.0.0.1", "::1"):
        raise HTTPException(status_code=403)

    from server.push import send_push_to_all
    papers = _latest_results()
    if papers:
        count = len(papers)
        preview = ", ".join(p["title"][:35] for p in papers[:2])
        msg = f"{count} new paper{'s' if count != 1 else ''}: {preview}"
        if len(msg) > 190:
            msg = msg[:187] + "..."
        send_push_to_all(msg)
    return {"ok": True}


# --- PWA static files (must be last) ---

if STATIC_DIR.exists():
    app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
