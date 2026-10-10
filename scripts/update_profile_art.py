"""Fetch Giuseph66's public contribution calendar and generate the stats card SVGs.

Uses only Python's standard library. No personal access token or third-party
stats service is needed: every year since the account was created is read from
the same public calendar fragment the profile page uses. A failed fetch leaves
the committed artwork untouched.
"""

import argparse
from collections import Counter
from datetime import date, timedelta
from html import escape
from html.parser import HTMLParser
import json
from pathlib import Path
import re
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
USERNAME = "Giuseph66"
FIRST_YEAR = 2023  # account created 2023-09-07
FONT = "'DejaVu Sans Mono', 'Liberation Mono', Consolas, monospace"
LIGHT = {
    "#0D1117": "#FFFFFF", "#30363D": "#D0D7DE",
    "#F0F3F8": "#1F2328", "#D2D8E3": "#24292F",
    "#9BA6B8": "#57606A", "#A8A4FF": "#5B52D6",
    "#434B5A": "#D0D7DE",
}


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
            self.cells[attrs["id"]] = attrs["data-date"]
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
        for cell_id, day in self.cells.items():
            match = re.match(r"^(No|[\d,]+) contributions?\b", self.tips.get(cell_id, ""))
            if not match:
                raise ValueError(f"Missing contribution count for {day}")
            count = 0 if match[1] == "No" else int(match[1].replace(",", ""))
            result.append({"date": date.fromisoformat(day).isoformat(), "count": count})
        return sorted(result, key=lambda item: item["date"])


def parse(html):
    parser = ContributionsParser()
    parser.feed(html)
    return parser.days()


def fetch_year(year):
    request = Request(
        f"https://github.com/users/{USERNAME}/contributions?from={year}-01-01&to={year}-12-31",
        headers={"User-Agent": "GitHub-profile-art", "Accept-Language": "en-US"},
    )
    with urlopen(request, timeout=30) as response:
        days = parse(response.read().decode("utf-8"))
    if not days or days[0]["date"] != f"{year}-01-01" or days[-1]["date"] != f"{year}-12-31":
        raise ValueError(f"Calendar for {year} does not cover the whole year")
    return days


def fetch_days(html_paths=None, today=None):
    today = today or date.today()
    if html_paths:
        days = [day for path in html_paths for day in parse(path.read_text(encoding="utf-8"))]
    else:
        days = [day for year in range(FIRST_YEAR, today.year + 1) for day in fetch_year(year)]
    days = sorted({day["date"]: day for day in days}.values(), key=lambda item: item["date"])
    days = [day for day in days if date.fromisoformat(day["date"]) <= today]
    dates = [date.fromisoformat(day["date"]) for day in days]
    if len(dates) < 365 or (dates[-1] - dates[0]).days != len(dates) - 1:
        raise ValueError("Contribution dates must be consecutive and cover at least a year")
    return days


def stats(days):
    runs, start = [], None
    for day in days:
        current = date.fromisoformat(day["date"])
        if day["count"]:
            start = start or current
            end = current
        elif start:
            runs.append((start, end))
            start = None
    if start:
        runs.append((start, end))
    last = date.fromisoformat(days[-1]["date"])
    # Today counts as still open: a streak ending yesterday is current.
    current = runs[-1] if runs and runs[-1][1] >= last - timedelta(days=1) else None
    longest = max(runs, key=lambda run: ((run[1] - run[0]).days, run[1]), default=None)
    best = max(days, key=lambda day: (day["count"], day["date"]))
    weekdays = Counter()
    for day in days:
        weekdays[date.fromisoformat(day["date"]).strftime("%A")] += day["count"]
    active = [day for day in days if day["count"]]
    return {
        "total": sum(day["count"] for day in days),
        "since": date.fromisoformat(active[0]["date"]) if active else None,
        "last": date.fromisoformat(active[-1]["date"]) if active else None,
        "current": current,
        "longest": longest,
        "best": (best["count"], date.fromisoformat(best["date"])),
        "year": (last.year, sum(day["count"] for day in days if day["date"].startswith(str(last.year)))),
        "weekday": weekdays.most_common(1)[0][0] if active else "—",
    }


def short(day, year=True):
    return f"{day:%b} {day.day}" + (f", {day.year}" if year else "")


def span(run):
    if not run:
        return 0, "no streak yet"
    start, end = run
    length = (end - start).days + 1
    if start == end:
        return length, short(end)
    return length, f"{short(start, start.year != end.year)} – {short(end)}"


def plural(value, unit):
    return f"{value:,} {unit}{'' if value == 1 else 's'}"


