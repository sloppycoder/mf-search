from typing import Iterator

from dotenv import load_dotenv

from sec_search import mutual_fund_search, split_fund_name

load_dotenv()


def read_fund_names():
    with open("tmp/fundnames.csv", "r") as f:
        return [name.strip() for name in f.readlines()]


def enumerate_possible_company_names(fund_name: str) -> Iterator[str]:
    """enumerate various company names for use with search"""
    if "/" in fund_name:
        parts = fund_name.split("/")
        yield parts[0].strip()
    elif "®" in fund_name:
        parts = fund_name.split("®")
        yield parts[0].strip()
        yield parts[1].strip()
    else:
        yield fund_name.strip()

    # flow will come here if none of the above yielded satisfactory results
    company_name, _ = split_fund_name(fund_name.strip())
    yield company_name


def extract_ciks(search_result: list | None) -> list[str]:
    if search_result is None:
        return []

    ciks = set()
    for row in search_result:
        cik, *_ = row
        ciks.add(cik)
    return list(ciks)


def main():
    n_exact_match, n_multiple_match, n_no_match = 0, 0, 0

    for name in read_fund_names()[:500]:
        match_found = False
        for company_name in enumerate_possible_company_names(name.strip()):
            search_result = mutual_fund_search({"company": company_name})
            ciks = extract_ciks(search_result)
            n_matches = len(ciks) if ciks else 0
            if n_matches:
                if n_matches == 1:
                    n_exact_match += 1
                else:
                    n_multiple_match += 1

                match_found = True
                break

        if not match_found:
            print(f"'{name}',")
            n_no_match += 1

    print(
        f"Exact matches: {n_exact_match}, Multiple matches: {n_multiple_match}, No matches: {n_no_match}"  # noqa: E501
    )


if __name__ == "__main__":
    main()
