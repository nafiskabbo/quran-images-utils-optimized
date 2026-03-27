#!/usr/bin/env python3
# Run aya_locator on both main (original) and prepared (cropped) images
# to generate data_main.csv and data_prepared.csv for comparison.
#
# Setup:
#   1. Put original page images in aya_locator/images_main/ (001.jpg .. 604.jpg)
#   2. Put prepared page images in aya_locator/images_prepared/
#      (e.g. symlink: ln -s ../image_prepare/output images_prepared)
# Then run: python run_both_csvs.py

import os
import sys

script_folder = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, script_folder)

from aya_locator import run_locator

def main():
    main_folder = os.path.join(script_folder, "images_main")
    prepared_folder = os.path.join(script_folder, "images_prepared")
    csv_main = os.path.join(script_folder, "data_main.csv")
    csv_prepared = os.path.join(script_folder, "data_prepared.csv")

    if not os.path.isdir(main_folder):
        print(f"Error: Put original page images in: {main_folder}")
        return 1
    if not os.path.isdir(prepared_folder):
        print(f"Error: Put prepared page images in: {prepared_folder}")
        print("  (e.g. copy from image_prepare/output/ or symlink that folder)")
        return 1

    print("=== Running on MAIN (original) images -> data_main.csv ===")
    n_main = run_locator(main_folder, csv_main, script_folder)
    print()

    print("=== Running on PREPARED (cropped) images -> data_prepared.csv ===")
    n_prepared = run_locator(prepared_folder, csv_prepared, script_folder)
    print()

    print("Done. Compare data_main.csv and data_prepared.csv to see which is more accurate for your app.")
    print(f"  Main images:     {n_main} ayas -> data_main.csv")
    print(f"  Prepared images: {n_prepared} ayas -> data_prepared.csv")
    return 0

if __name__ == "__main__":
    exit(main())
