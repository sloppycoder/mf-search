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

    with open("tmp/cik_map.csv", "w") as f_good:
        for name in read_fund_names():
            n_total += 1
            cik = search_fund_name_with_variations(name, use_llm=True)
            if cik:
                f_good.write(f"{name},{cik}\n")
            else:
                f_good.write(f"{name},\n")
                n_no_match += 1
            f_good.flush()

            if n_total % 100 == 0:
                print(f"## Total: {n_total:5d}, No matches: {n_no_match:4d}")

    print(f"## Total: {n_total:5d}, No matches: {n_no_match:4d}")


if __name__ == "__main__":
    main()
