import hashlib
import re
from pathlib import Path
from urllib.parse import urlencode

import requests
import spacy
from bs4 import BeautifulSoup
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_fixed

# Load the English NLP model
nlp = spacy.load("en_core_web_sm")

BASE_URL = "https://www.sec.gov/cgi-bin/series"
DEFAULT_USER_AGENT = "Lee Lynn (hayashi@yahoo.com)"

default_cache_dir = Path(__file__).parent / "../cache"


class RateLimitedError(Exception):
    pass


@retry(
    stop=stop_after_attempt(3),  # Stop after 5 attempts
    wait=wait_fixed(5),  # Wait 5 seconds between retries
    retry=retry_if_exception_type(RateLimitedError),
)
def mutual_fund_search(
    search_terms: dict[str, str],
    cache_dir: Path = default_cache_dir,
) -> list | None:
    """
    check cache directory and return content of cache file if it already exists
    otherwise send request using requests and save content
    to cache
    """
    cache_file = cache_dir / f"{_parameters_checksum(search_terms)}.html"

    result = (
        cache_file.read_text()
        if cache_file.exists()
        else sec_mutual_fund_search(search_terms)
    )

    if result:
        parsed_data = parse_fund_search_result(result)
        if not cache_file.exists() and parsed_data:
            cache_file.write_text(result)

        return parsed_data


def sec_mutual_fund_search(search_terms: dict[str, str]) -> str | None:
    query_string = urlencode(search_terms)
    headers = {"User-Agent": DEFAULT_USER_AGENT}
    response = requests.get(f"{BASE_URL}?{query_string}", headers=headers)
    if response.status_code == 200:
        return response.text
    elif response.status_code == 429:  # rate limited
        raise RateLimitedError()
    else:
        return response.raise_for_status()


def parse_fund_search_result(html_content: str):
    soup = BeautifulSoup(html_content, "html.parser")
    tables = soup.find_all("table")
    extracted_rows = []

    table_started = False

    for table in tables:
        rows = table.find_all("tr")  # type: ignore

        for row in rows:
            cells = row.find_all(["td", "th"])  # type: ignore
            cell_texts = [cell.get_text(strip=True) for cell in cells]

            if any("CIK" in cell_text for cell_text in cell_texts):
                table_started = True  # Mark the start of the table
                continue  # Skip the header row

            if table_started:
                extracted_rows.append(tuple(cell_texts))

    return _flatten_rows(extracted_rows)


# Define investment-related keywords (lowercase for case-insensitive matching)
investment_keywords = {
    "equity",
    "equities",
    "eq",
    "stock",
    "cap",
    "cp",
    "income",
    "growth",
    "gr",
    "fund",
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
}

# Words that frequently appear *before* investment terms
# and should be included in strategy
strategy_prefix_words = {
    "large",
    "sm",
    "small",
    "smid",
    "small-mid",
    "mid",
    "us",
    "global",
    "international",
    "emerging",
    "income",
    "quality",
    "strategic",
    "flexible",
    "core",
    "cor",
    "value",
    "select",
    "sel",
}


def split_fund_name(input_fund_name: str) -> tuple[str, str]:
    fund_name = re.sub(r"U\.S\.", "US", input_fund_name)
    fund_name = re.sub(r"U\.S", "US", fund_name)
    fund_name = re.sub(r"\bInv\b", "Investment", fund_name)
    fund_name = re.sub(r"\bCo\b", "Company", fund_name)
    fund_name = fund_name.replace("&", " and ")

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


def _flatten_rows(data):
    processed_data = []
    current_cik = ""
    current_company = ""
    current_series = ""
    current_series_name = ""

    for row in data:
        cik, series, fund_id, fund_name, ticker = (
            row if len(row) == 5 else (row + ("",) * (5 - len(row)))
        )

        if cik:
            current_cik = cik
            current_company = series
            current_series = ""
            current_series_name = ""
        elif series:
            current_series = series
            current_series_name = fund_id
        elif fund_id:
            if current_cik:
                if current_series_name in fund_name:
                    full_fund_name = f"{current_company} {fund_name}"
                else:
                    full_fund_name = (
                        f"{current_company} {current_series_name} {fund_name}"
                    )
                processed_data.append(
                    (
                        current_cik,
                        current_series,
                        fund_id,
                        current_company,
                        current_series_name,
                        full_fund_name,
                        ticker,
                    )
                )

    return processed_data


def _parameters_checksum(params: dict[str, str]) -> str:
    return hashlib.md5(str(params).encode()).hexdigest()
