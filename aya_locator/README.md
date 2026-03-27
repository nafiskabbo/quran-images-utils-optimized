# Quran Page Aya Locator

Locate ayah markers in Quran page images and output coordinates for app highlighting.

## How it works

The locator no longer depends on hand-cropped `template_1.jpg` / `template_2.jpg` files.

Instead it:

1. learns marker shapes from your own page images,
2. matches them back across the mushaf at multiple scales,
3. uses per-page ayah counts to keep the output stable and ordered, and
4. writes coordinates in the original image pixel space.

That makes it a better fit for `images_main/` and for the downloaded mushaf images used by the app.

## Recommended usage

Put your main page images in `aya_locator/images_main/` and run:

```bash
python aya_locator.py --images images_main --output data_main.csv
```

The CSV columns are:

- `aya_id`
- `page`
- `x`
- `y`

`x` and `y` are written in the same pixel space as the source images, so they can be used directly with your main images.

## Useful options

- `--images FOLDER` - folder containing `001.jpg` ... `604.jpg`
- `--output FILE` - output CSV path
- `--debug-dir DIR` - save annotated low-confidence pages for review
- `--first N --last N` - process only part of the mushaf while tuning
- `--page-counts FILE` - override the bundled per-page ayah counts with your own 604-item JSON list

## Compare main vs prepared images

If you still want to compare both coordinate spaces, put originals in `images_main/`, prepared images in `images_prepared/`, then run:

```bash
python run_both_csvs.py
```

For the app, `images_main/` is the preferred source because the output coordinates match the original pages directly.

## Background placeholder (layout for rendering text)

To get one reusable background image with the same layout as pages 003–604 (margins, frame, dimensions) so you can render text on it:

```bash
python create_background_placeholder.py
```

This copies page 004 from `images_main/` to `mushaf_background_placeholder.jpg`. Use that image as the background layer when drawing or overlaying text in your app.

If you want a clean background (text + page count removed), use:

```bash
python create_background_placeholder.py --erase-text
```

- `--source FOLDER` – image folder (default: `images_main`)
- `--page 003|004|005` – which page to use (default: 004)
- `--out FILE` – output filename (default: `mushaf_background_placeholder.jpg`)
- `--erase-text` – remove text + page count inside the inner page box

For the cropped/prepared layout, use:  
`python create_background_placeholder.py --source images_prepared --out mushaf_background_placeholder_prepared.jpg`
