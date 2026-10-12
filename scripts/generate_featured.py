"""Render data/featured.json as clickable project cards and update the README grid.

Each project becomes a small terminal-style card (dark and light), shown two per row
and linked to its repository. Static: uses only Python's standard library.
    python scripts/generate_featured.py
"""

from html import escape
import json
import textwrap

from update_github_stats import COLORS, OTHER
from update_profile_art import ROOT, USERNAME, replace_readme_block, svg_document

DATA = ROOT / "data/featured.json"
OUT = ROOT / "assets/featured"
WIDTH, HEIGHT, DISPLAY = 420, 172, 410
WRAP = 52  # characters per description line at 12px


def card(item, light=False):
    lines = textwrap.wrap(item["description"], WRAP)
    if len(lines) > 3:
        raise ValueError(f"{item['repo']}: description needs {len(lines)} lines; keep it to 3")
    color = COLORS.get(item["language"], OTHER)
    parts = [
        f'<rect x=".5" y=".5" width="{WIDTH - 1}" height="{HEIGHT - 1}" rx="12" fill="#0D1117" stroke="#30363D" />',
        f'<path d="M1 36H{WIDTH - 1}" stroke="#30363D" />',
        '<circle cx="18" cy="18" r="3.5" fill="#6C63FF" /><circle cx="30" cy="18" r="3.5" fill="#434B5A" /><circle cx="42" cy="18" r="3.5" fill="#434B5A" />',
        f'<text x="56" y="22" fill="#9BA6B8" font-size="11">~/{escape(item["repo"])}</text>',
        f'<g class="line" style="animation-delay:.1s"><text x="20" y="64" fill="#F0F3F8" font-size="16" font-weight="bold">{escape(item["title"])}</text></g>',
    ]
    for index, line in enumerate(lines):
        parts.append(
            f'<g class="line" style="animation-delay:{.18 + index * .06:.2f}s">'
            f'<text x="20" y="{90 + index * 18}" fill="#D2D8E3" font-size="12">{escape(line)}</text></g>'
        )
    parts.append(
        '<g class="line" style="animation-delay:.4s">'
        f'<circle cx="25" cy="{HEIGHT - 21}" r="5" fill="{color}" />'
        f'<text x="36" y="{HEIGHT - 17}" fill="#D2D8E3" font-size="12">{escape(item["language"])}</text>'
        f'<text x="{WIDTH - 20}" y="{HEIGHT - 17}" text-anchor="end" fill="#9BA6B8" font-size="11">{escape(item["stack"])}</text>'
        "</g>"
    )
    return svg_document(WIDTH, HEIGHT, f"{item['title']} ({item['repo']})", item["description"], "\n".join(parts), light)


def readme_grid(groups):
    blocks = []
    for group, items in groups.items():
        links = []
        for item in items:
            alt = escape(f"{item['title']} — {item['description']}", quote=True)
            url = f"https://github.com/{USERNAME}/{item['repo']}"
            for mode, suffix in (("dark", ""), ("light", "-light")):
                links.append(
                    f'  <a href="{url}#gh-{mode}-mode-only"><img src="./assets/featured/{item["repo"]}{suffix}.svg" '
                    f'width="{DISPLAY}" alt="{alt}" /></a>'
                )
        blocks.append(f"### {group}\n\n<p align=\"center\">\n" + "\n".join(links) + "\n</p>")
    return "\n\n".join(blocks)


def main():
    groups = json.loads(DATA.read_text(encoding="utf-8"))
    # Render everything before writing so a description that does not fit fails cleanly.
    outputs = {}
    for items in groups.values():
        for item in items:
            outputs[f"{item['repo']}.svg"] = card(item)
            outputs[f"{item['repo']}-light.svg"] = card(item, light=True)
    OUT.mkdir(parents=True, exist_ok=True)
    for stale in OUT.glob("*.svg"):
        if stale.name not in outputs:
            stale.unlink()
    for name, svg in outputs.items():
        (OUT / name).write_text(svg, encoding="utf-8")
    replace_readme_block("featured", readme_grid(groups))
    print(f"Rendered {len(outputs) // 2} project cards")


if __name__ == "__main__":
    main()
