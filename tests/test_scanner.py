"""
Basic smoke tests for the scanner package.
Run with: pytest tests/ -v
"""

from datetime import date

from scanner.models import Paper


def make_paper(**kwargs) -> Paper:
    defaults = dict(
        id="2404.00001",
        title="Test Paper",
        authors=["Author A"],
        abstract="This is a test abstract.",
        url="https://arxiv.org/abs/2404.00001",
        published=date.today(),
        source="arxiv",
    )
    return Paper(**{**defaults, **kwargs})


def test_paper_to_dict():
    p = make_paper()
    d = p.to_dict()
    assert d["id"] == "2404.00001"
    assert d["title"] == "Test Paper"
    assert isinstance(d["published"], str)


def test_paper_to_dict_optional_fields():
    p = make_paper(categories=["cs.LG"], citation_count=42)
    d = p.to_dict()
    assert d["categories"] == ["cs.LG"]
    assert d["citation_count"] == 42


def test_db_init_and_mark_seen(tmp_path):
    from scanner.db import filter_unseen, init_db, mark_seen

    db = tmp_path / "test.db"
    init_db(db)

    ids = ["paper1", "paper2", "paper3"]
    assert filter_unseen(db, ids) == ids   # all unseen initially

    mark_seen(db, ["paper1", "paper2"])
    assert filter_unseen(db, ids) == ["paper3"]

    mark_seen(db, ["paper1"])              # duplicate — should not raise
    assert filter_unseen(db, ["paper1"]) == []


def test_load_config():
    from scanner import load_config
    config = load_config()
    assert "scan" in config
    assert "sources" in config


def test_load_interest_profile():
    from scanner import load_interest_profile
    profile = load_interest_profile()
    assert "topics" in profile
    assert "keywords" in profile
    assert isinstance(profile["min_score"], float)
