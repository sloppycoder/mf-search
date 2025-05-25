# Define investment-related keywords (lowercase for case-insensitive matching)

import re
from typing import Iterator

geo_keywords = [
    "us",
    "global",
    "international",
    "emerging",
    "developed",
    "foreign",
    "esg",
    "sustainable",
    "sustsocial",
]

investment_keywords = {
    "equity",
    "equities",
    "eq",
    "stock",
    "stk",
    "cap",
    "cp",
    "income",
    "value",
    "val",
    "portfolio",
    "bond",
    "blend",
    "markets",
    "market",
    "mkt",
    "dividend",
    "growth",
    "gr",
    "instl",
    "institutional",
    "quant",
    "balanced",
    "secular",
}

# Words that frequently appear *before* investment terms
# and should be included in strategy
strategy_prefix_words = {
    "large",
    "lg",
    "lgcp",
    "lg-cp",
    "midcap",
    "sm",
    "small",
    "smid",
    "small-mid",
    "sm/md",
    "s-m",
    "small-cap",
    "mid",
    "mid-cap",
    "micro-cap",
    "micro",
    "quality",
    "strategic",
    "flexible",
    "flex",
    "core",
    "cor",
    "value",
    "select",
    "sel",
    "dividend",
    "div",
    "deep",
    "diversified",
    "targeted",
    "adaptive",
    "behvrl",
    "behavioral",
    "behav",
    "series",
    "ser",
}


def _word_index_in_list(words, keywords):
    for i, word in enumerate(words):
        if word in keywords and i > 0:
            return i
    return -1


def derive_fund_company_name(fund_name: str) -> str:
    """
    derive the search term to use from a fund name
    e.g.
    Eaton Vance Large-Cap Value R6 -> Eaton Vance
    Fidelity Advisor® Equity Income Z -> Fidelity Advisor

    """
    words = fund_name.split()
    lower_words = [
        word.lower() for word in words
    ]  # Convert words to lowercase for comparison

    # Identify where the investment strategy starts
    geo_index = _word_index_in_list(lower_words, geo_keywords)
    investment_index = _word_index_in_list(lower_words, investment_keywords)
    strategy_index = _word_index_in_list(lower_words, strategy_prefix_words)

    indexes = [i for i in [geo_index, investment_index, strategy_index] if i > 0]
    if indexes:
        start_index = min(indexes)
    else:
        start_index = len(words)

    return " ".join(words[:start_index])


def _normalize(orig_fund_name: str) -> str:
    # normalize the fund name
    # replace common abbrev and symbols
    fund_name = orig_fund_name.replace("&", " and ")
    fund_name = re.sub(r"U\.S\.", "US", fund_name)
    fund_name = re.sub(r"U\.S", "US", fund_name)
    fund_name = re.sub(r"\bInv\b", "Investment", fund_name)
    fund_name = re.sub(r"\bCo\b", "Company", fund_name)
    fund_name = fund_name.replace("®", "")
    fund_name = fund_name.replace("™", "")
    fund_name = fund_name.replace('"', "")
    fund_name = fund_name.replace("'", "")
    fund_name = fund_name.replace("\u00ae", "")

    # fund names that yeidls no match with SEC search page
    # and must be transformed to match
    fund_name = fund_name.replace("JHancock", "Hancock John")
    fund_name = fund_name.replace("TRP ", "T.RowePrice")

    return fund_name.strip()


def enumerate_possible_company_names(orig_fund_name: str) -> Iterator[str]:
    """enumerate various company names for use with search"""
    fund_name = _normalize(orig_fund_name)
    if "/" in fund_name:
        parts = fund_name.split("/")
        yield parts[0].strip()
    else:
        yield fund_name.strip()

    # flow will come here if none of the above yielded satisfactory results
    company_name = derive_fund_company_name(fund_name)
    parts = [word.strip() for word in company_name.split(" ") if len(word.strip()) > 1]
    for i in range(len(parts), 0, -1):
        yield " ".join(parts[:i])
