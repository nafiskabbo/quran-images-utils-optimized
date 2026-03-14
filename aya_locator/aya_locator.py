#!/usr/bin/env python3
# Purpose: Locate the Aya in the Quran images.
# Author: Abdallah Abdelazim
# Features:
# - Locate the Aya in the Quran images.
# - The input images are expected to be in the 'images' sub-folder (or --images).
# - The 'template_1.jpg' and 'template_2.jpg' are expected in the same folder as this script.
# - The input & output images are named as 001.jpg, 002.jpg, etc.
# - The output is the coordinates of the Aya in each image.
# - The output is saved to 'data.csv' (or --output).
# Usage:
#   python aya_locator.py [--images FOLDER] [--output CSV]
#   e.g. python aya_locator.py --images images_main --output data_main.csv
# Pre-requisites:
# - Python 3.6 or higher.
# - OpenCV package (pip install opencv-python).
# - Numpy package (pip install numpy).
#
import argparse
import os
import cv2
import numpy as np
import csv

def group_and_sort(points, group_y_threshold):
    """
    Groups the given points by y-coordinates with a maximum difference of `group_y_threshold` between each group.
    Within each group, sorts the points by x-coordinate in acending order.
    Returns a list of all points sorted.
    """
    groups = []
    current_group = []

    # Sort points by y-coordinate
    points_sorted = sorted(points, key=lambda p: p[1])

    # Group points by y-coordinate with a maximum difference of group_y_threshold
    for point in points_sorted:
        if not current_group or abs(point[1] - current_group[0][1]) <= group_y_threshold:
            current_group.append(point)
        else:
            groups.append(current_group)
            current_group = [point]
    groups.append(current_group)

    # Sort each group by x-coordinate in ascending order
    for group in groups:
        group.sort(key=lambda p: -p[0])

    # Flatten groups into a single list
    result = [point for group in groups for point in group]

    return result



# Set a threshold for the correlation coefficient (template matching)
threshold = 0.4

# Multi-scale matching: try these scales when template size may not match image resolution
# (e.g. when using templates extracted from a different resolution). Best scale per page is chosen.
match_scales = [0.8, 0.9, 1.0, 1.1, 1.2]

# Total number of ayas in Quran (Hafs: 6236)
total_ayas = 6236

# Show the preview of the input image with the matched location
show_preview = False


def _match_at_scale(input_image, template, scale, threshold):
    """Run template matching at one scale. Returns (locations, tw, th) in input_image coords."""
    th, tw = template.shape[:2]
    if abs(scale - 1.0) < 0.01:
        tpl = template
        tw_s, th_s = tw, th
    else:
        tw_s = max(1, int(tw * scale))
        th_s = max(1, int(th * scale))
        tpl = cv2.resize(template, (tw_s, th_s), interpolation=cv2.INTER_AREA)
    result = cv2.matchTemplate(input_image, tpl, cv2.TM_CCOEFF_NORMED)
    locations = np.where(result >= threshold)
    locations = list(zip(*locations[::-1]))
    return locations, tw_s, th_s


def run_locator(images_folder, output_csv, script_folder):
    """Run aya location on images in images_folder and write results to output_csv."""
    template_1 = cv2.imread(os.path.join(script_folder, "template_1.jpg"))
    template_2 = cv2.imread(os.path.join(script_folder, "template_2.jpg"))
    if template_1 is None or template_2 is None:
        raise FileNotFoundError(
            "template_1.jpg and template_2.jpg must be in the script folder. "
            "Using a different mushaf? Run extract_templates.py on your images first."
        )

    aya_id = 1
    output_data = []

    for i in range(1, 605):
        if i == 1 or i == 2:
            template = template_1
        else:
            template = template_2

        template_height, template_width = template.shape[:2]
        input_image = cv2.imread(os.path.join(images_folder, f"{i:03}.jpg"))
        if input_image is None:
            print(f"Warning: Skipping page {i} (image not found)")
            continue

        # Multi-scale: pick the scale that gives the most matches for this page
        best_locations = []
        best_tw = template_width
        best_th = template_height
        for scale in match_scales:
            locations, tw_s, th_s = _match_at_scale(input_image, template, scale, threshold)
            min_distance = max(tw_s, th_s)
            distinct = []
            for loc1 in locations:
                is_distinct = True
                for loc2 in distinct:
                    d = np.sqrt((loc1[0] - loc2[0]) ** 2 + (loc1[1] - loc2[1]) ** 2)
                    if d < min_distance:
                        is_distinct = False
                        break
                if is_distinct:
                    distinct.append(loc1)
            if len(distinct) > len(best_locations):
                best_locations = distinct
                best_tw, best_th = tw_s, th_s

        sorted_distinct_locations = group_and_sort(best_locations, best_th / 2)

        for loc in sorted_distinct_locations:
            print(f"Aya {aya_id} -> ({loc[0]}, {loc[1]})")
            output_data.append([aya_id, i, loc[0], loc[1]])
            aya_id += 1

        if show_preview:
            for loc in sorted_distinct_locations:
                x, y = loc
                cv2.rectangle(input_image, (x, y), (x + best_tw, y + best_th), (0, 0, 255), 2)
            cv2.imshow('Matched regions', input_image)
            cv2.waitKey(0)
            cv2.destroyAllWindows()

    matched = aya_id - 1
    if matched != total_ayas:
        print(f"Error: Missing {total_ayas - matched} aya matches (threshold = {threshold})")
    else:
        print("All ayas are matched successfully")

    with open(output_csv, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(['aya_id', 'page', 'x', 'y'])
        writer.writerows(output_data)
    print(f"Wrote {output_csv} ({matched} ayas)")
    return matched


def main():
    parser = argparse.ArgumentParser(description="Locate ayas in Quran page images and output CSV.")
    parser.add_argument("--images", default="images", help="Images folder name (under script dir) or path (default: images)")
    parser.add_argument("--output", default="data.csv", help="Output CSV filename (default: data.csv)")
    args = parser.parse_args()

    script_folder = os.path.dirname(os.path.abspath(__file__))
    images_folder = args.images if os.path.isabs(args.images) else os.path.join(script_folder, args.images)
    output_csv = args.output if os.path.isabs(args.output) else os.path.join(script_folder, args.output)

    if not os.path.isdir(images_folder):
        print(f"Error: Images folder not found: {images_folder}")
        return 1

    run_locator(images_folder, output_csv, script_folder)
    return 0


if __name__ == "__main__":
    exit(main())

