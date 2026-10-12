"""Generate the terminal portrait and info card; animate once on image load.

Normal regeneration uses only Python's standard library:
    python scripts/generate_terminal.py

To replace the portrait, supply a prepared image: subject on a transparent background
(or, without alpha, on a white one). This optional conversion uses Pillow; the daily
contribution workflow does not need it. Dark and light cards get separate renders so
the face is never shown as a negative.
The committed portrait comes from https://avatars.githubusercontent.com/u/144301215.
    python scripts/prep_photo.py avatar.jpg /tmp/portrait.png   # background removal, contrast
    python scripts/generate_terminal.py --avatar /tmp/portrait.png
"""

import argparse
from html import escape
from pathlib import Path
import re

from i18n import LANGS, localized
from update_profile_art import USERNAME, replace_readme_block, svg_document

ROOT = Path(__file__).resolve().parents[1]
FONT = "'DejaVu Sans Mono', 'Liberation Mono', Consolas, monospace"
GRID_COLS, GRID_ROWS = 80, 60
CELL = 1.27  # row pitch / column pitch
RAMP = " .':;!*+?x%&#@"  # DejaVu Sans Mono glyphs, ordered by measured ink coverage
PORTRAITS = {False: ROOT / "data/portrait.txt", True: ROOT / "data/portrait-light.txt"}
ROWS = {
    "en": [
        ("Role", "Full Stack / Mobile Developer"),
        ("Study", "Computer Engineering student"),
        ("Based", "Sinop, MT, Brazil"),
        ("Work", "Software Developer @ Esfera Solar"),
        ("Founder", "Neurelix"),
        ("Stack", "Node.js / Flutter / React Native"),
        ("Hardware", "Arduino / ESP32 / C++"),
        ("Focus", "AI / IoT / automation"),
    ],
    "pt": [
        ("Função", "Dev Full Stack / Mobile"),
        ("Estudo", "Engenharia de Computação"),
        ("Local", "Sinop, MT, Brasil"),
        ("Trabalho", "Dev de Software @ Esfera Solar"),
        ("Fundador", "Neurelix"),
        ("Stack", "Node.js / Flutter / React Native"),
        ("Hardware", "Arduino / ESP32 / C++"),
        ("Foco", "IA / IoT / automação"),
    ],
}
TEXT = {
    "en": {
        "title": "Giuseph Giangareli — software, mobile, AI and hardware",
        "desc": "ASCII portrait from Giuseph's GitHub avatar. Full Stack and Mobile Developer, Computer Engineering "
                "student, software developer at Esfera Solar, founder of Neurelix, based in Sinop, Brazil.",
        "footer": "From applications to connected devices.",
    },
    "pt": {
        "title": "Giuseph Giangareli — software, mobile, IA e hardware",
        "desc": "Retrato em ASCII a partir do avatar do GitHub do Giuseph. Dev Full Stack e Mobile, estudante de "
                "Engenharia de Computação, dev de software na Esfera Solar, fundador da Neurelix, em Sinop, Brasil.",
        "footer": "Dos aplicativos aos dispositivos conectados.",
    },
}


def convert_portrait(path):
    from PIL import Image, ImageOps

    with Image.open(path) as image:
        if "A" not in image.getbands():
            image = image.convert("RGB")
            image.putalpha(image.convert("L").point(lambda v: 0 if v > 245 else 255))
        image = image.convert("RGBA")
    # Pad to the grid's on-screen aspect so the face is not stretched by the cell shape.
    target = GRID_COLS / (GRID_ROWS * CELL)
    width, height = image.size
    size = (width, round(width / target)) if width / height > target else (round(height * target), height)
    pixels = ImageOps.pad(image, size, color=(0, 0, 0, 0)).resize((GRID_COLS, GRID_ROWS), Image.Resampling.LANCZOS)
    alpha = pixels.getchannel("A")
    luma = ImageOps.autocontrast(pixels.convert("L"), cutoff=1, mask=alpha.point(lambda a: 255 * (a > 128)))

    def render_text(dark):
        lines = []
        for y in range(GRID_ROWS):
            row = ""
            for x in range(GRID_COLS):
                a = alpha.getpixel((x, y)) / 255
                v = luma.getpixel((x, y)) / 255
                # Dense glyphs read bright on the dark card and dark on the light one.
                ink = (v ** 0.8 if dark else 1 - v) * a
                row += RAMP[round(ink * (len(RAMP) - 1))] if a > .15 else " "
            lines.append(row)
        return lines

    (ROOT / "data").mkdir(exist_ok=True)
    for light, file in PORTRAITS.items():
        file.write_text("\n".join(render_text(not light)) + "\n", encoding="utf-8")


