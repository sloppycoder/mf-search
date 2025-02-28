from dotenv import load_dotenv

from sec_search import search_fund_name_with_variations

load_dotenv()


def read_fund_names(filename):
    try:
        with open(filename, "r") as f:
            return [name.split(",")[0].strip() for name in f.readlines()]
    except FileNotFoundError:
        return []


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
    output_file = "tmp/cik_map.csv"

    # read number of records in the output file
    offset = len(read_fund_names(output_file))

    with open(output_file, "a+") as f_good:
        for name in read_fund_names("tmp/fundnames.csv")[offset:]:
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
