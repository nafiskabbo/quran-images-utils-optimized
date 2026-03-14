# Quran Page Aya Locator

Locate ayas in Quran page images and output coordinates (CSV) for highlighting in your app.

## Using your own mushaf (different images)

The bundled `template_1.jpg` and `template_2.jpg` are for a specific mushaf. **If your app uses a different mushaf, you must create templates from your own images:**

1. **Extract two templates from your pages**
   - From a **first or second page** image, run:
     ```bash
     python extract_templates.py path/to/your_page001.jpg --template 1
     ```
   - In the window: **click and drag** a rectangle around **one aya** (or one aya marker). Press **`s`** to save as `template_1.jpg`. Press **`r`** to clear and reselect, **`q`** to quit.
   - From a **later page** (e.g. 010), run:
     ```bash
     python extract_templates.py path/to/your_page010.jpg --template 2
     ```
   - Select one aya again and press **`s`** to save `template_2.jpg`.

2. **Put your main (full) page images** in a folder, e.g. `aya_locator/images_main/` (001.jpg … 604.jpg).

3. **Run the locator on your main images** (best for highlighting in your app):
   ```bash
   python aya_locator.py --images images_main --output data.csv
   ```
   The CSV has `aya_id, page, x, y` in **your image pixel coordinates**, so you can highlight ayas directly on your main images.

Multi-scale matching runs automatically so small resolution differences between the template and pages are handled. Use the generated `data.csv` with your main images for accurate highlighting.

## Default usage (same mushaf as bundled templates)

- Put page images in `aya_locator/images/` (001.jpg … 604.jpg).
- Run: `python aya_locator.py`
- Output: `data.csv` with columns `aya_id`, `page`, `x`, `y`.

## Options

- `--images FOLDER` — folder containing 001.jpg … 604.jpg (default: `images`).
- `--output FILE` — output CSV path (default: `data.csv`).

## Compare main vs prepared images

To generate both `data_main.csv` and `data_prepared.csv` for comparison, put originals in `images_main/`, prepared in `images_prepared/`, then run `python run_both_csvs.py`.
