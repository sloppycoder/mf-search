# Define investment-related keywords (lowercase for case-insensitive matching)

geo_keywords = [
    "u.s.",
    "u.s",
    "us",
    "global",
    "international",
    "emerging",
    "developed",
    "foreign",
]

investment_keywords = {
    "equity",
    "equities",
    "eq",
    "stock",
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
    "quant",
}

# Words that frequently appear *before* investment terms
# and should be included in strategy
strategy_prefix_words = {
    "large",
    "lg",
    "sm",
    "small",
    "smid",
    "small-mid",
    "mid",
    "income",
    "quality",
    "strategic",
    "flexible",
    "core",
    "cor",
    "value",
    "select",
    "sel",
    "dividend",
    "div",
    "deep",
    "diversified",
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
