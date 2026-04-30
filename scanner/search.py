"""
Agentic search tool. Claude calls this with its own query string.

Usage:
  python -m scanner.search "agentic reinforcement learning reward shaping"
  python -m scanner.search "vision language model grounding" --source s2 --max 15
  python -m scanner.search "GRPO training efficiency" --source both --max 30

Prints a JSON array of unseen papers to stdout.
"""

import argparse
import json
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from scanner import load_config
from scanner.arxiv_client import fetch_by_query as arxiv_search
from scanner.db import filter_unseen, init_db, mark_seen
from scanner.web_client import fetch_recent as s2_fetch


def main() -> None:
    parser = argparse.ArgumentParser(description="Search for papers with a custom query.")
    parser.add_argument("query", help="Search query string")
    parser.add_argument(
        "--source",
        default="both",
        choices=["arxiv", "s2", "both"],
        help="Which source to query (default: both)",
    )
    parser.add_argument("--max", type=int, default=30, help="Max results per source")
    args = parser.parse_args()

    config = load_config()
    db_path = Path(config["storage"]["db_path"])
    init_db(db_path)

    papers = []

    if args.source in ("arxiv", "both"):
        papers.extend(arxiv_search(args.query, max_results=args.max))

    if args.source in ("s2", "both"):
        # S2 works with keyword list; split the query into terms
        keywords = args.query.split()
        papers.extend(s2_fetch(keywords=keywords, max_results=max(args.max // 2, 10)))

    # deduplicate across sources
    papers = list({p.id: p for p in papers}.values())

    # filter already-seen papers
    unseen_ids = set(filter_unseen(db_path, [p.id for p in papers]))
    papers = [p for p in papers if p.id in unseen_ids]

    # mark as seen so tomorrow's run skips them
    mark_seen(db_path, list(unseen_ids))

    print(json.dumps([p.to_dict() for p in papers], indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
