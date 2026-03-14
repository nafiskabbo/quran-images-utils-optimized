#!/usr/bin/env python3
# Purpose: Rename existing image files in downloads/ from 1.jpg, 2.jpg, ... 99.jpg
#          to 001.jpg, 002.jpg, ... 099.jpg (3-digit zero-padded). 100.jpg and
#          above are unchanged. Does not modify download_pages.py.
# Usage: run from repo root or image_downloader: python image_downloader/rename_to_padded.py

import os
import re

script_folder = os.path.dirname(os.path.abspath(__file__))
download_folder = os.path.join(script_folder, "downloads")

if not os.path.isdir(download_folder):
    print(f"Folder not found: {download_folder}")
    exit(1)

# Collect (numeric_value, filename) for all N.jpg / N.jpeg etc.
pattern = re.compile(r"^(\d+)\.(jpg|jpeg|png|webp)$", re.IGNORECASE)
entries = []
for name in os.listdir(download_folder):
    m = pattern.match(name)
    if m:
        num = int(m.group(1))
        ext = m.group(2).lower()
        if ext == "jpeg":
            ext = "jpg"
        new_name = f"{num:03d}.{ext}"
        if name != new_name:
            entries.append((num, name, new_name))

# Sort by number descending so we don't overwrite (e.g. 99 -> 099 before 9 -> 009)
entries.sort(key=lambda x: -x[0])

renamed = 0
for num, old_name, new_name in entries:
    old_path = os.path.join(download_folder, old_name)
    new_path = os.path.join(download_folder, new_name)
    if os.path.exists(new_path) and os.path.abspath(old_path) != os.path.abspath(new_path):
        print(f"Skip (target exists): {old_name} -> {new_name}")
        continue
    try:
        os.rename(old_path, new_path)
        print(f"Renamed: {old_name} -> {new_name}")
        renamed += 1
    except OSError as e:
        print(f"Error renaming {old_name}: {e}")

print(f"Done. Renamed {renamed} file(s).")
