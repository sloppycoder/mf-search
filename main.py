from dotenv import load_dotenv

from sec_search import search_fund_name_with_variations

load_dotenv()


def read_fund_names():
    with open("tmp/fundnames.csv", "r") as f:
        return [name.strip() for name in f.readlines()]


def extract_ciks(search_result: list | None) -> list[str]:
    if search_result is None:
        return []

    ciks = set()
    for row in search_result:
        cik, *_ = row
        ciks.add(cik)
    return list(ciks)


def main():
    n_total, n_no_match = 0, 0

    with open("tmp/bad_list.txt", "w") as f:
        print("fund_name,cik")
        f.write("[")

        for name in read_fund_names()[:500]:
            n_total += 1
            cik = search_fund_name_with_variations(name)
            if cik:
                print(f"{name},{cik}")
            if cik is None:
                f.write(f"'{name}',")
                n_no_match += 1

        f.write("]")

    print(f"## Total: {n_total}, No matches: {n_no_match}")


if __name__ == "__main__":
    main()
