import re

import spacy

# Load spaCy's small English model
nlp = spacy.load("en_core_web_sm")

# Define investment-related keywords (lowercase for case-insensitive matching)
investment_keywords = {
    "equity",
    "stock",
    "cap",
    "income",
    "growth",
    "fund",
    "value",
    "portfolio",
    "bond",
    "blend",
    "markets",
}

# Words that frequently appear *before* investment terms and
# should be included in strategy
strategy_prefix_words = {
    "large",
    "small",
    "smid",
    "mid",
    "us",
    "u.s.global",
    "international",
    "emerging",
    "income",
}


def split_fund_name(input_fund_name):
    fund_name = input_fund_name.replace("U.S.", "US")  # Normalize "U.S." to "US"
    fund_name = re.sub(r"\bInv\b", "Investment", fund_name)

    words = fund_name.split()
    lower_words = [
        word.lower() for word in words
    ]  # Convert words to lowercase for comparison

    # Identify where the investment strategy starts
    for i, lower_word in enumerate(lower_words):
        if lower_word in investment_keywords:
            start_index = i  # Assume this is the start of the strategy

            # If the previous word is in strategy prefixes, include it in the strategy
            if i > 0 and lower_words[i - 1] in strategy_prefix_words:
                start_index = i - 1

            # If "US" is in the company part, move it into strategy
            while start_index > 0 and lower_words[start_index - 1] == "us":
                start_index -= 1

            return " ".join(words[:start_index]), " ".join(
                words[start_index:]
            )  # Return original case words

    return (
        fund_name,
        "",
    )  # If no investment strategy is found, assume the whole name is the company


# Example fund names (with mixed case)
fund_names = [
    "Mairs & Power Small Cap",
    "Towle Deep Value",
    "JHancock U.S. Growth A",
    "Christopher Weil & Co Core Investment",
    "AMG GW&K Small Cap Value II N",
    "Eaton Vance Atlanta Capital Sel Eq A",
    "Russell Inv US Large Cap Equity A",
    "Russell Inv US Mid Cap Equity A",
    "JNL/American Funds® Growth A",
    "JNL/Newton Equity Income A",
    "Satuit Capital US Smid Cap A",
    "American Beacon The London Co Inc Eq A",
    "Russell Inv US Strategic Equity A",
    "JNL/Morgan Stanley Mid Cap Growth A",
    "AAM/Bahl & Gaynor Income Growth I",
]

# Apply function
for fund in fund_names:
    company, strategy = split_fund_name(fund)
    print(f"Company: {company}, Strategy: {strategy}")
