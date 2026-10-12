"""Render data/more-repos.json as a `tree`-style terminal card with one link per repository.

GitHub README images cannot hold several links, so the card is sliced: a header, one
row per folder and repository, and a footer. Each slice is its own linked image, and
the slices stack seamlessly (align="top", rows taller than the 24px line box) so the
README still shows a single card. Static: uses only Python's standard library.
    python scripts/generate_repo_index.py
"""

from html import escape
import json

from update_profile_art import ROOT, USERNAME, replace_readme_block, svg_document

DATA = ROOT / "data/more-repos.json"
OUT = ROOT / "assets/more-repos"
NAME_COLUMN = 24  # characters reserved for the repository name
# Desktop and mobile geometry; rows stay above GitHub's 24px line height once scaled down.
LAYOUT = {
    False: {"width": 860, "row": 28, "font": 12, "char": 7.22},
    True: {"width": 420, "row": 30, "font": 11, "char": 6.62},
}
HEADER, FOOTER = 84, 56


def folder(title):
    """Folder name for a group title, e.g. "Apps & Web" -> "apps-and-web/"."""
    return title.lower().replace(" & ", "-and-").replace(", ", "-").replace(" ", "-") + "/"


def rows(groups):
    """Yield (slug, prefix, kind, entry) for every folder and repository line of the tree."""
    names = list(groups)
    for index, group in enumerate(names):
        last_group = index == len(names) - 1
        yield f"dir-{folder(group)[:-1]}", ("└── " if last_group else "├── "), "dir", folder(group)
        entries = groups[group]
        for position, entry in enumerate(entries):
            branch = "    " if last_group else "│   "
            yield f"repo-{entry[0]}", branch + ("└── " if position == len(entries) - 1 else "├── "), "repo", entry


def line(prefix, kind, entry, y, mobile):
    layout = LAYOUT[mobile]
    font, char = layout["font"], layout["char"]
    parts = [f'<text x="27" y="{y}" fill="#434B5A" font-size="{font}" xml:space="preserve">{prefix}</text>']
    x = 27 + len(prefix) * char
    if kind == "dir":
        parts.append(f'<text x="{x:.1f}" y="{y}" fill="#F0F3F8" font-size="{font}" font-weight="bold">{escape(entry)}</text>')
        return parts
    name, description, stack = entry
    parts.append(f'<text x="{x:.1f}" y="{y}" fill="#A8A4FF" font-size="{font}">{escape(name)}</text>')
    column = 27 + (8 + NAME_COLUMN) * char
    if mobile:
        parts.append(f'<text x="{column:.1f}" y="{y}" fill="#9BA6B8" font-size="{font}">{escape(stack)}</text>')
    else:
        parts.append(
            f'<text x="{column:.1f}" y="{y}" font-size="{font}"><tspan fill="#D2D8E3">{escape(description)}</tspan>'
            f'<tspan fill="#9BA6B8"> · {escape(stack)}</tspan></text>'
        )
    return parts


def sides(width, height):
    return (f'<rect width="{width}" height="{height}" fill="#0D1117" />'
            f'<path d="M.5 0V{height}M{width - .5} 0V{height}" stroke="#30363D" />')


