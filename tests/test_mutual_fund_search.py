from pathlib import Path

from sec_search import (
    mutual_fund_search,
    search_fund_name_with_variations,
    split_fund_name,
)

cache_dir = Path(__file__).parent / "cache"


def test_mutual_fund_search():
    result = mutual_fund_search({"company": "Strategic Advisers"}, cache_dir=cache_dir)
    assert result


def test_split_fund_name():
    company_name_1, _ = split_fund_name("JHancock U.S. Growth A")
    company_name_2, _ = split_fund_name("Russell Inv US Strategic Equity A")
    company_name_3, _ = split_fund_name("EquityCompass Quality Dividend A")
    company_name_4, _ = split_fund_name("Epoch US Small-Mid Cap Equity Adv")
    company_name_5, _ = split_fund_name("Segall Bryant & Hamill Sm Cp Val Ins")
    company_name_6, _ = split_fund_name("GMO US Flexible Equities III")
    assert company_name_4


def test_pick_match_with_llm():
    fund_name = "Russell Inv US Strategic Equity A"
    result = search_fund_name_with_variations(fund_name, cache_dir=cache_dir)
    assert result == "0000351601"
