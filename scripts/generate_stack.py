"""Render data/stack.json as a terminal card of technology chips with Simple Icons logos.

Icons come from a pinned Simple Icons release and are cached in data/stack-icons.json,
so later renders work offline. Brands without an icon there (OpenAI, Hyperledger and
others were removed for trademark reasons) get a coloured dot instead.
    python scripts/generate_stack.py
"""

from html import escape
import json
import re
import unicodedata
from urllib.request import Request, urlopen

from update_profile_art import ROOT, frame

DATA = ROOT / "data/stack.json"
CACHE = ROOT / "data/stack-icons.json"
CDN = "https://cdn.jsdelivr.net/npm/simple-icons@16.34.0"
CHAR = 7.22  # DejaVu Sans Mono advance at 12px


def fetch(url):
    with urlopen(Request(url, headers={"User-Agent": "GitHub-profile-art"}), timeout=30) as response:
        return response.read().decode("utf-8")


def slugify(title):
    """Simple Icons' titleToSlug."""
    swaps = {"+": "plus", ".": "dot", "&": "and", "đ": "d", "ħ": "h", "ı": "i", "ĸ": "k",
             "ŀ": "l", "ł": "l", "ß": "ss", "ŧ": "t", "ø": "o"}
    title = "".join(swaps.get(char, char) for char in title.lower())
    return re.sub(r"[^a-z0-9]", "", unicodedata.normalize("NFD", title))


def load_icons(slugs):
    cache = json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {}
    missing = sorted(set(slugs) - set(cache))
    if missing:
        catalog = json.loads(fetch(f"{CDN}/data/simple-icons.json"))
        entries = catalog if isinstance(catalog, list) else catalog["icons"]
        colors = {entry.get("slug") or slugify(entry["title"]): entry["hex"] for entry in entries}
        for slug in missing:
            path = re.search(r'<path d="([^"]+)"', fetch(f"{CDN}/icons/{slug}.svg"))[1]
            cache[slug] = {"hex": f"#{colors[slug]}", "path": path}
        CACHE.write_text(json.dumps(dict(sorted(cache.items())), indent=2) + "\n", encoding="utf-8")
    return cache


def luminance(color):
    channels = [int(color[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    r, g, b = [c / 12.92 if c <= .03928 else ((c + .055) / 1.055) ** 2.4 for c in channels]
    return .2126 * r + .7152 * g + .0722 * b


def readable(color, light):
    """Keep brand colours, except near-black logos on the dark card and pale ones on the light card."""
    if not light and luminance(color) < .05:
        return "#F0F3F8"
    if light and luminance(color) > .4:
        return "#" + "".join(f"{round(int(color[i:i + 2], 16) * .62):02X}" for i in (1, 3, 5))
    return color


def chip(x, y, label, icon, color):
    width = 42 + len(label) * CHAR
    mark = (
        f'<path transform="translate({x + 10:.1f} {y + 7}) scale(.5833)" d="{icon}" fill="{color}" />' if icon
        else f'<circle cx="{x + 17:.1f}" cy="{y + 14}" r="4.5" fill="{color}" />'
    )
    return width, (
        f'<rect x="{x:.1f}" y="{y}" width="{width:.1f}" height="28" rx="7" fill="#161B22" stroke="#30363D" />'
        f'{mark}<text x="{x + 31:.1f}" y="{y + 18.5}" fill="#D2D8E3" font-size="12">{escape(label)}</text>'
    )


def render(groups, icons, mobile=False, light=False):
    width = 420 if mobile else 860
    start, right = (27, width - 27) if mobile else (150, width - 27)
    y, parts = 62, []
    for index, (key, items) in enumerate(groups.items()):
        parts.append(f'<g class="line" style="animation-delay:{.1 + index * .08:.2f}s">')
        if mobile:
            parts.append(f'<text x="27" y="{y + 12}" fill="#A8A4FF" font-size="13">{key}:</text>')
            y += 22
        else:
            parts.append(f'<text x="27" y="{y + 18.5}" fill="#A8A4FF" font-size="13">{key}:</text>')
        x = start
        for label, slug, *fallback in items:
            icon = icons[slug] if slug else None
            color = readable(icon["hex"] if icon else fallback[0], light)
            size = 42 + len(label) * CHAR
            if x + size > right:
                x, y = start, y + 36
            size, markup = chip(x, y, label, icon and icon["path"], color)
            parts.append(markup)
            x += size + 8
        parts.append("</g>")
        y += 36 + (6 if mobile else 10)
    labels = "; ".join(f"{key}: " + ", ".join(item[0] for item in items) for key, items in groups.items())
    return frame(width, y + 8, "cat ~/.config/stack.yml", "Tech stack", labels, parts, light)


def main():
    groups = json.loads(DATA.read_text(encoding="utf-8"))
    icons = load_icons(item[1] for items in groups.values() for item in items if item[1])
    for mobile in (False, True):
        for light in (False, True):
            name = "tech-stack" + ("-mobile" if mobile else "") + ("-light" if light else "") + ".svg"
            (ROOT / "assets" / name).write_text(render(groups, icons, mobile, light), encoding="utf-8")
    print(f"Rendered {sum(len(items) for items in groups.values())} technologies")


if __name__ == "__main__":
    main()
