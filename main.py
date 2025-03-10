import csv
import re
import sys

from dotenv import load_dotenv

from sec_search import (
    search_fund_name_with_variations,
    search_fund_with_ticker,
)

load_dotenv()

ticker_regex = re.compile(r"([A-Z]{3,6})")


def read_funds(filename):
    funds = []
    try:
        with open(filename, "r") as f:
            reader = csv.DictReader(f)
            for row in reader:
                fund = {key.lower(): value.strip() for key, value in row.items()}
                if fund["ticker"] and not ticker_regex.match(fund["ticker"]):
                    fund["ticker"] = ""
                funds.append(fund)
        return funds
    except FileNotFoundError:
        return []


def main(
    source_file,
    output_file,
    overwrite=False,
    use_llm=True,
):
    n_total, n_no_match, offset = 0, 0, 0

    # read number of records in the output file
    if not overwrite:
        try:
            with open(output_file, "r") as f:
                offset = len(f.readlines()) - 1
        except FileNotFoundError:
            pass

    with open(output_file, "w" if overwrite else "a") as f:
        if overwrite:
            f.write("Name,Ticker,CIK,LLM\n")

        for item in read_funds(source_file)[offset:]:
            n_total += 1

            name = item["name"]
            ticker = item["ticker"]
            cik = ""

            # search with ticker if it's available
            if ticker:
                cik = search_fund_with_ticker(ticker)

            # if no match with ticker, search with fund name
            picked_by_llm = False
            if not cik:
                cik, picked_by_llm = search_fund_name_with_variations(
                    name,
                    use_prospectus_search=False,
                    use_llm=use_llm,
                )

            if not cik:
                cik, picked_by_llm = search_fund_name_with_variations(
                    name,
                    use_prospectus_search=True,
                    use_llm=use_llm,
                )

            if not cik:
                n_no_match += 1

            f.write(f"{name},{ticker},{cik},{1 if picked_by_llm else ''}\n")
            f.flush()

            if n_total % 100 == 0:
                print(f"## Total: {n_total:5d}, No matches: {n_no_match:4d}")

    print(f"## Total: {n_total:5d}, No matches: {n_no_match:4d}")


if __name__ == "__main__":
    main(
        source_file="tmp/fund_name_ticker.csv",
        output_file="tmp/cik_map.csv",
        overwrite=len(sys.argv) > 1 and sys.argv[1] == "-f",
        use_llm=True,
    )
