# process_data.py
#
# Cleans up the raw Eurostat and INE files and puts both series on the
# same scale (2020 = 100) so they can be compared. Eurostat's index
# starts in 2015 and INE's starts in 2021, so comparing the raw numbers
# would not mean anything - they need a common starting point first.
#
# Run this first: python process_data.py

import pandas as pd

COUNTRY_NAMES = {
    "AT": "Austria",
    "BE": "Belgium",
    "DE": "Germany",
    "ES": "Spain",
    "FR": "France",
    "IT": "Italy",
    "NL": "Netherlands",
    "PT": "Portugal",
}
# Ireland is also in the raw file, but its housing market had a very
# different path after the 2008 crash (a big crash, then a recovery from
# a very low base), so it was left out of the country comparison.

YEARS = [2020, 2021, 2022, 2023, 2024, 2025]


def clean_house_prices():
    df = pd.read_csv("data/house_prices.csv")

    rows = []
    for _, country_row in df.iterrows():
        code = country_row["country"]
        if code not in COUNTRY_NAMES:
            continue
        value_2020 = country_row["2020"]
        for year in YEARS:
            index_value = country_row[str(year)]
            rows.append({
                "country": code,
                "country_name": COUNTRY_NAMES[code],
                "year": year,
                "index": index_value / value_2020 * 100,
            })

    return pd.DataFrame(rows)


def clean_construction_cost():
    df = pd.read_csv("data/construction_cost_pt.csv")

    # the INE file uses "Dezembro de 2020" style dates and commas for
    # decimals (e.g. "95,02"), so both need fixing before use
    df["year"] = df["period"].str.extract(r"(\d{4})").astype(int)
    df["value"] = df["value"].str.replace(",", ".").astype(float)
    df = df[df["year"].isin(YEARS)]

    value_2020 = df.loc[df["year"] == 2020, "value"].iloc[0]
    df["index"] = df["value"] / value_2020 * 100

    return df[["year", "index"]]


def growth_by_country(price_table):
    rows = []
    for code, name in COUNTRY_NAMES.items():
        country_data = price_table[price_table["country"] == code]
        index_2020 = country_data[country_data["year"] == 2020]["index"].iloc[0]
        index_2025 = country_data[country_data["year"] == 2025]["index"].iloc[0]

        growth_pct = index_2025 - index_2020
        cagr_pct = ((index_2025 / index_2020) ** (1 / 5) - 1) * 100

        rows.append({
            "country": code,
            "country_name": name,
            "growth_pct": growth_pct,
            "cagr_pct": cagr_pct,
        })

    result = pd.DataFrame(rows)
    return result.sort_values("growth_pct", ascending=False)


if __name__ == "__main__":
    house_prices = clean_house_prices()
    construction_cost = clean_construction_cost()
    growth = growth_by_country(house_prices)

    house_prices.to_csv("data/processed_house_prices.csv", index=False)
    construction_cost.to_csv("data/processed_construction_cost.csv", index=False)
    growth.to_csv("data/processed_growth_by_country.csv", index=False)

    print("House price growth vs. construction cost growth in Portugal, 2020-2025:")
    pt_prices = house_prices[house_prices["country"] == "PT"]
    print("House price index 2025:", round(pt_prices[pt_prices["year"] == 2025]["index"].iloc[0], 1))
    print("Construction cost index 2025:", round(construction_cost[construction_cost["year"] == 2025]["index"].iloc[0], 1))
    print()
    print(growth)
