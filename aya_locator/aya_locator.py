#!/usr/bin/env python3
"""Locate ayah markers directly from Quran page images."""

import argparse
import csv
import json
import os
from dataclasses import dataclass

import cv2
import numpy as np

from page_metadata import PAGE_AYAH_COUNTS, TOTAL_AYAHS

DEFAULT_BG_THRESHOLD = 240
CONTENT_INSET = 1
PATCH_SIZE = 48
MATCH_SCALES = [0.72, 0.78, 0.84, 0.9, 0.96, 1.0, 1.06]
OPENING_MATCH_SCALES = [0.66, 0.72, 0.78, 0.84, 0.9, 0.96]
TEMPLATE_COUNT = 3
TEMPLATE_SAMPLE_START = 3
TEMPLATE_SAMPLE_LIMIT = 24
REVIEW_SCORE_THRESHOLD = 0.45


@dataclass(frozen=True)
class MarkerHit:
    score: float
    x: int
    y: int
    w: int
    h: int
    response: float
    ring_density: float

    @property
    def center_x(self):
        return self.x + (self.w / 2.0)

    @property
    def center_y(self):
        return self.y + (self.h / 2.0)


def load_page_ayah_counts(page_counts_path=None):
    """Load page ayah counts from JSON or fall back to the bundled defaults."""
    if page_counts_path is None:
        return list(PAGE_AYAH_COUNTS)

    with open(page_counts_path, "r", encoding="utf-8") as handle:
        data = json.load(handle)

    if isinstance(data, dict):
        data = data.get("counts")

    if not isinstance(data, list) or len(data) != 604:
        raise ValueError("Page counts file must be a JSON list with 604 integers.")

    counts = [int(value) for value in data]
    if any(value < 0 for value in counts):
        raise ValueError("Page counts cannot contain negative values.")
    return counts


def find_content_bounds(gray, bg_threshold=DEFAULT_BG_THRESHOLD):
    """Find the non-background content box in grayscale page images."""
    h, w = gray.shape

    left = 0
    for x in range(w):
        if float(np.mean(gray[:, x])) < bg_threshold:
            left = max(0, x - CONTENT_INSET)
            break

    right = w
    for x in range(w - 1, -1, -1):
        if float(np.mean(gray[:, x])) < bg_threshold:
            right = min(w, x + CONTENT_INSET + 1)
            break

    top = 0
    for y in range(h):
        if float(np.mean(gray[y, :])) < bg_threshold:
            top = max(0, y - CONTENT_INSET)
            break

    bottom = h
    for y in range(h - 1, -1, -1):
        if float(np.mean(gray[y, :])) < bg_threshold:
            bottom = min(h, y + CONTENT_INSET + 1)
            break

    top = max(0, min(top, h - 2))
    left = max(0, min(left, w - 2))
    bottom = max(top + 2, min(bottom, h))
    right = max(left + 2, min(right, w))
    return left, top, right, bottom


def preprocess_page(gray):
    """Crop the page to the content area and build a binary image for detection."""
    left, top, right, bottom = find_content_bounds(gray)
    cropped = gray[top:bottom, left:right]
    blurred = cv2.GaussianBlur(cropped, (3, 3), 0)
    binary = cv2.adaptiveThreshold(
        blurred,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV,
        31,
        11,
    )
    return binary, left, top


def normalized_correlation(a, b):
    """Compute normalized correlation between two same-sized float patches."""
    a_centered = (a - float(np.mean(a))).ravel()
    b_centered = (b - float(np.mean(b))).ravel()
    denom = (np.linalg.norm(a_centered) * np.linalg.norm(b_centered)) + 1e-9
    return float(np.dot(a_centered, b_centered) / denom)


def ring_density(binary, x, y, w, h):
    """Foreground density around a candidate box; ayah markers tend to be isolated."""
    pad = max(6, int(max(w, h) * 0.35))
    ry1 = max(0, y - pad)
    ry2 = min(binary.shape[0], y + h + pad)
    rx1 = max(0, x - pad)
    rx2 = min(binary.shape[1], x + w + pad)
    ring = binary[ry1:ry2, rx1:rx2].copy()
    ring[(y - ry1):(y - ry1 + h), (x - rx1):(x - rx1 + w)] = 0
    if ring.size == 0:
        return 1.0
    return float(np.mean(ring) / 255.0)


