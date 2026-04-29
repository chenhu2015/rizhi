"""
Main fetch script. Run as: python -m scanner.fetch

Fetches new papers from all configured sources, filters already-seen ones,
marks them as seen, and prints a JSON array to stdout for the Claude Code
agent to consume and score.
"""

import json
import sys
from pathlib import Path

# Ensure stdout handles Unicode on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from scanner import load_config, load_interest_profile
from scanner.arxiv_client import fetch_recent as arxiv_fetch
from scanner.db import filter_unseen, init_db, mark_seen
from scanner.web_client import fetch_recent as s2_fetch


def main() -> None:
    config = load_config()
    profile = load_interest_profile()

    db_path = Path(config["storage"]["db_path"])
    init_db(db_path)

    papers = []

    if config["sources"].get("arxiv"):
        arxiv_papers = arxiv_fetch(
            days_back=config["scan"]["days_back"],
            max_results=config["scan"]["max_results_arxiv"],
        )
        papers.extend(arxiv_papers)

    if config["sources"].get("semantic_scholar"):
        s2_papers = s2_fetch(
            keywords=profile.get("keywords", []),
            max_results=config["scan"]["max_results_s2"],
        )
        papers.extend(s2_papers)

    # deduplicate by id (S2 may return papers that arxiv already fetched)
    papers = list({p.id: p for p in papers}.values())

    # filter papers already seen in previous runs
    all_ids = [p.id for p in papers]
    unseen_ids = set(filter_unseen(db_path, all_ids))
    papers = [p for p in papers if p.id in unseen_ids]

    # mark all fetched papers as seen so they don't appear tomorrow
    mark_seen(db_path, list(unseen_ids))

    print(json.dumps([p.to_dict() for p in papers], indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
