#!/usr/bin/env python3
# Purpose: Prepare the Quran images (crop borders, resize, optimize).
# Works with your mushaf: auto-detects content bounds from each image.
#
# - Crop: removes borders by detecting where content starts (no fixed offsets).
# - Resize & optimize to reduce file size.
# - Input: image_prepare/images/ (001.jpg … 604.jpg).
# - Output: image_prepare/output/ (same names).
#
# Pre-requisites: Python 3.6+, Pillow (pip install pillow).
#
import argparse
import os
import numpy as np
from PIL import Image

script_folder = os.path.dirname(os.path.abspath(__file__))
input_folder = os.path.join(script_folder, "images")
output_folder = os.path.join(script_folder, "output")

# Conservative border crop: only remove very bright margin (avoids cutting into content).
# Threshold 240 = trim where mean intensity drops below 240 (keeps decorative border).
DEFAULT_BG_THRESHOLD = 240
CONTENT_INSET = 1
DEFAULT_RESIZE_RATIO = 0.5

def find_content_bounds(im, bg_threshold):
    """
    Find content box by scanning from each edge until non-background pixels.
    Returns (left, top, right, bottom) in pixel coordinates.
    """
    arr = np.array(im.convert("L"))
    h, w = arr.shape

    left = 0
    for x in range(w):
        if np.mean(arr[:, x]) < bg_threshold:
            left = max(0, x - CONTENT_INSET)
            break

    right = w
    for x in range(w - 1, -1, -1):
        if np.mean(arr[:, x]) < bg_threshold:
            right = min(w, x + CONTENT_INSET + 1)
            break

    top = 0
    for y in range(h):
        if np.mean(arr[y, :]) < bg_threshold:
            top = max(0, y - CONTENT_INSET)
            break

    bottom = h
    for y in range(h - 1, -1, -1):
        if np.mean(arr[y, :]) < bg_threshold:
            bottom = min(h, y + CONTENT_INSET + 1)
            break

    return left, top, right, bottom


def main():
    parser = argparse.ArgumentParser(description="Prepare Quran page images: auto-crop borders, resize, optimize.")
    parser.add_argument("--threshold", type=int, default=DEFAULT_BG_THRESHOLD,
                        help="Background intensity threshold 0–255 (default: 240, conservative). Lower = more crop.")
    parser.add_argument("--ratio", type=float, default=DEFAULT_RESIZE_RATIO,
                        help="Resize ratio after crop (default: 0.5).")
    parser.add_argument("--first", type=int, default=1, help="First page number (default: 1).")
    parser.add_argument("--last", type=int, default=604, help="Last page number (default: 604).")
    parser.add_argument("--no-crop", action="store_true", help="Do not crop; only resize and optimize (keeps full image).")
    args = parser.parse_args()

    if not os.path.exists(output_folder):
        os.mkdir(output_folder)

    bg_threshold = args.threshold
    resize_ratio = args.ratio

    for i in range(args.first, args.last + 1):
        input_path = os.path.join(input_folder, f"{i:03}.jpg")
        output_path = os.path.join(output_folder, f"{i:03}.jpg")

        if not os.path.exists(input_path):
            print(f"Skip {i}: missing {input_path}")
            continue

        image = Image.open(input_path).convert("RGB")
        width, height = image.size

        if args.no_crop:
            left, top, right, bottom = 0, 0, width, height
        else:
            left, top, right, bottom = find_content_bounds(image, bg_threshold)
            left = max(0, min(left, width - 2))
            top = max(0, min(top, height - 2))
            right = max(left + 2, min(right, width))
            bottom = max(top + 2, min(bottom, height))

        cropped = image.crop((left, top, right, bottom))
        cw, ch = cropped.size

        new_width = max(1, int(cw * resize_ratio))
        new_height = max(1, int(ch * resize_ratio))
        resampler = getattr(Image, "Resampling", None)
        resample = resampler.LANCZOS if resampler else Image.LANCZOS
        resized = cropped.resize((new_width, new_height), resample)
        resized.save(output_path, optimize=True, quality=85)

        crop_msg = "no-crop" if args.no_crop else f"crop {left},{top},{right},{bottom}"
        print(f"Prepared {i} of {args.last} ({crop_msg} -> {cw}x{ch} -> {new_width}x{new_height})")

    print("Done preparing images")


if __name__ == "__main__":
    main()
