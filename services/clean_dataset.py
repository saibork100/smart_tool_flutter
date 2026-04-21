# Copyright © 2026 Mahmoud Triki (W2069987), University of Westminster. All rights reserved.
"""
clean_dataset.py — Scan dataset folders and remove corrupt/unreadable images.

Run this before training to prevent cv2.error crashes.

Usage:
    python services/clean_dataset.py           # scan + delete bad files
    python services/clean_dataset.py --dry-run # only report, don't delete
"""

from __future__ import annotations

import argparse
from pathlib import Path

from tqdm import tqdm

DATASET_ROOT = Path(r"E:\photo coliction\dataset")
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff"}


def is_valid(path: Path) -> bool:
    """Return True if the file can be fully decoded as an image."""
    try:
        import cv2
        import numpy as np
        img = cv2.imdecode(np.fromfile(str(path), dtype=np.uint8), cv2.IMREAD_COLOR)
        if img is None or img.size == 0:
            return False
        # Also verify minimum dimensions
        if img.shape[0] < 32 or img.shape[1] < 32:
            return False
        return True
    except Exception:
        return False


def scan_and_clean(root: Path, dry_run: bool) -> None:
    # Collect all image files
    all_files = [
        f for f in root.rglob("*")
        if f.is_file() and f.suffix.lower() in IMAGE_EXTS
    ]

    print(f"\nScanning {len(all_files)} images under {root} ...\n")

    bad: list[Path] = []
    for path in tqdm(all_files, desc="Checking", unit="img"):
        if not is_valid(path):
            bad.append(path)

    print(f"\nFound {len(bad)} corrupt / unreadable files out of {len(all_files)}")

    if not bad:
        print("Dataset is clean. Ready to train.")
        return

    if dry_run:
        print("\n[DRY RUN] Would delete:")
        for p in bad[:30]:
            print(f"  {p.relative_to(root)}")
        if len(bad) > 30:
            print(f"  ... and {len(bad) - 30} more")
        return

    print("\nDeleting bad files ...")
    deleted = 0
    for p in tqdm(bad, desc="Deleting", unit="file"):
        try:
            p.unlink()
            deleted += 1
        except Exception as e:
            print(f"  [warn] Could not delete {p}: {e}")

    print(f"\nDeleted {deleted} files.")

    # Report per-class counts after cleanup
    print("\nImages per class after cleanup:")
    low: list[tuple[str, int]] = []
    for split in ("train", "val"):
        split_dir = root / split
        if not split_dir.exists():
            continue
        for cls_dir in sorted(split_dir.iterdir()):
            if not cls_dir.is_dir():
                continue
            count = sum(1 for f in cls_dir.iterdir() if f.suffix.lower() in IMAGE_EXTS)
            if count < 10:
                low.append((f"{split}/{cls_dir.name}", count))

    if low:
        print(f"\nWARNING: {len(low)} class/split folders have fewer than 10 images:")
        for name, count in low:
            print(f"  {name}: {count} images")
        print("\nConsider re-running image_downloader.py --skip-existing to top them up.")
    else:
        print("All classes have >= 10 images. Dataset is ready.")

    print("\nNext step: python services/dataset_builder.py train-finetune")


def main() -> None:
    parser = argparse.ArgumentParser(description="Remove corrupt images from dataset")
    parser.add_argument("--dry-run", action="store_true",
                        help="Report bad files without deleting them")
    parser.add_argument("--path", default=str(DATASET_ROOT),
                        help=f"Dataset root (default: {DATASET_ROOT})")
    args = parser.parse_args()

    root = Path(args.path)
    if not root.exists():
        print(f"ERROR: Path not found: {root}")
        return

    scan_and_clean(root, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