def portrait(lines, x, y, width):
    pitch = width / GRID_COLS
    return "\n".join(
        f'<text class="ascii" x="{x}" y="{y + i * pitch * CELL:.2f}" '
        f'font-size="{pitch * 1.67:.2f}" textLength="{width}" '
        f'lengthAdjust="spacingAndGlyphs" xml:space="preserve" '
        f'style="animation-delay:{i * .02:.3f}s">{escape(line)}</text>'
        for i, line in enumerate(lines)
    )


def info(x, y, mobile=False, lang="en"):
    parts = [
        f'<text x="{x}" y="{y}" fill="#F0F3F8" font-size="{28 if mobile else 27}" '
        f'font-weight="bold">Giuseph Giangareli</text>',
        f'<text x="{x}" y="{y + 25}" fill="#6C63FF" font-size="13">'
        '──────────────────────────</text>',
    ]
    for index, (label, value) in enumerate(ROWS[lang]):
        row_y = y + 57 + index * (43 if mobile else 34)
        parts.append(f'<g class="line" style="animation-delay:{.3 + index * .08:.2f}s">')
        if mobile:
            parts.append(f'<text x="{x}" y="{row_y}" fill="#A8A4FF" font-size="13">{label}</text>')
            parts.append(f'<text x="{x}" y="{row_y + 18}" fill="#D2D8E3" font-size="15">{escape(value)}</text>')
        else:
            parts.append(f'<text x="{x}" y="{row_y}" fill="#A8A4FF" font-size="13">{label}</text>')
            parts.append(f'<text x="{x + 87}" y="{row_y}" fill="#D2D8E3" font-size="13">{escape(value)}</text>')
        parts.append("</g>")
    return "\n".join(parts)


