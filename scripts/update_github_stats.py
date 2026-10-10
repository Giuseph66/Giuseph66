"""Fetch Giuseph66's public GitHub numbers and generate the stats/languages card SVGs.

Uses only Python's standard library and a handful of REST calls per run. GITHUB_TOKEN
is used when set (GitHub Actions provides it) and is optional otherwise. Languages are
counted by each owned repository's primary language rather than by bytes, so vendored
libraries in a single repository cannot dominate the chart. A failed fetch leaves the
committed artwork untouched.
"""

import argparse
from collections import Counter
from html import escape
import json
import os
from urllib.request import Request, urlopen

from update_profile_art import ROOT, USERNAME, frame

DATA = ROOT / "data/github-stats.json"
TOP_LANGUAGES = 8
# GitHub linguist colours for the languages likely to appear; others fall back to grey.
COLORS = {
    "TypeScript": "#3178C6", "JavaScript": "#F1E05A", "Python": "#3572A5", "Dart": "#00B4AB",
    "HTML": "#E34C26", "CSS": "#663399", "GDScript": "#355570", "C++": "#F34B7D", "C": "#555555",
    "Java": "#B07219", "Kotlin": "#A97BFF", "Shell": "#89E051", "Go": "#00ADD8", "Rust": "#DEA584",
    "PHP": "#4F5D95", "Vue": "#41B883", "Svelte": "#FF3E00", "C#": "#178600", "Swift": "#F05138",
    "Lua": "#000080", "Ruby": "#701516", "Jupyter Notebook": "#DA5B0B",
}
OTHER = "#8B949E"


def api(path):
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "GitHub-profile-art",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if os.environ.get("GITHUB_TOKEN"):
        headers["Authorization"] = f"Bearer {os.environ['GITHUB_TOKEN']}"
    with urlopen(Request(f"https://api.github.com/{path}", headers=headers), timeout=30) as response:
        return json.load(response)


def fetch():
    user = api(f"users/{USERNAME}")
    repos, page = [], 1
    while True:
        batch = api(f"users/{USERNAME}/repos?type=owner&per_page=100&page={page}")
        repos += batch
        if len(batch) < 100:
            break
        page += 1
    owned = [repo for repo in repos if not repo["fork"]]
    if not owned:
        raise ValueError("No public repositories returned")
    languages = Counter(repo["language"] for repo in owned if repo["language"])
    return {
        "commits": api(f"search/commits?q=author:{USERNAME}&per_page=1")["total_count"],
        "pull_requests": api(f"search/issues?q=author:{USERNAME}+type:pr&per_page=1")["total_count"],
        "repositories": len(owned),
        "stars": sum(repo["stargazers_count"] for repo in owned),
        "followers": user["followers"],
        "languages": dict(languages.most_common()),
    }


def top_languages(languages):
    ranked = list(languages.items())
    if len(ranked) > TOP_LANGUAGES:
        ranked = ranked[:TOP_LANGUAGES - 1] + [("Other", sum(count for _, count in ranked[TOP_LANGUAGES - 1:]))]
    total = sum(count for _, count in ranked)
    return [(name, count / total, COLORS.get(name, OTHER)) for name, count in ranked]


