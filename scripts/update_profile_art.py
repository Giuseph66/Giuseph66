"""Fetch Giuseph66's public contribution calendar and generate animated SVGs.

Uses only Python's standard library. No personal access token or third-party
stats service is needed. A failed fetch leaves the committed artwork untouched.
"""

import argparse
from datetime import date, timedelta
from html import escape
from html.parser import HTMLParser
import json
from pathlib import Path
import re
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
USERNAME = "Giuseph66"
PALETTE = ("#1C2230", "#29254B", "#443A8A", "#6C63FF", "#A8A4FF")


class ContributionsParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.cells = {}
        self.tips = {}
        self.tip_id = None
        self.tip_text = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if "data-date" in attrs and "data-level" in attrs:
            self.cells[attrs["id"]] = {
                "date": attrs["data-date"],
                "level": int(attrs["data-level"]),
            }
        if tag == "tool-tip":
            self.tip_id = attrs.get("for")
            self.tip_text = []

    def handle_data(self, text):
        if self.tip_id:
            self.tip_text.append(text)

    def handle_endtag(self, tag):
        if tag == "tool-tip" and self.tip_id:
            self.tips[self.tip_id] = "".join(self.tip_text).strip()
            self.tip_id = None

    def days(self):
        result = []
        for cell_id, cell in self.cells.items():
            match = re.match(r"^(No|[\d,]+) contributions?\b", self.tips.get(cell_id, ""))
            if not match:
                raise ValueError(f"Missing contribution count for {cell['date']}")
            count = 0 if match[1] == "No" else int(match[1].replace(",", ""))
            day = date.fromisoformat(cell["date"])
            if not 0 <= cell["level"] <= 4 or count < 0:
                raise ValueError(f"Invalid contribution data for {day}")
            result.append({**cell, "count": count})
        result.sort(key=lambda item: item["date"])
        if not 365 <= len(result) <= 371:
            raise ValueError(f"Unexpected calendar length: {len(result)}")
        dates = [date.fromisoformat(item["date"]) for item in result]
        if len(set(dates)) != len(dates) or (dates[-1] - dates[0]).days != len(dates) - 1:
            raise ValueError("Contribution dates must be unique and consecutive")
        return result


def fetch_days(html_path=None):
    if html_path:
        html = html_path.read_text(encoding="utf-8")
    else:
        request = Request(
            f"https://github.com/users/{USERNAME}/contributions",
            headers={"User-Agent": "GitHub-profile-art", "Accept-Language": "en-US"},
        )
        with urlopen(request, timeout=30) as response:
            html = response.read().decode("utf-8")
    parser = ContributionsParser()
    parser.feed(html)
    return parser.days()


def render(days, mobile=False, light=False):
    width, height = (420, 178) if mobile else (860, 226)
    pitch, cell_size = (7, 5) if mobile else (15, 11)
    origin_x, origin_y = (24, 66) if mobile else (31, 75)
    first = date.fromisoformat(days[0]["date"])
    first_sunday = first - timedelta(days=(first.weekday() + 1) % 7)
    parts = []
    previous_month = None
    for item in days:
        day = date.fromisoformat(item["date"])
        column = (day - first_sunday).days // 7
        row = (day.weekday() + 1) % 7
        x, y = origin_x + column * pitch, origin_y + row * pitch
        month = (day.year, day.month)
        if month != previous_month:
            parts.append(f'<text x="{x}" y="{origin_y - 10}" class="muted" font-size="10">{day:%b}</text>')
            previous_month = month
        parts.append(
            f'<rect class="day" x="{x}" y="{y}" width="{cell_size}" height="{cell_size}" '
            f'rx="{1 if mobile else 2}" fill="{PALETTE[item["level"]]}" '
            f'style="animation-delay:{(column + row) * .012:.3f}s">'
            f'<title>{day.isoformat()}: {item["count"]} contributions</title></rect>'
        )
    total = sum(item["count"] for item in days)
    footer_y = 138 if mobile else 199
    legend_x = 24 if mobile else 686
    legend_y = 153 if mobile else 188
    for index, color in enumerate(PALETTE):
        parts.append(f'<rect x="{legend_x + 30 + index * 14}" y="{legend_y}" width="10" height="10" rx="2" fill="{color}" />')
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">
<title id="title">{USERNAME}'s contribution calendar</title>
<desc id="desc">{total} contributions from {days[0]['date']} to {days[-1]['date']}, fetched from GitHub's public calendar.</desc>
<style>
text {{ font-family: 'DejaVu Sans Mono', 'Liberation Mono', Consolas, monospace; }}
.muted {{ fill: #9BA6B8; }}
.day {{ animation: reveal .35s both; }}
@keyframes reveal {{ from {{ opacity: 0; transform: translateY(-3px); }} to {{ opacity: 1; transform: translateY(0); }} }}
@media (prefers-reduced-motion: reduce) {{ .day {{ animation: none; }} }}
</style>
<rect x=".5" y=".5" width="{width - 1}" height="{height - 1}" rx="14" fill="#0D1117" stroke="#30363D" />
<text x="{origin_x}" y="30" fill="#D2D8E3" font-size="{13 if mobile else 15}">giuseph66@github ~ $ contributions</text>
{''.join(parts)}
<text x="{origin_x}" y="{footer_y}" fill="#D2D8E3" font-size="{12 if mobile else 13}">{total} contributions · {escape(days[0]['date'])} — {escape(days[-1]['date'])}</text>
<text x="{legend_x}" y="{legend_y + 9}" class="muted" font-size="9">Less</text>
<text x="{legend_x + 105}" y="{legend_y + 9}" class="muted" font-size="9">More</text>
</svg>
'''
    if light:
        for dark, bright in {
            "#0D1117": "#FFFFFF", "#30363D": "#D0D7DE",
            "#D2D8E3": "#24292F", "#9BA6B8": "#57606A",
            "#1C2230": "#EBEDF0", "#29254B": "#E4E1FF",
            "#443A8A": "#BEB8FF", "#A8A4FF": "#4434AC",
        }.items():
            svg = svg.replace(dark, bright)
    return svg


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--html", type=Path, help="Use a saved public calendar instead of fetching")
    args = parser.parse_args()
    days = fetch_days(args.html)
    # Validate and render everything before replacing any committed output.
    outputs = {}
    for mobile in (False, True):
        for light in (False, True):
            name = "contrib-heatmap" + ("-mobile" if mobile else "") + ("-light" if light else "") + ".svg"
            outputs[name] = render(days, mobile, light)
    (ROOT / "assets").mkdir(exist_ok=True)
    (ROOT / "data").mkdir(exist_ok=True)
    (ROOT / "data/contributions.json").write_text(
        json.dumps({"username": USERNAME, "days": days}, indent=2) + "\n", encoding="utf-8"
    )
    for name, svg in outputs.items():
        (ROOT / "assets" / name).write_text(svg, encoding="utf-8")
    print(f"Updated {len(days)} days; {sum(day['count'] for day in days)} contributions")


if __name__ == "__main__":
    main()
