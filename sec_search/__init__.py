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

FUND_SEARCH_URL = "https://www.sec.gov/cgi-bin/series"
PROSPECTUS_SEARCH_URL = "https://www.sec.gov/cgi-bin/browse-edgar"

DEFAULT_USER_AGENT = "Lee Lynn (hayashi@yahoo.com)"

default_cache_dir = Path(__file__).parent / "../cache"


class RateLimitedError(Exception):
    pass


def search_fund_with_ticker(ticker: str, cache_dir: Path = default_cache_dir) -> str:
    funds = _sec_search_with_cache(
        FUND_SEARCH_URL, {"ticker": ticker}, cache_dir=cache_dir
    )
    if funds:
        return list(funds[0])[0]

    return ""


def search_fund_name_with_variations(
    fund_name: str,
    use_prospectus_search: bool = False,
    cache_dir: Path = default_cache_dir,
    use_llm: bool = True,
) -> str:
    for company_name in _enumerate_possible_company_names(_normalize(fund_name)):
        if use_prospectus_search:
            search_terms = {
                "type": "485",
                "action": "getcompany",
                "company": company_name[:20],
            }
            url = PROSPECTUS_SEARCH_URL
        else:
            search_terms = {"company": company_name}
            url = FUND_SEARCH_URL

        funds = _sec_search_with_cache(url, search_terms, cache_dir=cache_dir)

        if len(funds) == 0:
            continue
        elif len(funds) == 1:
            return list(funds[0])[0]
        else:
            ciks = {list(item)[0] for item in funds}
            if len(ciks) == 1:
                return ciks.pop()

            if use_llm:
                llm_result = pick_match_with_llm(fund_name, funds)
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


@retry(
    stop=stop_after_attempt(3),  # Stop after 5 attempts
    wait=wait_fixed(5),  # Wait 5 seconds between retries
    retry=retry_if_exception_type(RateLimitedError),
)
def _sec_search_with_cache(
    url: str,
    search_terms: dict[str, str],
    cache_dir: Path = default_cache_dir,
) -> list[str]:
    """
    check cache directory and return content of cache file if it already exists
    otherwise send request using requests and save content
    to cache
    """
    is_prospectus_search = (
        "action" in search_terms and search_terms["action"] == "getcompany"
    )  # noqa: E501

    if is_prospectus_search:
        cache_suffix = "_p"
    else:
        cache_suffix = ""

    cache_filename = _parameters_checksum(search_terms) + cache_suffix + ".html"
    # print(f"*** {cache_filename}")
    cache_file = cache_dir / cache_filename
    result = (
        cache_file.read_text() if cache_file.exists() else _sec_search(url, search_terms)
    )

    if result:
        if not cache_file.exists():
            cache_file.write_text(result)

        if is_prospectus_search:
            return _parse_prospectus_search_result(result)
        else:
            return _parse_fund_search_result(result)
    else:
        return []


def _sec_search(url: str, search_terms: dict[str, str]) -> str | None:
    query_string = urlencode(search_terms)
    headers = {"User-Agent": DEFAULT_USER_AGENT}
    response = requests.get(f"{url}?{query_string}", headers=headers)
    if response.status_code == 200:
        return response.text
    elif response.status_code == 429:  # rate limited
        raise RateLimitedError()
    else:
        return response.raise_for_status()


def _parse_fund_search_result(html_content: str):
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


def _parse_prospectus_search_result(html_content: str):
    soup = BeautifulSoup(html_content, "html.parser")
    tables = soup.find_all("table")

    for table in tables:
        headers = [th.get_text(strip=True) for th in table.find_all("th")]  # type: ignore

        if "CIK" in headers:
            data = []
            rows = table.find_all("tr")[1:]  # Skip header row # type: ignore

            for row in rows:
                cells = row.find_all(["td", "th"])  # Get all columns # type: ignore
                if not cells:
                    continue  # Skip empty rows

                row_data = {}
                for i, cell in enumerate(cells):
                    key = headers[i]  # Match column header
                    link = cell.find("a")  # Check if cell has a link # type: ignore
                    value = link.text.strip() if link else cell.get_text(strip=True)  # type: ignore
                    row_data[key] = value

                data.append((row_data["CIK"], "", "", "", "", row_data["Company"]))

            return data  # Return the first matching table

    return []


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
