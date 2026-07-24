# make_map.py
#
# Builds the interactive map. The country shapes come from
# data/country_borders.json - a list of (longitude, latitude) points for
# each country's outline, already extracted from a public domain map
# dataset (Natural Earth, via the world-atlas project on GitHub) so this
# script doesn't need to deal with map file formats, just plain numbers.
#
# To turn a (longitude, latitude) point into an (x, y) pixel on the page,
# this uses a simple equirectangular projection: longitude becomes x and
# latitude becomes y, with a small correction (cos of 50 degrees, roughly
# the middle latitude of Europe) so the map isn't stretched sideways.
#
# Run this after process_data.py: python make_map.py

import json
import math

import pandas as pd

MID_LATITUDE = 50
COUNTRIES_WITH_LABELS = {
    "AT": "Austria", "BE": "Belgium", "DE": "Germany", "ES": "Spain",
    "FR": "France", "IT": "Italy", "NL": "Netherlands", "PT": "Portugal",
}


def color_for_growth(growth_pct):
    # a simple 5-step color scale, light blue for small growth, dark
    # blue for large growth
    if growth_pct < 12:
        return "#9ec5f4"
    elif growth_pct < 20:
        return "#6da7ec"
    elif growth_pct < 30:
        return "#3987e5"
    elif growth_pct < 55:
        return "#256abf"
    else:
        return "#104281"


def project(lon, lat, scale, offset_x, offset_y):
    x = lon * math.cos(math.radians(MID_LATITUDE)) * scale + offset_x
    y = -lat * scale + offset_y
    return x, y


def path_from_rings(rings, scale, offset_x, offset_y):
    # a country can be made of more than one shape (mainland + islands),
    # so this builds one SVG path with one "M ... Z" section per shape
    path_parts = []
    for ring in rings:
        points = [project(lon, lat, scale, offset_x, offset_y) for lon, lat in ring]
        point_str = " L ".join(f"{x:.1f},{y:.1f}" for x, y in points)
        path_parts.append(f"M {point_str} Z")
    return " ".join(path_parts)


def center_of_rings(rings):
    # used to place the country code label roughly in the middle of the
    # biggest shape (the mainland, usually the one with the most points)
    biggest_ring = max(rings, key=len)
    lons = [p[0] for p in biggest_ring]
    lats = [p[1] for p in biggest_ring]
    return (min(lons) + max(lons)) / 2, (min(lats) + max(lats)) / 2


def build_map():
    borders = json.load(open("data/country_borders.json"))
    growth = pd.read_csv("data/processed_growth_by_country.csv").set_index("country")

    all_countries = {**borders["with_data"], **borders["no_data"]}

    # work out a scale that fits every country on a WIDTH x HEIGHT canvas
    WIDTH, HEIGHT, PADDING = 820, 760, 20
    all_points = [p for rings in all_countries.values() for ring in rings for p in ring]
    xs_unscaled = [lon * math.cos(math.radians(MID_LATITUDE)) for lon, lat in all_points]
    ys_unscaled = [-lat for lon, lat in all_points]
    scale_x = (WIDTH - 2 * PADDING) / (max(xs_unscaled) - min(xs_unscaled))
    scale_y = (HEIGHT - 2 * PADDING) / (max(ys_unscaled) - min(ys_unscaled))
    scale = min(scale_x, scale_y)
    offset_x = PADDING - min(xs_unscaled) * scale
    offset_y = PADDING - min(ys_unscaled) * scale

    # build the SVG shapes for the countries that are NOT part of the story
    # (grey, just there so the map doesn't look like floating islands)
    background_shapes = ""
    for code, rings in borders["no_data"].items():
        d = path_from_rings(rings, scale, offset_x, offset_y)
        background_shapes += f'<path d="{d}" class="country-no-data"><title>{code}: not in this analysis</title></path>\n'

    # build the SVG shapes for the 8 countries in the story, plus a label
    data_shapes = ""
    labels = ""
    for code, rings in borders["with_data"].items():
        row = growth.loc[code]
        d = path_from_rings(rings, scale, offset_x, offset_y)
        color = color_for_growth(row["growth_pct"])
        name = COUNTRIES_WITH_LABELS[code]
        tooltip = f"{name}: +{row['growth_pct']:.1f}% since 2020 (about {row['cagr_pct']:.1f}%/year)"
        data_shapes += (
            f'<path d="{d}" fill="{color}" class="country-data" '
            f'data-name="{name}" data-growth="{row["growth_pct"]:.1f}" data-cagr="{row["cagr_pct"]:.1f}">'
            f'<title>{tooltip}</title></path>\n'
        )
        cx, cy = center_of_rings(rings)
        label_x, label_y = project(cx, cy, scale, offset_x, offset_y)
        labels += f'<text x="{label_x:.1f}" y="{label_y:.1f}" class="country-label">{code}</text>\n'

    html = HTML_TEMPLATE.format(
        width=WIDTH, height=HEIGHT,
        background_shapes=background_shapes,
        data_shapes=data_shapes,
        labels=labels,
    )

    with open("../assets/map.html", "w") as f:
        f.write(html)
    print("wrote assets/map.html")