def extract_patch(binary, x, y, w, h):
    """Crop and normalize a candidate region into a fixed-size patch."""
    pad = max(4, int(max(w, h) * 0.12))
    y1 = max(0, y - pad)
    y2 = min(binary.shape[0], y + h + pad)
    x1 = max(0, x - pad)
    x2 = min(binary.shape[1], x + w + pad)
    patch = binary[y1:y2, x1:x2]
    patch = cv2.resize(patch, (PATCH_SIZE, PATCH_SIZE), interpolation=cv2.INTER_AREA)
    return patch.astype(np.float32) / 255.0


def iter_component_boxes(binary, strict=False):
    """Yield compact component boxes that could plausibly be ayah markers."""
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    closed = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
    num_labels, _, stats, _ = cv2.connectedComponentsWithStats(closed, 8)
    page_h, page_w = binary.shape

    for idx in range(1, num_labels):
        x, y, w, h, area = stats[idx]
        if w <= 0 or h <= 0:
            continue

        width_ratio = w / float(page_w)
        height_ratio = h / float(page_h)
        aspect = w / float(h)
        fill = area / float(w * h)

        if strict:
            if not (0.028 <= width_ratio <= 0.055 and 0.025 <= height_ratio <= 0.05):
                continue
            if not (0.65 <= aspect <= 1.05 and 0.18 <= fill <= 0.5):
                continue
        else:
            if not (0.012 <= width_ratio <= 0.08 and 0.012 <= height_ratio <= 0.07):
                continue
            if not (0.45 <= aspect <= 1.35 and 0.1 <= fill <= 0.65):
                continue

        yield x, y, w, h, area, fill


def learn_marker_templates(images_folder, page_counts, first_page=1, last_page=604):
    """Learn marker templates from the current mushaf instead of fixed bundled crops."""
    seed_patches = []
    sampled_pages = 0

    start_page = max(TEMPLATE_SAMPLE_START, first_page)
    for page in range(start_page, last_page + 1):
        if sampled_pages >= TEMPLATE_SAMPLE_LIMIT and len(seed_patches) >= 30:
            break

        image_path = os.path.join(images_folder, f"{page:03}.jpg")
        gray = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
        if gray is None:
            continue

        binary, _, _ = preprocess_page(gray)
        candidates = []
        for x, y, w, h, _, _ in iter_component_boxes(binary, strict=True):
            patch = extract_patch(binary, x, y, w, h)
            score = 1.0 - ring_density(binary, x, y, w, h)
            candidates.append((score, patch))

        if not candidates:
            continue

        candidates.sort(key=lambda item: item[0], reverse=True)
        expected = page_counts[page - 1]
        seed_patches.extend(patch for _, patch in candidates[:expected])
        sampled_pages += 1

    if not seed_patches:
        raise RuntimeError("Could not learn ayah markers from the provided images.")

    mean_patch = np.mean(seed_patches, axis=0)
    correlations = [normalized_correlation(patch, mean_patch) for patch in seed_patches]
    cutoff = float(np.quantile(correlations, 0.55))
    refined = [
        (corr, patch)
        for corr, patch in zip(correlations, seed_patches)
        if corr >= cutoff
    ]
    refined.sort(key=lambda item: item[0], reverse=True)

    reference = np.mean([patch for _, patch in refined], axis=0) if refined else mean_patch
    templates = []
    for _, patch in refined:
        if any(normalized_correlation(patch, chosen) > 0.985 for chosen in templates):
            continue
        templates.append(patch)
        if len(templates) >= TEMPLATE_COUNT:
            break

    if not templates:
        best_idx = int(np.argmax(correlations))
        templates = [seed_patches[best_idx]]

    template_images = [np.clip(template * 255.0, 0, 255).astype(np.uint8) for template in templates]
    return template_images, reference


def non_max_suppress(hits, limit=None):
    """Suppress near-duplicate detections from overlapping templates and scales."""
    ranked = sorted(hits, key=lambda hit: hit.score, reverse=True)
    kept = []
    for hit in ranked:
        duplicate = False
        for existing in kept:
            distance_sq = ((hit.center_x - existing.center_x) ** 2) + ((hit.center_y - existing.center_y) ** 2)
            threshold = max(hit.w, hit.h, existing.w, existing.h) * 0.8
            if distance_sq < (threshold ** 2):
                duplicate = True
                break
        if duplicate:
            continue
        kept.append(hit)
        if limit is not None and len(kept) >= limit:
            break
    return kept


