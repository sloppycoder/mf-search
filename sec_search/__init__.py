import json
from urllib.parse import urlencode

import requests
from bs4 import BeautifulSoup
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_fixed

from log import progress, rich_log

from .llm import pick_match_with_llm
from .util import enumerate_possible_company_names

DEFAULT_USER_AGENT = "Lee Lynn (hayashi@yahoo.com)"


class RateLimitedError(Exception):
    pass


def search_fund_with_ticker(ticker: str, entry_name: str) -> str:
    rich_log(progress(entry_name, f"using fund search with ticker {ticker}"))
    funds = _sec_fund_search({"ticker": ticker})
    if funds:
        return list(funds[0])[0]
    return ""


def search_fund_name_with_variations(  # noqa: C901
    fund_name: str,
    entry_name: str,
    use_prospectus_search: bool = False,
    use_llm: bool = True,
) -> tuple[str, bool]:
    for company_name in enumerate_possible_company_names(fund_name):
        if use_prospectus_search:
            rich_log(progress(entry_name, f"using prospectus search with {company_name}"))
            funds = _sec_prospectus_search(
                {
                    "type": "485",
                    "action": "getcompany",
                    "company": company_name[:20],
                }
            )
        else:
            rich_log(progress(entry_name, f"using fund search with {company_name}"))
            funds = _sec_fund_search({"company": company_name})

        if len(funds) == 0:
            continue
        elif len(funds) == 1:
            return list(funds[0])[0], False
        else:
            ciks = {list(item)[0] for item in funds}
            if len(ciks) == 1:
                return ciks.pop(), False

            if use_llm:
                rich_log(
                    progress(
                        entry_name,
                        f"using llm to pick closest match for {fund_name} amount {len(funds)} candidates",  # noqa: E501
                    )
                )
                llm_result = pick_match_with_llm(fund_name, funds)
                if llm_result:
                    try:
                        result = json.loads(llm_result)
                        if "cik" in result:
                            return result["cik"], True
                    except json.JSONDecodeError:
                        pass
            else:
                return "/".join(ciks), False

    return "", False


def _sec_fund_search(search_terms: dict[str, str]) -> list[str]:
    # UI at
    # https://www.sec.gov/search-filings/mutual-funds-search
    url = "https://www.sec.gov/cgi-bin/series"
    response = _sec_search(url, search_terms)
    if response:
        return _parse_fund_search_result(response)
    return []


def _sec_prospectus_search(search_terms: dict[str, str]) -> list[str]:
    # UI at
    # https://www.sec.gov/search-filings/mutual-funds-search/mutual-fund-prospectuses-search
    url = "https://www.sec.gov/cgi-bin/browse-edgar"
    search_terms.update(
        {
            "start": "0",
            "count": "500",
            "hidefilings": "0",
        }
    )
    response = _sec_search(url, search_terms)
    if response:
        return _parse_prospectus_search_result(response)
    return []


@retry(
    stop=stop_after_attempt(3),
    wait=wait_fixed(5),
    retry=retry_if_exception_type(RateLimitedError),
)
def _sec_search(url: str, search_terms: dict[str, str]) -> str | None:
    query_string = urlencode(search_terms)
    headers = {"User-Agent": DEFAULT_USER_AGENT}
    response = requests.get(f"{url}?{query_string}", headers=headers)
    if response.status_code == 200:
        return response.text
    elif response.status_code == 429:  # rate limited
        raise RateLimitedError()
    else:
        response.raise_for_status()


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
