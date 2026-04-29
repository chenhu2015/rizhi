import sqlite3
from pathlib import Path


def init_db(db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS seen_papers (
                id TEXT PRIMARY KEY,
                seen_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
        """)


def filter_unseen(db_path: Path, paper_ids: list[str]) -> list[str]:
    if not paper_ids:
        return []
    with sqlite3.connect(db_path) as conn:
        placeholders = ",".join("?" * len(paper_ids))
        seen = {
            row[0] for row in conn.execute(
                f"SELECT id FROM seen_papers WHERE id IN ({placeholders})", paper_ids
            )
        }
    return [pid for pid in paper_ids if pid not in seen]


def mark_seen(db_path: Path, paper_ids: list[str]) -> None:
    if not paper_ids:
        return
    with sqlite3.connect(db_path) as conn:
        conn.executemany(
            "INSERT OR IGNORE INTO seen_papers (id) VALUES (?)",
            [(pid,) for pid in paper_ids],
        )
