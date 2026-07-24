# make_charts.py
#
# Draws the two charts used in the article as plain SVG files. No
# charting library - an SVG is just a text file, so the code below
# builds it up line by line: a rectangle for the background, lines and
# circles for the data, text for the labels.
#
# Run this after process_data.py: python make_charts.py

import pandas as pd

BLUE = "#2a78d6"
ORANGE = "#eb6834"
GRAY = "#c3c2b7"
FONT = "font-family='Arial, sans-serif'"


def make_price_vs_cost_chart():
    prices = pd.read_csv("data/processed_house_prices.csv")
    prices = prices[prices["country"] == "PT"]
    cost = pd.read_csv("data/processed_construction_cost.csv")

    years = list(prices["year"])
    price_values = list(prices["index"])
    cost_values = list(cost["index"])

    width, height = 780, 420
    left, top = 60, 70
    plot_width, plot_height = 540, 260
    y_min, y_max = 90, 180

    def x_pos(year):
        share = (year - years[0]) / (years[-1] - years[0])
        return left + share * plot_width

    def y_pos(value):
        share = (y_max - value) / (y_max - y_min)
        return top + share * plot_height

    svg = []
    svg.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">')
    svg.append(f'<rect width="{width}" height="{height}" fill="white"/>')
    svg.append(f'<text x="{left}" y="30" font-size="18" font-weight="bold" {FONT}>House prices vs. construction costs, Portugal</text>')
    svg.append(f'<text x="{left}" y="50" font-size="13" fill="#666" {FONT}>Index, 2020 = 100</text>')

    # grid lines and labels on the left
    for tick in [90, 105, 120, 135, 150, 165, 180]:
        y = y_pos(tick)
        svg.append(f'<line x1="{left}" y1="{y}" x2="{left + plot_width}" y2="{y}" stroke="#e0e0e0"/>')
        svg.append(f'<text x="{left - 10}" y="{y + 4}" font-size="12" text-anchor="end" {FONT}>{tick}</text>')

    # year labels along the bottom
    for year in years:
        svg.append(f'<text x="{x_pos(year)}" y="{top + plot_height + 20}" font-size="12" text-anchor="middle" {FONT}>{year}</text>')

    # shaded area between the two lines
    top_points = [(x_pos(y), y_pos(v)) for y, v in zip(years, price_values)]
    bottom_points = [(x_pos(y), y_pos(v)) for y, v in zip(years, cost_values)]
    area_points = top_points + list(reversed(bottom_points))
    area_str = " ".join(f"{x},{y}" for x, y in area_points)
    svg.append(f'<polygon points="{area_str}" fill="{BLUE}" opacity="0.1"/>')

    # the two lines
    price_line = " ".join(f"{x_pos(y)},{y_pos(v)}" for y, v in zip(years, price_values))
    cost_line = " ".join(f"{x_pos(y)},{y_pos(v)}" for y, v in zip(years, cost_values))
    svg.append(f'<polyline points="{cost_line}" fill="none" stroke="{ORANGE}" stroke-width="3"/>')
    svg.append(f'<polyline points="{price_line}" fill="none" stroke="{BLUE}" stroke-width="3"/>')

    # a dot on every data point
    for year, value in zip(years, price_values):
        svg.append(f'<circle cx="{x_pos(year)}" cy="{y_pos(value)}" r="4" fill="{BLUE}"/>')
    for year, value in zip(years, cost_values):
        svg.append(f'<circle cx="{x_pos(year)}" cy="{y_pos(value)}" r="4" fill="{ORANGE}"/>')

    # labels at the end of each line
    last_year = years[-1]
    svg.append(f'<text x="{x_pos(last_year) + 8}" y="{y_pos(price_values[-1]) - 4}" font-size="13" font-weight="bold" fill="{BLUE}" {FONT}>House price +71%</text>')
    svg.append(f'<text x="{x_pos(last_year) + 8}" y="{y_pos(cost_values[-1]) + 16}" font-size="13" font-weight="bold" fill="{ORANGE}" {FONT}>Construction cost +33%</text>')

    svg.append(f'<text x="{left}" y="{height - 15}" font-size="11" fill="#888" {FONT}>Source: Eurostat and INE.</text>')
    svg.append('</svg>')

    with open("../assets/chart-price-vs-cost.svg", "w") as f:
        f.write("\n".join(svg))
    print("wrote assets/chart-price-vs-cost.svg")


def make_country_growth_chart():
    growth = pd.read_csv("data/processed_growth_by_country.csv")
    growth = growth.sort_values("growth_pct")  # smallest first, so Portugal ends up on top

    width = 700
    row_height = 42
    left, top = 140, 60
    plot_width = 480
    max_growth = 80  # chart goes from 0% to 80%
    height = top + row_height * len(growth) + 40

    svg = []
    svg.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">')
    svg.append(f'<rect width="{width}" height="{height}" fill="white"/>')
    svg.append(f'<text x="{left}" y="30" font-size="18" font-weight="bold" {FONT}>House price growth by country, 2020-2025</text>')

    row_number = 0
    for _, country in growth.iterrows():
        y = top + row_number * row_height
        bar_width = country["growth_pct"] / max_growth * plot_width
        color = BLUE if country["country"] == "PT" else GRAY
        weight = "bold" if country["country"] == "PT" else "normal"

        svg.append(f'<text x="{left - 10}" y="{y + 22}" font-size="13" text-anchor="end" font-weight="{weight}" {FONT}>{country["country_name"]}</text>')
        svg.append(f'<rect x="{left}" y="{y + 6}" width="{bar_width}" height="22" fill="{color}"/>')
        svg.append(f'<text x="{left + bar_width + 8}" y="{y + 22}" font-size="13" font-weight="{weight}" {FONT}>+{country["growth_pct"]:.0f}%</text>')
        row_number += 1

    svg.append(f'<text x="{left}" y="{height - 15}" font-size="11" fill="#888" {FONT}>Source: Eurostat.</text>')
    svg.append('</svg>')

    with open("../assets/chart-country-growth.svg", "w") as f:
        f.write("\n".join(svg))
    print("wrote assets/chart-country-growth.svg")


if __name__ == "__main__":
    make_price_vs_cost_chart()
    make_country_growth_chart()
