import csv
from pathlib import Path

import pytest

from main import read_funds
from sec_search import (
    search_fund_name_with_variations,
    search_fund_with_ticker,
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


def test_fund_search_with_name():
    assert (
        search_fund_name_with_variations(
            "Westfield Capital",
            cache_dir=cache_dir,
        )
        == "0000890540"
    )
    assert (
        search_fund_name_with_variations(
            "Russell Inv US Strategic Equity A",
            cache_dir=cache_dir,
        )
        == "0000351601"
    )

    assert not search_fund_name_with_variations("Thaler", cache_dir=cache_dir)


def test_fund_search_with_ticker():
    assert search_fund_with_ticker("LOCSX", cache_dir=cache_dir) == "0001014913"
    assert search_fund_with_ticker("BLAH", cache_dir=cache_dir) == ""


def test_prospectus_search():
    assert (
        search_fund_name_with_variations(
            "Capstone Large Cap Equity C",
            use_prospectus_search=True,
            cache_dir=cache_dir,
            use_llm=True,
        )
        == "0000079179"
    )
    assert (
        search_fund_name_with_variations(
            "Flutter",
            use_prospectus_search=True,
            cache_dir=cache_dir,
            use_llm=False,
        )
        == ""
    )


@pytest.mark.skip(reason="This test is for manual use only")
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
    fund = "Strategic Advisers® Core Multi-Mgr"
    company_name_1 = derive_fund_company_name(fund)
    assert company_name_1


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
    assert prompt
