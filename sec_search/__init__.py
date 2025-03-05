import hashlib
import json
import re
from pathlib import Path
from typing import Iterator
from urllib.parse import urlencode

import requests
from bs4 import BeautifulSoup
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_fixed

from sec_search.llm import pick_match_with_llm
from sec_search.util import derive_fund_company_name

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
        if not cache_file.exists():
            cache_file.write_text(result)

        return parse_fund_search_result(result)
    else:
        return None


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


def search_fund_with_ticker(
    ticker: str, cache_dir: Path = default_cache_dir
) -> str | None:
    result = mutual_fund_search({"ticker": ticker})
    return list(result[0])[0] if result else None


def search_fund_name_with_variations(
    fund_name: str,
    cache_dir: Path = default_cache_dir,
    use_llm: bool = True,
) -> str:
    for company_name in _enumerate_possible_company_names(_normalize(fund_name)):
        search_result = mutual_fund_search({"company": company_name}, cache_dir=cache_dir)
        if search_result:
            if len(search_result) == 1:
                cik, *_ = search_result[0]
                return cik
            else:
                ciks = {list(item)[0] for item in search_result}
                if len(ciks) == 1:
                    return ciks.pop()

                if use_llm:
                    llm_result = pick_match_with_llm(fund_name, search_result)
                    if llm_result:
                        try:
                            result = json.loads(llm_result)
                            if "cik" in result:
                                return result["cik"]
                        except json.JSONDecodeError:
                            pass
                else:
                    return "/".join(ciks)

    return ""


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


def _enumerate_possible_company_names(orig_fund_name: str) -> Iterator[str]:
    """enumerate various company names for use with search"""
    fund_name = _normalize(orig_fund_name)
    if "/" in fund_name:
        parts = fund_name.split("/")
        yield parts[0].strip()
    else:
        yield fund_name.strip()

    # flow will come here if none of the above yielded satisfactory results
    company_name = derive_fund_company_name(fund_name)
    yield company_name


def _parameters_checksum(params: dict[str, str]) -> str:
    return hashlib.md5(str(params).encode()).hexdigest()
