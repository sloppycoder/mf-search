from pathlib import Path

from sec_search import (
    mutual_fund_search,
    search_fund_name_with_variations,
)
from sec_search.util import derive_fund_company_name

cache_dir = Path(__file__).parent / "cache"


def test_mutual_fund_search():
    result = mutual_fund_search({"company": "Strategic Advisers"}, cache_dir=cache_dir)
    assert result


def test_derive_fund_company_name_batch():
    with open(Path(__file__).parent / "../tmp/fundnames.csv") as f:
        funds = [line.strip() for line in f.readlines()][1:][:50]

    for fund in funds:
        company_name = derive_fund_company_name(fund)
        print(f"{company_name} -> {fund}")
    # company_name_1, _ = derive_fund_company_name("JHancock U.S. Growth A")
    # company_name_2, _ = split_fund_name("Russell Inv US Strategic Equity A")
    # company_name_3, _ = split_fund_name("EquityCompass Quality Dividend A")
    # company_name_4, _ = split_fund_name("Epoch US Small-Mid Cap Equity Adv")
    # company_name_5, _ = split_fund_name("Segall Bryant & Hamill Sm Cp Val Ins")
    # company_name_6, _ = split_fund_name("GMO US Flexible Equities III")
    assert True


def test_dervie_fund_company_name():
    # fund = "Towle Deep Value"
    fund = "Strategic Advisers® Core Multi-Mgr"
    company_name_1 = derive_fund_company_name(fund)
    assert company_name_1


def test_pick_match_with_llm():
    fund_name = "Russell Inv US Strategic Equity A"
    result = search_fund_name_with_variations(fund_name, cache_dir=cache_dir)
    assert result == "0000351601"
