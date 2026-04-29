from datetime import date

import httpx

from .models import Paper

S2_API = "https://api.semanticscholar.org/graph/v1/paper/search"
S2_FIELDS = "title,authors,abstract,url,year,citationCount,externalIds,publicationDate"


def fetch_recent(keywords: list[str], max_results: int = 20) -> list[Paper]:
    if not keywords:
        return []

    # S2 works best with a focused query; use the first 5 keywords
    query = " OR ".join(f'"{k}"' for k in keywords[:5])
    params = {
        "query": query,
        "limit": max_results,
        "fields": S2_FIELDS,
        "publicationDateOrYear": str(date.today().year),
    }

    try:
        resp = httpx.get(S2_API, params=params, timeout=30)
    except httpx.RequestError:
        return []

    if resp.status_code == 429:
        print("Semantic Scholar: rate limited, skipping")
        return []
    if not resp.is_success:
        print(f"Semantic Scholar: HTTP {resp.status_code}, skipping")
        return []

    papers: list[Paper] = []
    for item in resp.json().get("data", []):
        if not item.get("abstract"):
            continue

        arxiv_id = (item.get("externalIds") or {}).get("ArXiv")
        url = f"https://arxiv.org/abs/{arxiv_id}" if arxiv_id else (item.get("url") or "")

        pub_date = item.get("publicationDate")
        if pub_date:
            try:
                published = date.fromisoformat(pub_date)
            except ValueError:
                published = date(item.get("year") or date.today().year, 1, 1)
        else:
            published = date(item.get("year") or date.today().year, 1, 1)

        paper_id = f"s2_{item['paperId']}" if not arxiv_id else arxiv_id
        papers.append(
            Paper(
                id=paper_id,
                title=item["title"],
                authors=[a["name"] for a in (item.get("authors") or [])],
                abstract=item["abstract"],
                url=url,
                published=published,
                source="semantic_scholar",
                citation_count=item.get("citationCount"),
            )
        )
    return papers