def render(data, mobile=False, light=False):
    current_len, current_span = span(data["current"])
    if not data["current"] and data["last"]:
        current_span = f"last on {short(data['last'])}"
    longest_len, longest_span = span(data["longest"])
    since = f"since {data['since']:%b %Y}" if data["since"] else "no contributions yet"
    blocks = [
        (f"{data['total']:,}", "contributions", since, "#F0F3F8"),
        (plural(current_len, "day"), "current streak", current_span, "#A8A4FF"),
        (plural(longest_len, "day"), "longest streak", longest_span, "#F0F3F8"),
    ]
    best_count, best_day = data["best"]
    facts = [
        ("best day", f"{best_count} on {short(best_day)}"),
        (f"in {data['year'][0]}", plural(data["year"][1], "contribution")),
        ("most active", data["weekday"]),
    ]
    width, height = (420, 380) if mobile else (860, 236)
    parts = []
    if mobile:
        for index, (value, label, sub, color) in enumerate(blocks):
            top = 66 + index * 74
            if index:
                parts.append(f'<path d="M27 {top - 12}H{width - 27}" stroke="#30363D" />')
            parts.append(f'<g class="line" style="animation-delay:{.1 + index * .1:.2f}s">')
            parts.append(f'<text x="27" y="{top + 34}" fill="{color}" font-size="30" font-weight="bold">{escape(value)}</text>')
            parts.append(f'<text x="215" y="{top + 18}" fill="#D2D8E3" font-size="13">{label}</text>')
            parts.append(f'<text x="215" y="{top + 38}" fill="#9BA6B8" font-size="11">{escape(sub)}</text>')
            parts.append("</g>")
        parts.append(f'<path d="M1 286H{width - 1}" stroke="#30363D" />')
        for index, (label, value) in enumerate(facts):
            row_y = 314 + index * 22
            parts.append(f'<g class="line" style="animation-delay:{.45 + index * .08:.2f}s">')
            parts.append(f'<text x="27" y="{row_y}" fill="#A8A4FF" font-size="12">{label}</text>')
            parts.append(f'<text x="140" y="{row_y}" fill="#D2D8E3" font-size="12">{escape(value)}</text>')
            parts.append("</g>")
    else:
        column = width / 3
        for index, (value, label, sub, color) in enumerate(blocks):
            center = column * index + column / 2
            if index:
                parts.append(f'<path d="M{column * index:.0f} 70V160" stroke="#30363D" />')
            parts.append(f'<g class="line" style="animation-delay:{.1 + index * .12:.2f}s">')
            parts.append(f'<text x="{center:.0f}" y="108" text-anchor="middle" fill="{color}" font-size="34" font-weight="bold">{escape(value)}</text>')
            parts.append(f'<text x="{center:.0f}" y="135" text-anchor="middle" fill="#D2D8E3" font-size="13">{label}</text>')
            parts.append(f'<text x="{center:.0f}" y="155" text-anchor="middle" fill="#9BA6B8" font-size="11">{escape(sub)}</text>')
            parts.append("</g>")
        parts.append(f'<path d="M1 184H{width - 1}" stroke="#30363D" />')
        for index, (label, value) in enumerate(facts):
            center = column * index + column / 2
            parts.append(f'<g class="line" style="animation-delay:{.5 + index * .08:.2f}s">')
            parts.append(
                f'<text x="{center:.0f}" y="215" text-anchor="middle" font-size="12">'
                f'<tspan fill="#A8A4FF">{label}</tspan><tspan fill="#D2D8E3"> {escape(value)}</tspan></text>'
            )
            parts.append("</g>")
    summary = (
        f"{data['total']:,} contributions {since}; current streak {plural(current_len, 'day')}; "
        f"longest streak {plural(longest_len, 'day')}; best day {best_count} contributions on {short(best_day)}. "
        "Generated from GitHub's public contribution calendar."
    )
    return frame(width, height, "contributions --stats", f"{USERNAME}'s contribution stats", summary, parts, light)


def frame(width, height, command, title, desc, parts, light=False):
    """Terminal-window card shared by the stats SVGs; dark colours swap via LIGHT."""
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">
<title id="title">{escape(title)}</title>
<desc id="desc">{escape(desc)}</desc>
<style>
text {{ font-family: {FONT}; }}
.line {{ animation: print-line .4s both; }}
.grow {{ animation: grow .7s cubic-bezier(.2, .7, .3, 1) both; transform-box: fill-box; transform-origin: left center; }}
@keyframes print-line {{ from {{ opacity: 0; transform: translateY(5px); }} to {{ opacity: 1; transform: translateY(0); }} }}
@keyframes grow {{ from {{ transform: scaleX(0); }} to {{ transform: scaleX(1); }} }}
@media (prefers-reduced-motion: reduce) {{ .line, .grow {{ animation: none; }} }}
</style>
<rect x=".5" y=".5" width="{width - 1}" height="{height - 1}" rx="14" fill="#0D1117" stroke="#30363D" />
<path d="M1 43H{width - 1}" stroke="#30363D" />
<circle cx="23" cy="23" r="4" fill="#6C63FF" /><circle cx="39" cy="23" r="4" fill="#434B5A" /><circle cx="55" cy="23" r="4" fill="#434B5A" />
<text x="78" y="28" fill="#9BA6B8" font-size="12">{USERNAME.lower()}@github ~ $ {escape(command)}</text>
{chr(10).join(parts)}
</svg>
'''
    if light:
        for dark, bright in LIGHT.items():
            svg = svg.replace(dark, bright)
    return svg


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--html", type=Path, nargs="+", help="Use saved yearly calendars instead of fetching")
    args = parser.parse_args()
    days = fetch_days(args.html)
    data = stats(days)
    # Validate and render everything before replacing any committed output.
    outputs = {}
    for mobile in (False, True):
        for light in (False, True):
            name = "contrib-stats" + ("-mobile" if mobile else "") + ("-light" if light else "") + ".svg"
            outputs[name] = render(data, mobile, light)
    (ROOT / "assets").mkdir(exist_ok=True)
    (ROOT / "data").mkdir(exist_ok=True)
    rows = ",\n".join(f"    {json.dumps(day)}" for day in days)
    (ROOT / "data/contributions.json").write_text(
        f'{{\n  "username": "{USERNAME}",\n  "days": [\n{rows}\n  ]\n}}\n', encoding="utf-8"
    )
    for name, svg in outputs.items():
        (ROOT / "assets" / name).write_text(svg, encoding="utf-8")
    print(f"Updated {len(days)} days; {data['total']} contributions")


if __name__ == "__main__":
    main()