def render(lines, mobile=False, light=False, lang="en"):
    width, height = (420, 820) if mobile else (860, 450)
    portrait_width = 278 if mobile else 310
    portrait_x = 71 if mobile else 27
    portrait_y = 72 if mobile else 81
    info_x, info_y = (27, 380) if mobile else (383, 91)
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">
<title id="title">{TEXT[lang]["title"]}</title>
<desc id="desc">{TEXT[lang]["desc"]}</desc>
<style>
text {{ font-family: {FONT}; }}
.ascii {{ fill: #BAC3D2; animation: type-row .45s both; }}
.line {{ animation: print-line .4s both; }}
@keyframes type-row {{ from {{ opacity: 0; clip-path: inset(0 100% 0 0); }} to {{ opacity: 1; clip-path: inset(0); }} }}
@keyframes print-line {{ from {{ opacity: 0; transform: translateY(5px); }} to {{ opacity: 1; transform: translateY(0); }} }}
@media (prefers-reduced-motion: reduce) {{ .ascii, .line {{ animation: none; }} }}
</style>
<rect x=".5" y=".5" width="{width - 1}" height="{height - 1}" rx="14" fill="#0D1117" stroke="#30363D" />
<path d="M1 43H{width - 1}" stroke="#30363D" />
<circle cx="23" cy="23" r="4" fill="#6C63FF" /><circle cx="39" cy="23" r="4" fill="#434B5A" /><circle cx="55" cy="23" r="4" fill="#434B5A" />
<text x="78" y="28" fill="#9BA6B8" font-size="12">giuseph66@github ~ $ neofetch</text>
{portrait(lines, portrait_x, portrait_y, portrait_width)}
{info(info_x, info_y, mobile, lang)}
<text x="27" y="{height - 23}" fill="#9BA6B8" font-size="11">{TEXT[lang]["footer"]}</text>
</svg>
'''
    if light:
        for dark, bright in {
            "#0D1117": "#FFFFFF", "#30363D": "#D0D7DE",
            "#F0F3F8": "#1F2328", "#D2D8E3": "#24292F",
            "#9BA6B8": "#57606A", "#BAC3D2": "#57606A",
            "#A8A4FF": "#5B52D6", "#434B5A": "#D0D7DE",
        }.items():
            svg = svg.replace(dark, bright)
    return svg


# The card is sliced so the language buttons in its title bar can be real links: one
# row of top-aligned slices (bar, English, Português, right edge) whose percentage widths
# add up to 100%, then the card body below. See generate_repo_index.py for the stacking.
BAR = 44
SPLIT = (653, 92, 99, 16)  # desktop pixels of each title-bar slice; mobile scales the same shares
TARGETS = {
    "en": f"https://github.com/{USERNAME}",
    "pt": f"https://github.com/{USERNAME}/{USERNAME}/blob/main/README.pt-BR.md",
}
LABELS = {False: {"en": "English", "pt": "Português"}, True: {"en": "EN", "pt": "PT"}}
FLAG_W, FLAG_H, FLAG_SCALE = 22, 15, .72  # flags are drawn at 22x15 and shown at about 16x11
FLAGS = {
    # Drawn as SVG instead of emoji, because Windows shows flag emoji as letters.
    "en": "".join(
        [f'<rect width="{FLAG_W}" height="{FLAG_H}" fill="#FFFFFF" />']
        + [f'<rect y="{i * FLAG_H / 7:.2f}" width="{FLAG_W}" height="{FLAG_H / 7 + .01:.2f}" fill="#B22234" />' for i in range(0, 7, 2)]
        + ['<rect width="10" height="8.6" fill="#3C3B6E" />']
        + [f'<circle cx="{x}" cy="{y}" r=".55" fill="#FFFFFF" />' for x in (2.2, 5, 7.8) for y in (2.2, 4.3, 6.4)]
    ),
    "pt": (
        f'<rect width="{FLAG_W}" height="{FLAG_H}" fill="#009C3B" />'
        '<path d="M11 1.6 20.4 7.5 11 13.4 1.6 7.5Z" fill="#FFDF00" />'
        '<circle cx="11" cy="7.5" r="3.7" fill="#002776" />'
        '<path d="M7.5 6.7Q11 5.9 14.5 8" stroke="#FFFFFF" stroke-width=".8" fill="none" />'
    ),
}
SLICES = ("bar", "lang-en", "lang-pt", "edge")


def cuts(mobile):
    width = 420 if mobile else 860
    return [part / sum(SPLIT) * width for part in SPLIT]


def language_button(code, x, active, mobile):
    """Low-key pill: the active language gets a faint fill and hairline border, the other stays muted."""
    label, pad = LABELS[mobile][code], (5 if mobile else 9)
    size = pad + FLAG_W * FLAG_SCALE + (4 if mobile else 6) + len(label) * 6.62 + pad
    y = (BAR - 24) / 2
    frame = (f'<rect x="{x + .5:.2f}" y="{y + .5}" width="{size - 1:.2f}" height="23" rx="6" fill="#161B22" stroke="#30363D" />'
             if active else "")
    color, opacity = ("#D2D8E3", 1) if active else ("#9BA6B8", .6)
    flag_x = x + pad
    return size, (
        f'{frame}<clipPath id="flag-{code}"><rect width="{FLAG_W}" height="{FLAG_H}" rx="2" /></clipPath>'
        f'<g transform="translate({flag_x:.2f} {y + (24 - FLAG_H * FLAG_SCALE) / 2:.2f}) scale({FLAG_SCALE})" opacity="{opacity}">'
        f'<g clip-path="url(#flag-{code})">{FLAGS[code]}</g></g>'
        f'<text x="{flag_x + FLAG_W * FLAG_SCALE + (4 if mobile else 6):.2f}" y="{y + 16}" fill="{color}" font-size="11">{escape(label)}</text>'
    )


def title_bar(mobile, lang):
    width = 420 if mobile else 860
    parts = [
        f'<path d="M.5 {BAR}V14.5A14 14 0 0 1 14.5 .5H{width - 14.5}A14 14 0 0 1 {width - .5} 14.5V{BAR}" fill="#0D1117" stroke="#30363D" />',
        f'<path d="M0 {BAR - .5}H{width}" stroke="#30363D" />',
        '<circle cx="23" cy="23" r="4" fill="#6C63FF" /><circle cx="39" cy="23" r="4" fill="#434B5A" /><circle cx="55" cy="23" r="4" fill="#434B5A" />',
        f'<text x="78" y="28" fill="#9BA6B8" font-size="12">{USERNAME.lower()}@github ~ $ neofetch</text>',
    ]
    x = cuts(mobile)[0]
    for code, slice_width in zip(("en", "pt"), cuts(mobile)[1:3]):
        size, _ = language_button(code, 0, False, mobile)
        gap = min(6 if code == "en" else 0, slice_width - size)  # right-align inside its own slice
        parts.append(language_button(code, x + slice_width - size - gap, code == lang, mobile)[1])
        x += slice_width
    return "\n".join(parts)


def crop(svg, x, y, width, height):
    """Show only a window of an SVG by rewriting the size and viewBox of its root element."""
    head, rest = svg.split(">", 1)
    head = re.sub(r'width="[^"]*" height="[^"]*" viewBox="[^"]*"',
                  f'width="{width:.3f}" height="{height}" viewBox="{x:.3f} {y} {width:.3f} {height}"', head, count=1)
    return f"{head}>{rest}"


def slices(lines, mobile, light, lang):
    width, height = (420, 820) if mobile else (860, 450)
    bar = svg_document(width, BAR, "giuseph66@github ~ $ neofetch", "English / Português", title_bar(mobile, lang), light)
    out, x = {}, 0.0
    for name, slice_width in zip(SLICES, cuts(mobile)):
        out[name] = crop(bar, x, 0, slice_width, BAR)
        x += slice_width
    out["body"] = crop(render(lines, mobile, light, lang), 0, BAR, width, height - BAR)
    return out


def readme_card(lang):
    folder = "./assets/profile-terminal" + ("" if lang == "en" else f"/{lang}")
    shares = [f"{part / sum(SPLIT) * 100:.4f}%" for part in SPLIT]
    alts = {"bar": "giuseph66@github ~ $ neofetch", "lang-en": "English", "lang-pt": "Português", "edge": "", "body": TEXT[lang]["title"]}
    links = {"lang-en": TARGETS["en"], "lang-pt": TARGETS["pt"]}

    def picture(name, share):
        return "".join(
            f'<a href="{links.get(name, TARGETS["en"])}#gh-{mode}-mode-only"><picture>'
            f'<source media="(max-width: 600px)" srcset="{folder}/{name}-mobile{suffix}.svg" />'
            f'<img src="{folder}/{name}{suffix}.svg" width="{share}" align="top" alt="{escape(alts[name], quote=True)}" /></picture></a>'
            for mode, suffix in (("dark", ""), ("light", "-light"))
        )

    row = "".join(picture(name, share) for name, share in zip(SLICES, shares))
    return f'<p align="center">\n{row}<br />\n{picture("body", "100%")}\n</p>'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--avatar", type=Path)
    args = parser.parse_args()
    if args.avatar:
        convert_portrait(args.avatar)
    portraits = {}
    for light, file in PORTRAITS.items():
        lines = file.read_text(encoding="utf-8").splitlines()
        if len(lines) != GRID_ROWS or any(len(line) != GRID_COLS for line in lines):
            raise ValueError(f"{file.name} must contain {GRID_ROWS} rows of {GRID_COLS} characters")
        portraits[light] = lines
    out = ROOT / "assets/profile-terminal"
    for lang in LANGS:
        folder = localized(out / "x.svg", lang).parent
        folder.mkdir(parents=True, exist_ok=True)
        for mobile in (False, True):
            for light in (False, True):
                suffix = ("-mobile" if mobile else "") + ("-light" if light else "")
                for name, svg in slices(portraits[light], mobile, light, lang).items():
                    (folder / f"{name}{suffix}.svg").write_text(svg, encoding="utf-8")
        replace_readme_block("neofetch", readme_card(lang), lang)


if __name__ == "__main__":
    main()