def slices(groups, mobile=False, light=False):
    """Return {slug: svg} for the header, every tree line and the footer."""
    layout = LAYOUT[mobile]
    width, row, font = layout["width"], layout["row"], layout["font"]
    baseline = round(row / 2 + font * .36, 1)
    out = {}
    header = (
        f'<path d="M.5 {HEADER}V14.5A14 14 0 0 1 14.5 .5H{width - 14.5}A14 14 0 0 1 {width - .5} 14.5V{HEADER}" '
        'fill="#0D1117" stroke="#30363D" />'
        f'<path d="M1 43H{width - 1}" stroke="#30363D" />'
        '<circle cx="23" cy="23" r="4" fill="#6C63FF" /><circle cx="39" cy="23" r="4" fill="#434B5A" />'
        '<circle cx="55" cy="23" r="4" fill="#434B5A" />'
        f'<text x="78" y="28" fill="#9BA6B8" font-size="12">{USERNAME.lower()}@github ~ $ tree ~/more-repos</text>'
        f'<g class="line"><text x="27" y="{HEADER - 10}" fill="#F0F3F8" font-size="{font}" font-weight="bold">~/more-repos</text></g>'
    )
    out["header"] = svg_document(width, HEADER, "More repositories", "tree ~/more-repos", header, light)
    for index, (slug, prefix, kind, entry) in enumerate(rows(groups)):
        body = sides(width, row) + f'<g class="line" style="animation-delay:{.05 + index * .025:.3f}s">'
        body += "".join(line(prefix, kind, entry, baseline, mobile)) + "</g>"
        title, desc = (entry, entry) if kind == "dir" else (entry[0], f"{entry[1]} ({entry[2]})")
        out[slug] = svg_document(width, row, title, desc, body, light)
    total = sum(len(entries) for entries in groups.values())
    footer = (
        f'<path d="M.5 0V{FOOTER - 14.5}A14 14 0 0 0 14.5 {FOOTER - .5}H{width - 14.5}A14 14 0 0 0 {width - .5} {FOOTER - 14.5}V0" '
        'fill="#0D1117" stroke="#30363D" />'
        f'<g class="line" style="animation-delay:1.1s"><text x="27" y="30" fill="#9BA6B8" font-size="{font}">'
        f"{len(groups)} directories, {total} repositories</text></g>"
    )
    out["footer"] = svg_document(width, FOOTER, "More repositories", f"{len(groups)} directories, {total} repositories", footer, light)
    return out


def readme_rows(groups):
    """One line per slice: a dark and a light linked <picture>, both top-aligned."""
    targets = [("header", f"https://github.com/{USERNAME}?tab=repositories", "More repositories")]
    for slug, _, kind, entry in rows(groups):
        if kind == "dir":
            targets.append((slug, f"https://github.com/{USERNAME}?tab=repositories", entry))
        else:
            targets.append((slug, f"https://github.com/{USERNAME}/{entry[0]}", f"{entry[0]} — {entry[1]} ({entry[2]})"))
    targets.append(("footer", f"https://github.com/{USERNAME}?tab=repositories", "All repositories"))
    lines = []
    for slug, url, alt in targets:
        alt = escape(alt, quote=True)
        pictures = "".join(
            f'<a href="{url}#gh-{mode}-mode-only"><picture>'
            f'<source media="(max-width: 600px)" srcset="./assets/more-repos/{slug}-mobile{suffix}.svg" />'
            f'<img src="./assets/more-repos/{slug}{suffix}.svg" width="860" align="top" alt="{alt}" /></picture></a>'
            for mode, suffix in (("dark", ""), ("light", "-light"))
        )
        lines.append(pictures + ("" if slug == "footer" else "<br />"))
    return '<p align="center">\n' + "\n".join(lines) + "\n</p>"


def main():
    groups = json.loads(DATA.read_text(encoding="utf-8"))
    outputs = {}
    for mobile in (False, True):
        for light in (False, True):
            suffix = ("-mobile" if mobile else "") + ("-light" if light else "")
            for slug, svg in slices(groups, mobile, light).items():
                outputs[f"{slug}{suffix}.svg"] = svg
    OUT.mkdir(parents=True, exist_ok=True)
    for stale in OUT.glob("*.svg"):
        if stale.name not in outputs:
            stale.unlink()
    for name, svg in outputs.items():
        (OUT / name).write_text(svg, encoding="utf-8")
    replace_readme_block("more-repos", readme_rows(groups))
    print(f"Rendered {sum(len(entries) for entries in groups.values())} repositories in {len(outputs)} slices")


if __name__ == "__main__":
    main()
