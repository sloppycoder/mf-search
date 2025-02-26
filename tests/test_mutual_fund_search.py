from pathlib import Path

from sec_search import mutual_fund_search, split_fund_name

cache_dir = Path(__file__).parent / "cache"


def test_mutual_fund_search():
    rows = mutual_fund_search({"company": "Strategic Advisers"}, cache_dir=cache_dir)
    assert rows


def test_split_fund_name():
    company_name_1, _ = split_fund_name("JHancock U.S. Growth A")
    company_name_2, _ = split_fund_name("Russell Inv US Strategic Equity A")
    company_name_3, _ = split_fund_name("EquityCompass Quality Dividend A")
    company_name_4, _ = split_fund_name("Epoch US Small-Mid Cap Equity Adv")
    company_name_5, _ = split_fund_name("Segall Bryant & Hamill Sm Cp Val Ins")
    company_name_6, _ = split_fund_name("GMO US Flexible Equities III")
    assert company_name_4