def language_block(langs, x, y, width, legend_columns, row_gap, column_gap):
    parts = [
        f'<g class="line" style="animation-delay:.2s">',
        f'<text x="{x}" y="{y}" fill="#D2D8E3" font-size="13">top languages</text>',
        f'<text x="{x + width}" y="{y}" text-anchor="end" fill="#9BA6B8" font-size="11">by repository</text>',
        "</g>",
        f'<clipPath id="bar"><rect x="{x}" y="{y + 16}" width="{width}" height="10" rx="5" /></clipPath>',
        f'<rect x="{x}" y="{y + 16}" width="{width}" height="10" rx="5" fill="#30363D" />',
        f'<g clip-path="url(#bar)"><g class="grow" style="animation-delay:.3s">',
    ]
    offset = 0.0
    for index, (name, share, color) in enumerate(langs):
        # A 2px gap keeps neighbouring segments with similar colours apart.
        gap = 0 if index == len(langs) - 1 else 2
        parts.append(f'<rect x="{x + offset:.2f}" y="{y + 16}" width="{max(0, share * width - gap):.2f}" height="10" fill="{color}" />')
        offset += share * width
    parts.append("</g></g>")
    rows = -(-len(langs) // legend_columns)
    for index, (name, share, color) in enumerate(langs):
        column, row = divmod(index, rows)
        left, base = x + column * column_gap, y + 56 + row * row_gap
        parts.append(f'<g class="line" style="animation-delay:{.45 + index * .05:.2f}s">')
        parts.append(f'<circle cx="{left + 5}" cy="{base - 4}" r="5" fill="{color}" />')
        parts.append(f'<text x="{left + 18}" y="{base}" fill="#D2D8E3" font-size="12">{escape(name)}</text>')
        parts.append(f'<text x="{left + column_gap - 24}" y="{base}" text-anchor="end" fill="#9BA6B8" font-size="12">{share:.0%}</text>')
        parts.append("</g>")
    return parts


def render(data, mobile=False, light=False):
    rows = [
        ("commits", f"{data['commits']:,}"),
        ("pull requests", f"{data['pull_requests']:,}"),
        ("repositories", f"{data['repositories']:,}"),
        ("stars earned", f"{data['stars']:,}"),
        ("followers", f"{data['followers']:,}"),
        ("languages", f"{len(data['languages']):,}"),
    ]
    langs = top_languages(data["languages"])
    width, height = (420, 424) if mobile else (860, 252)
    parts = []
    for index, (label, value) in enumerate(rows):
        row_y = (80 if mobile else 84) + index * (26 if mobile else 29)
        parts.append(f'<g class="line" style="animation-delay:{.1 + index * .06:.2f}s">')
        parts.append(f'<text x="27" y="{row_y}" fill="#A8A4FF" font-size="13">{label}</text>')
        parts.append(f'<text x="{180 if mobile else 160}" y="{row_y}" fill="#F0F3F8" font-size="13" font-weight="bold">{value}</text>')
        parts.append("</g>")
    if mobile:
        parts.append(f'<path d="M1 232H{width - 1}" stroke="#30363D" />')
        parts += language_block(langs, 27, 262, width - 54, 2, 26, (width - 54) / 2 + 12)
    else:
        parts.append('<path d="M300 66V230" stroke="#30363D" />')
        parts += language_block(langs, 330, 84, 503, 2, 28, 262)
    summary = (
        f"{data['commits']:,} commits, {data['pull_requests']} pull requests, {data['repositories']} repositories, "
        f"{data['stars']} stars, {data['followers']} followers. Top languages by repository: "
        + ", ".join(f"{name} {share:.0%}" for name, share, _ in langs) + "."
    )
    return frame(width, height, "gh stats --languages", f"{USERNAME}'s GitHub stats", summary, parts, light)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cached", action="store_true", help=f"Re-render from {DATA.relative_to(ROOT)} without calling the API")
    args = parser.parse_args()
    data = json.loads(DATA.read_text(encoding="utf-8")) if args.cached else fetch()
    # Render everything before replacing any committed output.
    outputs = {}
    for mobile in (False, True):
        for light in (False, True):
            name = "github-stats" + ("-mobile" if mobile else "") + ("-light" if light else "") + ".svg"
            outputs[name] = render(data, mobile, light)
    DATA.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    for name, svg in outputs.items():
        (ROOT / "assets" / name).write_text(svg, encoding="utf-8")
    print(f"Updated GitHub stats: {data['commits']} commits, {data['repositories']} repositories")


if __name__ == "__main__":
    main()