def collect_template_hits(binary, templates, expected_count, opening_page=False):
    """Run multi-scale template matching and gather the strongest candidates."""
    raw_hits = []
    scales = OPENING_MATCH_SCALES if opening_page else MATCH_SCALES
    top_k = max(40, expected_count * 6)

    for template in templates:
        for scale in scales:
            width = max(8, int(round(template.shape[1] * scale)))
            height = max(8, int(round(template.shape[0] * scale)))
            if width >= binary.shape[1] or height >= binary.shape[0]:
                continue

            interpolation = cv2.INTER_AREA if scale <= 1.0 else cv2.INTER_LINEAR
            resized = cv2.resize(template, (width, height), interpolation=interpolation)
            result = cv2.matchTemplate(binary, resized, cv2.TM_CCOEFF_NORMED)
            flat = result.ravel()
            count = min(top_k, flat.size)
            if count <= 0:
                continue

            top_indices = np.argpartition(flat, -count)[-count:]
            for idx in top_indices:
                y, x = divmod(int(idx), result.shape[1])
                response = float(result[y, x])
                ring = ring_density(binary, x, y, width, height)
                score = (response * 0.9) + ((1.0 - ring) * 0.1)
                raw_hits.append(MarkerHit(score, x, y, width, height, response, ring))

    return non_max_suppress(raw_hits, limit=max(expected_count * 4, 20))


def collect_component_fallback_hits(binary, reference_template, expected_count):
    """Fallback candidates from connected components for pages where matching is weaker."""
    hits = []
    for x, y, w, h, _, _ in iter_component_boxes(binary, strict=False):
        patch = extract_patch(binary, x, y, w, h)
        correlation = normalized_correlation(patch, reference_template)
        ring = ring_density(binary, x, y, w, h)
        score = (correlation * 0.75) + ((1.0 - ring) * 0.25)
        hits.append(MarkerHit(score, x, y, w, h, correlation, ring))

    hits.sort(key=lambda hit: hit.score, reverse=True)
    return non_max_suppress(hits, limit=max(expected_count * 4, 20))


def sort_hits_reading_order(hits):
    """Sort markers from top to bottom, then right to left inside each line."""
    if not hits:
        return []

    ordered = sorted(hits, key=lambda hit: hit.center_y)
    line_threshold = max(12.0, float(np.median([hit.h for hit in hits])) * 0.9)
    lines = []
    current_line = [ordered[0]]
    current_center = ordered[0].center_y

    for hit in ordered[1:]:
        if abs(hit.center_y - current_center) <= line_threshold:
            current_line.append(hit)
            current_center = (
                (current_center * (len(current_line) - 1)) + hit.center_y
            ) / len(current_line)
        else:
            lines.append(current_line)
            current_line = [hit]
            current_center = hit.center_y

    lines.append(current_line)
    output = []
    for line in lines:
        output.extend(sorted(line, key=lambda hit: -hit.center_x))
    return output


def save_debug_page(debug_dir, page, image, hits, crop_left, crop_top):
    """Save annotated debug pages for manual QA."""
    os.makedirs(debug_dir, exist_ok=True)
    debug = image.copy()
    for index, hit in enumerate(hits, start=1):
        x1 = crop_left + hit.x
        y1 = crop_top + hit.y
        x2 = x1 + hit.w
        y2 = y1 + hit.h
        cv2.rectangle(debug, (x1, y1), (x2, y2), (0, 0, 255), 2)
        label = f"{index}:{hit.score:.2f}"
        cv2.putText(debug, label, (x1, max(18, y1 - 4)), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 128, 255), 1, cv2.LINE_AA)
    cv2.imwrite(os.path.join(debug_dir, f"{page:03}.jpg"), debug)


