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

ROOT = Path(__file__).resolve().parents[1]
FONT = "'DejaVu Sans Mono', 'Liberation Mono', Consolas, monospace"
GRID_COLS, GRID_ROWS = 80, 60
CELL = 1.27  # row pitch / column pitch
RAMP = " .':;!*+?x%&#@"  # DejaVu Sans Mono glyphs, ordered by measured ink coverage
PORTRAITS = {False: ROOT / "data/portrait.txt", True: ROOT / "data/portrait-light.txt"}
ROWS = [
    ("Role", "Full Stack / Mobile Developer"),
    ("Study", "Computer Engineering student"),
    ("Based", "Sinop, MT, Brazil"),
    ("Work", "Founder @ Neurelix"),
    ("Mobile", "React Native / Expo / Dart"),
    ("Backend", "Node.js / Python / Firebase"),
    ("Hardware", "Arduino / ESP32 / C++"),
    ("Focus", "AI / IoT / automation"),
]


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


def info(x, y, mobile=False):
    parts = [
        f'<text x="{x}" y="{y}" fill="#F0F3F8" font-size="{28 if mobile else 27}" '
        f'font-weight="bold">Giuseph Giangareli</text>',
        f'<text x="{x}" y="{y + 25}" fill="#6C63FF" font-size="13">'
        '──────────────────────────</text>',
    ]
    for index, (label, value) in enumerate(ROWS):
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


def render(lines, mobile=False, light=False):
    width, height = (420, 820) if mobile else (860, 450)
    portrait_width = 278 if mobile else 310
    portrait_x = 71 if mobile else 27
    portrait_y = 72 if mobile else 81
    info_x, info_y = (27, 380) if mobile else (383, 91)
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">
<title id="title">Giuseph Giangareli — software, mobile, AI and hardware</title>
<desc id="desc">ASCII portrait from Giuseph's GitHub avatar. Full Stack and Mobile Developer, Computer Engineering student, founder of Neurelix, based in Sinop, Brazil.</desc>
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
{info(info_x, info_y, mobile)}
<text x="27" y="{height - 23}" fill="#9BA6B8" font-size="11">From applications to connected devices.</text>
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
    (ROOT / "assets").mkdir(exist_ok=True)
    for mobile in (False, True):
        for light in (False, True):
            name = "profile-terminal" + ("-mobile" if mobile else "") + ("-light" if light else "") + ".svg"
            (ROOT / "assets" / name).write_text(render(portraits[light], mobile, light), encoding="utf-8")


if __name__ == "__main__":
    main()
