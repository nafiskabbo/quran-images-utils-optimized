#!/usr/bin/env python3
# Extract aya templates from YOUR mushaf images so aya_locator works with your layout.
#
# Use when you have a different mushaf: the bundled template_1/template_2 won't match.
# Run this twice: once on page 1 or 2 (saves template_1.jpg), once on a later page (saves template_2.jpg).
#
# Usage:
#   python extract_templates.py path/to/001.jpg --template 1   # for first two pages
#   python extract_templates.py path/to/010.jpg --template 2   # for pages 3–604
#
# In the window: click and drag to select a rectangle around ONE aya (or aya marker).
# Then press 's' to save, or 'r' to clear and reselect. Press 'q' to quit without saving.

import argparse
import os
import cv2
import numpy as np

script_folder = os.path.dirname(os.path.abspath(__file__))

# Global state for mouse callback
start_pt = None
end_pt = None
selecting = False
img_display = None
img_orig = None
window_name = "Select one aya: drag rectangle, then press 's' to save, 'q' to quit"


def on_mouse(event, x, y, flags, param):
    global start_pt, end_pt, selecting, img_display, img_orig
    if event == cv2.EVENT_LBUTTONDOWN:
        start_pt = (x, y)
        end_pt = (x, y)
        selecting = True
    elif event == cv2.EVENT_MOUSEMOVE and selecting:
        end_pt = (x, y)
        img_display = img_orig.copy()
        cv2.rectangle(img_display, start_pt, end_pt, (0, 255, 0), 2)
        cv2.imshow(window_name, img_display)
    elif event == cv2.EVENT_LBUTTONUP:
        end_pt = (x, y)
        selecting = False
        img_display = img_orig.copy()
        cv2.rectangle(img_display, start_pt, end_pt, (0, 255, 0), 2)
        cv2.imshow(window_name, img_display)


def main():
    parser = argparse.ArgumentParser(
        description="Extract aya template from one of your mushaf page images."
    )
    parser.add_argument("image", help="Path to a page image (e.g. 001.jpg for template 1, 010.jpg for template 2)")
    parser.add_argument("--template", type=int, choices=[1, 2], default=1,
                        help="Which template: 1 = first two pages, 2 = pages 3–604 (default: 1)")
    args = parser.parse_args()

    global img_orig, img_display
    img_orig = cv2.imread(args.image)
    if img_orig is None:
        print(f"Error: Could not load image: {args.image}")
        return 1

    img_display = img_orig.copy()
    cv2.namedWindow(window_name)
    cv2.setMouseCallback(window_name, on_mouse)
    cv2.imshow(window_name, img_display)

    print("Drag a rectangle around ONE aya (or aya marker), then press 's' to save, 'r' to reselect, 'q' to quit.")
    while True:
        key = cv2.waitKey(1) & 0xFF
        if key == ord("q"):
            print("Quit without saving.")
            break
        if key == ord("r"):
            start_pt = end_pt = None
            img_display = img_orig.copy()
            cv2.imshow(window_name, img_display)
            print("Selection cleared. Draw again and press 's' to save.")
            continue
        if key == ord("s"):
            if start_pt is None or end_pt is None:
                print("Draw a rectangle first, then press 's'.")
                continue
            x1, x2 = min(start_pt[0], end_pt[0]), max(start_pt[0], end_pt[0])
            y1, y2 = min(start_pt[1], end_pt[1]), max(start_pt[1], end_pt[1])
            if x2 - x1 < 5 or y2 - y1 < 5:
                print("Selection too small. Draw a larger rectangle.")
                continue
            crop = img_orig[y1:y2, x1:x2]
            out_name = f"template_{args.template}.jpg"
            out_path = os.path.join(script_folder, out_name)
            cv2.imwrite(out_path, crop)
            print(f"Saved {out_name} from your image. Use it with aya_locator on your main images.")
            break

    cv2.destroyAllWindows()
    return 0


if __name__ == "__main__":
    exit(main())