def run_locator(
    images_folder,
    output_csv,
    script_folder=None,
    page_counts_path=None,
    debug_dir=None,
    first_page=1,
    last_page=604,
):
    """Run ayah location on images_folder and write the result CSV."""
    if script_folder and page_counts_path and not os.path.isabs(page_counts_path):
        page_counts_path = os.path.join(script_folder, page_counts_path)

    page_counts = load_page_ayah_counts(page_counts_path)
    templates, reference_template = learn_marker_templates(images_folder, page_counts, first_page, last_page)
    print(f"Learned {len(templates)} marker template(s) from {images_folder}")

    aya_id = sum(page_counts[: first_page - 1]) + 1
    output_rows = []
    low_confidence_pages = []

    for page in range(first_page, last_page + 1):
        image_path = os.path.join(images_folder, f"{page:03}.jpg")
        image = cv2.imread(image_path)
        if image is None:
            print(f"Warning: Skipping page {page:03} (image not found)")
            continue

        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        binary, crop_left, crop_top = preprocess_page(gray)
        expected = page_counts[page - 1]

        hits = collect_template_hits(binary, templates, expected, opening_page=(page <= 2))
        if len(hits) < expected:
            hits.extend(collect_component_fallback_hits(binary, reference_template, expected))
            hits = non_max_suppress(hits, limit=max(expected * 4, 20))

        selected = sort_hits_reading_order(hits[:expected])

        if len(selected) != expected:
            print(f"Warning: Page {page:03} expected {expected} ayahs but found {len(selected)}")

        min_score = min((hit.score for hit in selected), default=0.0)
        avg_score = float(np.mean([hit.score for hit in selected])) if selected else 0.0
        if min_score < REVIEW_SCORE_THRESHOLD or len(selected) != expected:
            low_confidence_pages.append(page)
            print(f"Page {page:03}: expected {expected}, found {len(selected)}, avg {avg_score:.3f}, min {min_score:.3f}  [review]")
            if debug_dir:
                save_debug_page(debug_dir, page, image, selected, crop_left, crop_top)
        else:
            print(f"Page {page:03}: expected {expected}, found {len(selected)}, avg {avg_score:.3f}, min {min_score:.3f}")

        for hit in selected:
            output_rows.append([aya_id, page, crop_left + hit.x, crop_top + hit.y])
            aya_id += 1

    expected_total = sum(page_counts[first_page - 1:last_page])
    matched = len(output_rows)
    if matched != expected_total:
        print(f"Error: Missing {expected_total - matched} ayah matches")
    else:
        print("All ayahs were matched for the requested page range")

    with open(output_csv, "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["aya_id", "page", "x", "y"])
        writer.writerows(output_rows)

    if low_confidence_pages:
        sample = ", ".join(f"{page:03}" for page in low_confidence_pages[:20])
        suffix = " ..." if len(low_confidence_pages) > 20 else ""
        print(f"Low-confidence pages: {sample}{suffix}")

    print(f"Wrote {output_csv} ({matched} ayahs)")
    return matched


def main():
    parser = argparse.ArgumentParser(description="Locate ayah markers in Quran page images and output CSV.")
    parser.add_argument("--images", default="images", help="Images folder name (under script dir) or path (default: images)")
    parser.add_argument("--output", default="data.csv", help="Output CSV filename (default: data.csv)")
    parser.add_argument("--page-counts", help="Optional JSON file with 604 per-page ayah counts")
    parser.add_argument("--debug-dir", help="Optional folder for annotated low-confidence pages")
    parser.add_argument("--first", type=int, default=1, help="First page number to process (default: 1)")
    parser.add_argument("--last", type=int, default=604, help="Last page number to process (default: 604)")
    args = parser.parse_args()

    if not (1 <= args.first <= args.last <= 604):
        print("Error: page range must satisfy 1 <= first <= last <= 604")
        return 1

    script_folder = os.path.dirname(os.path.abspath(__file__))
    images_folder = args.images if os.path.isabs(args.images) else os.path.join(script_folder, args.images)
    output_csv = args.output if os.path.isabs(args.output) else os.path.join(script_folder, args.output)
    debug_dir = None
    if args.debug_dir:
        debug_dir = args.debug_dir if os.path.isabs(args.debug_dir) else os.path.join(script_folder, args.debug_dir)

    if not os.path.isdir(images_folder):
        print(f"Error: Images folder not found: {images_folder}")
        return 1

    expected_total = sum(PAGE_AYAH_COUNTS[args.first - 1:args.last])
    if args.page_counts:
        page_counts_path = args.page_counts if os.path.isabs(args.page_counts) else os.path.join(script_folder, args.page_counts)
        counts = load_page_ayah_counts(page_counts_path)
        expected_total = sum(counts[args.first - 1:args.last])
    else:
        page_counts_path = None

    matched = run_locator(
        images_folder,
        output_csv,
        script_folder=script_folder,
        page_counts_path=page_counts_path,
        debug_dir=debug_dir,
        first_page=args.first,
        last_page=args.last,
    )
    return 0 if matched == expected_total else 1


if __name__ == "__main__":
    raise SystemExit(main())

