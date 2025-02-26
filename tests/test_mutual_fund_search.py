from pathlib import Path

from sec_search import mutual_fund_search

cache_dir = Path(__file__).parent / "cache"


def test_mutual_fund_search():
    result = mutual_fund_search({"company": "Strategic Advisers"}, cache_dir=cache_dir)
    assert result
