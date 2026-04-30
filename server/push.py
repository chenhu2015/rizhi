"""
Web Push notification support.

Run as a script to generate VAPID keys:
    python -m server.push --generate-keys
"""

import os
import sqlite3
import sys
from pathlib import Path

from pywebpush import WebPushException, webpush

ROOT = Path(__file__).parent.parent
DB_PATH = ROOT / "storage" / "seen_papers.db"

VAPID_PRIVATE_KEY = os.environ.get("VAPID_PRIVATE_KEY", "")
VAPID_PUBLIC_KEY = os.environ.get("VAPID_PUBLIC_KEY", "")
VAPID_EMAIL = os.environ.get("VAPID_CLAIMS_EMAIL", "")


# --- subscription storage ---

def _conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS push_subscriptions (
            endpoint TEXT PRIMARY KEY,
            p256dh   TEXT NOT NULL,
            auth     TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)
    return conn


def add_subscription(sub: dict) -> None:
    endpoint = sub["endpoint"]
    keys = sub.get("keys", {})
    with _conn() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO push_subscriptions (endpoint, p256dh, auth) VALUES (?, ?, ?)",
            (endpoint, keys.get("p256dh", ""), keys.get("auth", "")),
        )


def remove_subscription(endpoint: str) -> None:
    with _conn() as conn:
        conn.execute("DELETE FROM push_subscriptions WHERE endpoint = ?", (endpoint,))


def get_all_subscriptions() -> list[dict]:
    with _conn() as conn:
        rows = conn.execute(
            "SELECT endpoint, p256dh, auth FROM push_subscriptions"
        ).fetchall()
    return [{"endpoint": r[0], "keys": {"p256dh": r[1], "auth": r[2]}} for r in rows]


# --- sending ---

def send_push_to_all(message: str) -> None:
    if not VAPID_PRIVATE_KEY or not VAPID_PUBLIC_KEY:
        print("Warning: VAPID keys not configured — skipping push notifications")
        return

    subscriptions = get_all_subscriptions()
    if not subscriptions:
        return

    dead: list[str] = []
    for sub in subscriptions:
        try:
            webpush(
                subscription_info=sub,
                data=message,
                vapid_private_key=VAPID_PRIVATE_KEY,
                vapid_claims={"sub": f"mailto:{VAPID_EMAIL}"},
            )
        except WebPushException as e:
            if e.response is not None and e.response.status_code in (404, 410):
                dead.append(sub["endpoint"])   # subscription expired
            else:
                print(f"Push failed ({sub['endpoint'][:40]}...): {e}")

    for endpoint in dead:
        remove_subscription(endpoint)


# --- VAPID key generation utility ---

def _generate_keys() -> None:
    import base64
    from cryptography.hazmat.primitives.serialization import (
        Encoding, NoEncryption, PrivateFormat, PublicFormat,
    )
    from py_vapid import Vapid

    v = Vapid()
    v.generate_keys()

    priv_b64 = base64.urlsafe_b64encode(
        v._private_key.private_bytes(Encoding.DER, PrivateFormat.PKCS8, NoEncryption())
    ).decode().rstrip("=")

    pub_b64 = base64.urlsafe_b64encode(
        v._public_key.public_bytes(Encoding.X962, PublicFormat.UncompressedPoint)
    ).decode().rstrip("=")

    print("Add these to your .env file:\n")
    print(f"VAPID_PRIVATE_KEY={priv_b64}")
    print(f"VAPID_PUBLIC_KEY={pub_b64}")


if __name__ == "__main__":
    if "--generate-keys" in sys.argv:
        _generate_keys()
    else:
        print("Usage: python -m server.push --generate-keys")
