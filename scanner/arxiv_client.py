import time
from datetime import date, timedelta

import feedparser
import httpx

from .models import Paper

ARXIV_API = "https://export.arxiv.org/api/query"


def _fetch(params: dict) -> list[Paper]:
    """Execute an arxiv API request with one 429 retry."""
    for attempt in range(2):
        resp = httpx.get(ARXIV_API, params=params, timeout=30)
        if resp.status_code == 429 and attempt == 0:
            print("arxiv: rate limited, waiting 65 s before retry…", flush=True)
            time.sleep(65)
            continue
        resp.raise_for_status()
        break

    feed = feedparser.parse(resp.text)
    papers: list[Paper] = []
    for entry in feed.entries:
        published = date.fromisoformat(entry.published[:10])
        arxiv_id = entry.id.split("/abs/")[-1]
        papers.append(
            Paper(
                id=arxiv_id,
                title=entry.title.replace("\n", " ").strip(),
                authors=[a.name for a in entry.authors],
                abstract=entry.summary.replace("\n", " ").strip(),
                url=entry.id,
                published=published,
                source="arxiv",
                categories=[t.term for t in entry.tags],
            )
        )
    return papers


def fetch_by_query(query: str, max_results: int = 30) -> list[Paper]:
    """Search arxiv with an arbitrary query string (e.g. 'ti:agentic RL')."""
    params = {
        "search_query": query,
        "start": 0,
        "max_results": max_results,
        "sortBy": "submittedDate",
        "sortOrder": "descending",
    }
    return _fetch(params)


def fetch_recent(days_back: int = 1, max_results: int = 100) -> list[Paper]:
    """Fetch recent papers across broad ML/AI categories (legacy broad fetch)."""
    categories = ["cs.LG", "cs.AI", "cs.CV", "cs.CL", "stat.ML"]
    query = " OR ".join(f"cat:{c}" for c in categories)
    params = {
        "search_query": query,
        "start": 0,
        "max_results": max_results,
        "sortBy": "submittedDate",
        "sortOrder": "descending",
    }
    cutoff = date.today() - timedelta(days=days_back)
    return [p for p in _fetch(params) if p.published >= cutoff]
