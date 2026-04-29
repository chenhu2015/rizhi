from dataclasses import dataclass, field
from datetime import date


@dataclass
class Paper:
    id: str
    title: str
    authors: list[str]
    abstract: str
    url: str
    published: date
    source: str                          # "arxiv" | "semantic_scholar"
    categories: list[str] = field(default_factory=list)
    citation_count: int | None = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "authors": self.authors,
            "abstract": self.abstract,
            "url": self.url,
            "published": self.published.isoformat(),
            "source": self.source,
            "categories": self.categories,
            "citation_count": self.citation_count,
        }
