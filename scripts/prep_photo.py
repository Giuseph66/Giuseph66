"""Prepare a profile photo for the ASCII portrait in generate_terminal.py.

Removes the background (OpenCV GrabCut), smooths skin texture, boosts local
contrast (CLAHE) and fades the bust out at the bottom, then writes a grayscale
PNG with a transparent background. Local-only: needs opencv-python and numpy,
which the daily workflow does not install.
    python scripts/prep_photo.py avatar.jpg /tmp/portrait.png
    python scripts/generate_terminal.py --avatar /tmp/portrait.png
"""

import argparse

import cv2
import numpy as np


def prepare(src, out, rect, bottom, fade):
    image = cv2.imread(str(src))
    if image is None:
        raise SystemExit(f"Cannot read {src}")
    height, width = image.shape[:2]
    # GrabCut seeds: everything outside the rectangle is background.
    x, y, w, h = (round(v * s) for v, s in zip(rect, (width, height, width, height)))
    mask = np.zeros((height, width), np.uint8)
    models = np.zeros((1, 65)), np.zeros((1, 65))
    cv2.grabCut(image, mask, (x, y, w, h), *models, 8, cv2.GC_INIT_WITH_RECT)
    subject = np.where((mask == cv2.GC_FGD) | (mask == cv2.GC_PR_FGD), 255, 0).astype(np.uint8)
    subject = cv2.morphologyEx(subject, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
    subject = cv2.GaussianBlur(subject, (9, 9), 0)

    gray = cv2.cvtColor(cv2.bilateralFilter(image, 9, 60, 9), cv2.COLOR_BGR2GRAY)
    gray = cv2.createCLAHE(clipLimit=1.6, tileGridSize=(4, 4)).apply(gray)

    end = round(bottom * height)
    ramp = np.clip((end - np.arange(height)) / max(1, fade * height), 0, 1)[:, None]
    alpha = (subject * ramp).astype(np.uint8)
    rows = np.flatnonzero(alpha.max(axis=1) > 32)
    cols = np.flatnonzero(alpha.max(axis=0) > 32)
    if not len(rows):
        raise SystemExit("No subject found; try a different --rect")
    top = max(0, rows[0] - round(.01 * height))
    crop = np.dstack([gray, gray, gray, alpha])[top:rows[-1] + 1, cols[0]:cols[-1] + 1]
    cv2.imwrite(str(out), crop)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("src")
    parser.add_argument("out")
    parser.add_argument("--rect", default="0.15,0.02,0.61,0.95",
                        help="subject box as x,y,w,h fractions of the image (default %(default)s)")
    parser.add_argument("--bottom", type=float, default=.82,
                        help="where the bust ends, as a fraction of image height (default %(default)s)")
    parser.add_argument("--fade", type=float, default=.15,
                        help="fade length above --bottom, as a fraction of image height (default %(default)s)")
    args = parser.parse_args()
    prepare(args.src, args.out, [float(v) for v in args.rect.split(",")], args.bottom, args.fade)


if __name__ == "__main__":
    main()
