import hashlib
from pathlib import Path
from urllib.parse import urlencode

import requests

BASE_URL = "https://www.sec.gov/cgi-bin/series"
DEFAULT_USER_AGENT = "Lee Lynn (hayashi@yahoo.com)"

default_cache_dir = Path(__file__).parent / "../cache"


def parameters_checksum(params: dict[str, str]) -> str:
    return hashlib.md5(str(params).encode()).hexdigest()


def mutual_fund_search(
    search_terms: dict[str, str],
    cache_dir: Path = default_cache_dir,
) -> str:
    """
    check cache directory and return content of cache file if it already exists
    otherwise send request using requests and save content
    to cache
    """
    cache_file = cache_dir / f"{parameters_checksum(search_terms)}.html"
    if cache_file.exists():
        return cache_file.read_text()

    result = sec_mutual_fund_search(search_terms)
    cache_file.write_text(result)
    return result


def sec_mutual_fund_search(search_terms: dict[str, str]) -> str:
    query_string = urlencode(search_terms)
    headers = {"User-Agent": DEFAULT_USER_AGENT}
    response = requests.get(f"{BASE_URL}?{query_string}", headers=headers)
    response.raise_for_status()  # Raise an exception for HTTP errors
    return response.text
