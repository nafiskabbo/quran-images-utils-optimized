#!/usr/bin/env python3
# Create a single mushaf background placeholder from the main image folder.
#
# Pages 003, 004, 005 (and 3–604) share the same layout. This script copies one
# of them to a fixed filename so you have one canonical background image with
# that layout (margins, frame, dimensions) to render text on.
#
# Usage:
#   python create_background_placeholder.py
#   python create_background_placeholder.py --source ../image_downloader/downloads --page 004
#   python create_background_placeholder.py --source images_prepared --out mushaf_background_prepared.jpg
#
# Output: mushaf_background_placeholder.jpg (or --out path) in this folder.

import argparse
import os
import shutil

import cv2
import numpy as np

script_folder = os.path.dirname(os.path.abspath(__file__))

# Default: main (original) images = same layout as 003/004/005
DEFAULT_SOURCE = "images_main"
DEFAULT_PAGE = "004"  # one of 003, 004, 005 — same layout
DEFAULT_OUT = "mushaf_background_placeholder.jpg"
DEFAULT_INK_THRESHOLD = 80
DEFAULT_BORDER_DARK_FRACTION = 0.2
DEFAULT_RUN = 10
DEFAULT_INNER_INSET = 2
DEFAULT_INPAINT_RADIUS = 3


def _find_inner_bounds(gray, ink_threshold, border_dark_fraction, run):
    ink = gray < ink_threshold
    row_dark = ink.mean(axis=1)
    col_dark = ink.mean(axis=0)

    def find_inner_start(arr):
        n = len(arr)
        for i in range(n - run):
            if np.all(arr[i : i + run] < border_dark_fraction):
                return i
        return 0

    def find_inner_end(arr):
        n = len(arr)
        for i in range(n - 1, run - 1, -1):
            if np.all(arr[i - run + 1 : i + 1] < border_dark_fraction):
                return i
        return n - 1

    top = find_inner_start(row_dark)
    bottom = find_inner_end(row_dark)
    left = find_inner_start(col_dark)
    right = find_inner_end(col_dark)
    return left, top, right, bottom


def _erase_text(image, ink_threshold, border_dark_fraction, run, inner_inset, inpaint_radius):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    left, top, right, bottom = _find_inner_bounds(gray, ink_threshold, border_dark_fraction, run)

    left = max(0, left + inner_inset)
    top = max(0, top + inner_inset)
    right = min(gray.shape[1] - 1, right - inner_inset)
    bottom = min(gray.shape[0] - 1, bottom - inner_inset)

    mask = (gray < ink_threshold).astype(np.uint8) * 255
    inner_mask = np.zeros_like(mask)
    inner_mask[top : bottom + 1, left : right + 1] = mask[top : bottom + 1, left : right + 1]

    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    inner_mask = cv2.dilate(inner_mask, kernel, iterations=1)

    inpainted = cv2.inpaint(image, inner_mask, inpaint_radius, cv2.INPAINT_TELEA)
    return inpainted, (left, top, right, bottom)


def main():
    parser = argparse.ArgumentParser(
        description="Create one mushaf background placeholder from main image folder (003/004/005 layout)."
    )
    parser.add_argument(
        "--source",
        default=DEFAULT_SOURCE,
        help=f"Folder containing page images 001.jpg..604.jpg (default: {DEFAULT_SOURCE})",
    )
    parser.add_argument(
        "--page",
        default=DEFAULT_PAGE,
        choices=["003", "004", "005"],
        help=f"Which page to use as layout (default: {DEFAULT_PAGE})",
    )
    parser.add_argument(
        "--out",
        default=DEFAULT_OUT,
        help=f"Output filename (default: {DEFAULT_OUT})",
    )
    parser.add_argument(
        "--erase-text",
        action="store_true",
        help="Remove text + page count by inpainting inside the inner page box.",
    )
    parser.add_argument(
        "--ink-threshold",
        type=int,
        default=DEFAULT_INK_THRESHOLD,
        help=f"Ink threshold 0–255 (default: {DEFAULT_INK_THRESHOLD}). Lower keeps more dark pixels.",
    )
    parser.add_argument(
        "--border-dark-fraction",
        type=float,
        default=DEFAULT_BORDER_DARK_FRACTION,
        help=f"Dark pixel fraction that marks the border band (default: {DEFAULT_BORDER_DARK_FRACTION}).",
    )
    parser.add_argument(
        "--run",
        type=int,
        default=DEFAULT_RUN,
        help=f"Consecutive rows/cols needed to detect inner page bounds (default: {DEFAULT_RUN}).",
    )
    parser.add_argument(
        "--inner-inset",
        type=int,
        default=DEFAULT_INNER_INSET,
        help=f"Inset inner bounds before erasing text (default: {DEFAULT_INNER_INSET}).",
    )
    parser.add_argument(
        "--inpaint-radius",
        type=int,
        default=DEFAULT_INPAINT_RADIUS,
        help=f"Inpaint radius in pixels (default: {DEFAULT_INPAINT_RADIUS}).",
    )
    args = parser.parse_args()

    source_dir = args.source if os.path.isabs(args.source) else os.path.join(script_folder, args.source)
    in_path = os.path.join(source_dir, f"{args.page}.jpg")
    out_path = os.path.join(script_folder, args.out)

    if not os.path.isfile(in_path):
        print(f"Error: Source image not found: {in_path}")
        print("  Use --source to point to the folder with 003.jpg, 004.jpg, 005.jpg (e.g. images_main or image_downloader/downloads).")
        return 1

    if not args.erase_text:
        shutil.copy2(in_path, out_path)
        print(f"Created: {out_path}")
        print("  Use this image as the background layer when rendering text in the same layout (pages 3–604).")
        return 0

    image = cv2.imread(in_path, cv2.IMREAD_COLOR)
    if image is None:
        print(f"Error: Failed to read image: {in_path}")
        return 1

    cleaned, bounds = _erase_text(
        image,
        ink_threshold=args.ink_threshold,
        border_dark_fraction=args.border_dark_fraction,
        run=args.run,
        inner_inset=args.inner_inset,
        inpaint_radius=args.inpaint_radius,
    )
    cv2.imwrite(out_path, cleaned)
    left, top, right, bottom = bounds
    print(f"Created: {out_path}")
    print(f"  Erased text inside bounds: left={left}, top={top}, right={right}, bottom={bottom}.")
    print("  Use this image as the background layer when rendering text in the same layout (pages 3–604).")
    return 0


if __name__ == "__main__":
    exit(main())
