import csv
from pathlib import Path

from main import read_funds
from sec_search import (
    mutual_fund_search,
    search_fund_name_with_variations,
)
from sec_search.llm import _derive_company_name
from sec_search.util import derive_fund_company_name

cache_dir = Path(__file__).parent / "cache"
data_dir = Path(__file__).parent / "data"


def test_read_funds():
    funds = read_funds(data_dir / "test_fund_ticker.csv")
    assert len(funds) == 4
    assert funds[0]["ticker"] == "LOCSX"
    assert funds[1]["ticker"] == ""
    assert funds[2]["ticker"] == ""
    assert funds[3]["ticker"] == "RFISX"


def test_mutual_fund_search():
    result = mutual_fund_search({"company": "Westfield Capital"}, cache_dir=cache_dir)
    assert result and len(result) == 4
    result = mutual_fund_search({"ticker": "LOCSX"}, cache_dir=cache_dir)
    assert result and len(result) == 1
    result = mutual_fund_search({"ticker": "Thaler"}, cache_dir=cache_dir)
    assert not result


def test_derive_fund_company_name_batch():
    with open(Path(__file__).parent / "../tmp/cik_map.csv") as f:
        reader = csv.reader(f)
        next(reader)  # Skip the header line

        bad_list = []
        for row in reader:
            if not row[2]:
                bad_list.append(row[0])

    with open(Path(__file__).parent / "../tmp/no_match.csv", "w") as f:
        bad_list.sort()
        for fund in bad_list:
            f.write(fund + "\n")

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


def test_fund_name_prompt():
    funds = [
        "JNL/Newton Equity Income A",
        "Multi-Manager Small Cap Eq Strat A",
        "JNL/Morgan Stanley Mid Cap Growth A",
        "GMO US Flexible Equities III",
        "JH Adaptive Rsk Mgd U.S EqPort-Svc",
        "Fidelity Advisor® Ser Oppc Insights",
        "Fidelity Advisor® Ser Equity-Income",
        "DFA US Large Cap Growth Instl",
        "Snow Capital Infl Advtgd Equities A",
    ]
    prompt = _derive_company_name(funds)
    print(prompt)
    assert prompt