HTML_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>House price growth in Europe, 2020-2025</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
  body {{ margin: 0; font-family: Arial, sans-serif; }}
  .layout {{ display: flex; height: 100vh; }}
  .sidebar {{ width: 240px; padding: 16px; border-right: 1px solid #ddd; overflow-y: auto; }}
  .sidebar h2 {{ font-size: 13px; text-transform: uppercase; color: #888; margin: 20px 0 8px; }}
  .sidebar h2:first-child {{ margin-top: 0; }}
  .layer-option {{ display: block; margin: 6px 0; font-size: 14px; }}
  .legend-row {{ display: flex; align-items: center; gap: 8px; font-size: 13px; margin: 4px 0; }}
  .legend-swatch {{ width: 14px; height: 14px; display: inline-block; }}
  .map-area {{ flex: 1; position: relative; }}
  svg {{ width: 100%; height: 100%; }}
  .country-data {{ stroke: white; stroke-width: 1; cursor: pointer; }}
  .country-data:hover {{ opacity: 0.8; }}
  .country-no-data {{ fill: #e5e4de; stroke: #c3c2b7; stroke-width: 1; }}
  .country-label {{ font-size: 11px; font-weight: bold; text-anchor: middle; pointer-events: none; }}
  #info-box {{ font-size: 13px; line-height: 1.5; }}
  .zoom-buttons {{ position: absolute; right: 12px; bottom: 12px; }}
  .zoom-buttons button {{ width: 46px; height: 30px; font-size: 14px; display: block; margin-bottom: 4px; }}
</style>
</head>
<body>
<div class="layout">
  <div class="sidebar">
    <h2>Layers</h2>
    <label class="layer-option"><input type="checkbox" id="toggle-data" checked> Price growth</label>
    <label class="layer-option"><input type="checkbox" id="toggle-nodata" checked> Countries with no data</label>
    <label class="layer-option"><input type="checkbox" id="toggle-labels" checked> Country codes</label>

    <h2>Legend</h2>
    <div class="legend-row"><span class="legend-swatch" style="background:#9ec5f4"></span> below 12%</div>
    <div class="legend-row"><span class="legend-swatch" style="background:#6da7ec"></span> 12% to 20%</div>
    <div class="legend-row"><span class="legend-swatch" style="background:#3987e5"></span> 20% to 30%</div>
    <div class="legend-row"><span class="legend-swatch" style="background:#256abf"></span> 30% to 55%</div>
    <div class="legend-row"><span class="legend-swatch" style="background:#104281"></span> above 55%</div>

    <h2>Selected country</h2>
    <div id="info-box">Click a country to see its numbers.</div>
  </div>
  <div class="map-area">
    <svg id="map" viewBox="0 0 {width} {height}">
      <g id="no-data-layer">
{background_shapes}
      </g>
      <g id="data-layer">
{data_shapes}
      </g>
      <g id="label-layer">
{labels}
      </g>
    </svg>
    <div class="zoom-buttons">
      <button id="zoom-in">+</button>
      <button id="zoom-out">-</button>
      <button id="zoom-reset">reset</button>
    </div>
  </div>
</div>

<script>
var svg = document.getElementById("map");
var infoBox = document.getElementById("info-box");

// clicking a country updates the info box in the sidebar
var countries = document.querySelectorAll(".country-data");
for (var i = 0; i < countries.length; i++) {{
  countries[i].addEventListener("click", function () {{
    var name = this.getAttribute("data-name");
    var growth = this.getAttribute("data-growth");
    var cagr = this.getAttribute("data-cagr");
    infoBox.innerHTML =
      "<b>" + name + "</b><br>" +
      "Growth 2020-2025: +" + growth + "%<br>" +
      "Average per year: +" + cagr + "%";
  }});
}}

// layer checkboxes just show/hide their SVG group
document.getElementById("toggle-data").addEventListener("change", function (e) {{
  document.getElementById("data-layer").style.display = e.target.checked ? "" : "none";
}});
document.getElementById("toggle-nodata").addEventListener("change", function (e) {{
  document.getElementById("no-data-layer").style.display = e.target.checked ? "" : "none";
}});
document.getElementById("toggle-labels").addEventListener("change", function (e) {{
  document.getElementById("label-layer").style.display = e.target.checked ? "" : "none";
}});

// simple zoom: change the viewBox width/height, keeping the same center
var viewBox = {{ x: 0, y: 0, w: {width}, h: {height} }};

function applyZoom(factor) {{
  var newW = viewBox.w * factor;
  var newH = viewBox.h * factor;
  viewBox.x -= (newW - viewBox.w) / 2;
  viewBox.y -= (newH - viewBox.h) / 2;
  viewBox.w = newW;
  viewBox.h = newH;
  svg.setAttribute("viewBox", viewBox.x + " " + viewBox.y + " " + viewBox.w + " " + viewBox.h);
}}

document.getElementById("zoom-in").addEventListener("click", function () {{ applyZoom(0.8); }});
document.getElementById("zoom-out").addEventListener("click", function () {{ applyZoom(1.25); }});
document.getElementById("zoom-reset").addEventListener("click", function () {{
  viewBox = {{ x: 0, y: 0, w: {width}, h: {height} }};
  svg.setAttribute("viewBox", "0 0 {width} {height}");
}});

// click-and-drag panning
var dragging = false;
var lastX = 0;
var lastY = 0;

svg.addEventListener("mousedown", function (e) {{
  dragging = true;
  lastX = e.clientX;
  lastY = e.clientY;
}});
window.addEventListener("mousemove", function (e) {{
  if (!dragging) return;
  var rect = svg.getBoundingClientRect();
  var dx = (e.clientX - lastX) / rect.width * viewBox.w;
  var dy = (e.clientY - lastY) / rect.height * viewBox.h;
  viewBox.x -= dx;
  viewBox.y -= dy;
  svg.setAttribute("viewBox", viewBox.x + " " + viewBox.y + " " + viewBox.w + " " + viewBox.h);
  lastX = e.clientX;
  lastY = e.clientY;
}});
window.addEventListener("mouseup", function () {{ dragging = false; }});
</script>
</body>
</html>
"""


if __name__ == "__main__":
    build_map()
