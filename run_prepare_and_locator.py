#!/usr/bin/env python3
# Run full pipeline: 1) Prepare images (crop borders, resize). 2) Run aya_locator on main and prepared images.
# Uses templates from aya_locator/ (template_1.jpg, template_2.jpg).
# Requires: image_prepare/images/ and aya_locator/images_main/ (or symlinks), and aya_locator/template_*.jpg.

import os
import subprocess
import sys

repo = os.path.dirname(os.path.abspath(__file__))
prepare_script = os.path.join(repo, "image_prepare", "prepare_imgs.py")
aya_dir = os.path.join(repo, "aya_locator")
run_both = os.path.join(aya_dir, "run_both_csvs.py")

def main():
    print("=== Step 1: Prepare images (crop borders, resize) ===\n")
    r = subprocess.run([sys.executable, prepare_script], cwd=repo)
    if r.returncode != 0:
        return r.returncode

    print("\n=== Step 2: Run aya_locator on MAIN and PREPARED images ===\n")
    r = subprocess.run([sys.executable, run_both], cwd=aya_dir)
    return r.returncode

if __name__ == "__main__":
    sys.exit(main())
