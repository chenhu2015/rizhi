import time
from datetime import date, timedelta

import feedparser
import httpx

from .models import Paper

ARXIV_API = "https://export.arxiv.org/api/query"

# Categories covering ML, AI, CV, NLP, and statistics
CATEGORIES = ["cs.LG", "cs.AI", "cs.CV", "cs.CL", "stat.ML"]


def fetch_recent(days_back: int = 1, max_results: int = 100) -> list[Paper]:
    query = " OR ".join(f"cat:{c}" for c in CATEGORIES)
    params = {
        "search_query": query,
        "start": 0,
        "max_results": max_results,
        "sortBy": "submittedDate",
        "sortOrder": "descending",
    }
    # arxiv asks for polite delays; retry once on 429 with a 65-second wait
    for attempt in range(2):
        resp = httpx.get(ARXIV_API, params=params, timeout=30)
        if resp.status_code == 429 and attempt == 0:
            print("arxiv: rate limited, waiting 65 s before retry…")
            time.sleep(65)
            continue
        resp.raise_for_status()
        break

    feed = feedparser.parse(resp.text)
    cutoff = date.today() - timedelta(days=days_back)

    papers: list[Paper] = []
    for entry in feed.entries:
        published = date.fromisoformat(entry.published[:10])
        if published < cutoff:
            break
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
