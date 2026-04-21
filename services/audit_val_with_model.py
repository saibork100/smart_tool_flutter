# Copyright © 2026 Mahmoud Triki (W2069987), University of Westminster. All rights reserved.
"""
audit_val_with_model.py — Auto-audit val images using the trained YOLO model.

For each val image, runs inference and flags it if:
  1. Top-1 prediction != folder class  (wrong type / cross-class contamination)
  2. Top-1 confidence < MIN_CONF       (ambiguous / corrupt image)

Also detects near-duplicate images within each class using perceptual hashing.

Output:
  audit_report.txt  — human-readable list of suspicious images to review
  audit_delete.py   — ready-to-run deletion script for auto-flagged images

Usage:
    pip install imagehash pillow ultralytics
    python services/audit_val_with_model.py

Adjust MODEL_PATH and MIN_CONF as needed.
"""

from __future__ import annotations

import sys
from pathlib import Path
from collections import defaultdict

# ── Config ────────────────────────────────────────────────────────────────────
VAL_DIR    = Path(r"E:\photo coliction\type_dataset\val")
MODEL_PATH = Path(r"D:\smart_tool_flutter\runs\classify\runs\classify\type_v22\weights\best.pt")
MIN_CONF   = 0.30   # flag if top-1 confidence below this
HASH_BITS  = 8      # perceptual hash size (higher = stricter)
HASH_DIST  = 4      # hamming distance threshold for "duplicate"
# ─────────────────────────────────────────────────────────────────────────────

try:
    from ultralytics import YOLO
except ImportError:
    sys.exit("ultralytics not installed: pip install ultralytics")

try:
    import imagehash
    from PIL import Image
    HAS_HASH = True
except ImportError:
    print("WARNING: imagehash/Pillow not found — duplicate detection skipped.")
    print("         pip install imagehash pillow")
    HAS_HASH = False


def run_audit() -> None:
    print(f"Loading model: {MODEL_PATH}")
    model = YOLO(str(MODEL_PATH))

    # Map class index → class name from model
    idx_to_name: dict[int, str] = model.names  # {0: 'boulon__inox__a2', ...}
    name_to_idx: dict[str, int] = {v: k for k, v in idx_to_name.items()}

    class_dirs = sorted([d for d in VAL_DIR.iterdir() if d.is_dir()])
    print(f"Auditing {len(class_dirs)} classes in {VAL_DIR}\n")

    wrong_class: list[tuple[str, str, str, float]] = []  # (class, file, predicted, conf)
    low_conf:    list[tuple[str, str, str, float]] = []
    duplicates:  list[tuple[str, str, str]]        = []  # (class, file_a, file_b)

    for class_dir in class_dirs:
        folder_name = class_dir.name
        images = sorted(class_dir.glob("*.jpg")) + sorted(class_dir.glob("*.png"))
        if not images:
            print(f"  EMPTY  {folder_name}")
            continue

        print(f"  [{folder_name}]  {len(images)} images", end="", flush=True)

        # ── Inference ─────────────────────────────────────────────────────────
        folder_idx = name_to_idx.get(folder_name)
        if folder_idx is None:
            print(f"  WARNING: '{folder_name}' not in model classes — skipping inference")
        else:
            results = model.predict(
                [str(p) for p in images],
                verbose=False,
                imgsz=224,
            )
            for img_path, result in zip(images, results):
                probs     = result.probs
                top_idx   = int(probs.top1)
                top_conf  = float(probs.top1conf)
                top_name  = idx_to_name[top_idx]

                if top_idx != folder_idx:
                    wrong_class.append((folder_name, img_path.name, top_name, top_conf))
                elif top_conf < MIN_CONF:
                    low_conf.append((folder_name, img_path.name, top_name, top_conf))

        # ── Duplicate detection ───────────────────────────────────────────────
        if HAS_HASH and len(images) > 1:
            hashes: list[tuple[Path, object]] = []
            for img_path in images:
                try:
                    h = imagehash.phash(Image.open(img_path), hash_size=HASH_BITS)
                    hashes.append((img_path, h))
                except Exception:
                    pass

            seen: set[str] = set()
            for i, (pa, ha) in enumerate(hashes):
                for pb, hb in hashes[i+1:]:
                    if (pa.name, pb.name) in seen:
                        continue
                    if abs(ha - hb) <= HASH_DIST:
                        duplicates.append((folder_name, pa.name, pb.name))
                        seen.add((pa.name, pb.name))

        print(f"  ✓")

    # ── Write report ──────────────────────────────────────────────────────────
    report_path = Path("audit_report.txt")
    delete_path = Path("audit_delete.py")

    total_flagged = len(wrong_class) + len(low_conf) + len(duplicates)
    print(f"\nFlagged: {len(wrong_class)} wrong-class  |  {len(low_conf)} low-conf  |  {len(duplicates)} duplicates")
    print(f"Writing {report_path} …")

    with open(report_path, "w", encoding="utf-8") as f:
        f.write(f"Val audit report\n")
        f.write(f"Model : {MODEL_PATH}\n")
        f.write(f"Total flagged: {total_flagged}\n")
        f.write("=" * 80 + "\n\n")

        f.write(f"WRONG CLASS ({len(wrong_class)} images)\n")
        f.write("-" * 60 + "\n")
        for cls, fn, pred, conf in sorted(wrong_class):
            f.write(f"  {cls}/{fn}  →  predicted={pred}  conf={conf:.2f}\n")

        f.write(f"\nLOW CONFIDENCE ({len(low_conf)} images, conf < {MIN_CONF})\n")
        f.write("-" * 60 + "\n")
        for cls, fn, pred, conf in sorted(low_conf):
            f.write(f"  {cls}/{fn}  conf={conf:.2f}\n")

        f.write(f"\nNEAR-DUPLICATES ({len(duplicates)} pairs)\n")
        f.write("-" * 60 + "\n")
        for cls, fa, fb in sorted(duplicates):
            f.write(f"  {cls}/{fa}  ≈  {cls}/{fb}\n")

    # ── Write deletion script ──────────────────────────────────────────────────
    # Auto-include wrong-class images (high confidence they're wrong).
    # Duplicates: keep the first file, mark second for deletion.
    # Low-conf: listed in report but NOT auto-added (need manual review).
    auto_delete: dict[str, set[str]] = defaultdict(set)

    for cls, fn, pred, conf in wrong_class:
        if conf >= 0.60:   # high-confidence wrong-class = safe to auto-delete
            auto_delete[cls].add(fn)

    for cls, fa, fb in duplicates:
        auto_delete[cls].add(fb)  # keep fa, delete fb

    print(f"Writing {delete_path}  ({sum(len(v) for v in auto_delete.values())} auto-safe deletions) …")

    with open(delete_path, "w", encoding="utf-8") as f:
        f.write('"""Auto-generated by audit_val_with_model.py\n')
        f.write('Review audit_report.txt before running.\n')
        f.write('Low-confidence images are NOT included — add manually after review.\n"""\n\n')
        f.write("from pathlib import Path\n\n")
        f.write(f'VAL = Path(r"{VAL_DIR}")\n\n')
        f.write("BAD_IMAGES = {\n")
        for cls in sorted(auto_delete):
            f.write(f'    "{cls}": [\n')
            for fn in sorted(auto_delete[cls]):
                f.write(f'        "{fn}",\n')
            f.write("    ],\n")
        f.write("}\n\n")
        f.write("deleted = not_found = 0\n")
        f.write("for cls, files in BAD_IMAGES.items():\n")
        f.write("    for fn in files:\n")
        f.write("        p = VAL / cls / fn\n")
        f.write("        if p.exists(): p.unlink(); print(f'DELETED {cls}/{fn}'); deleted += 1\n")
        f.write("        else: print(f'MISSING {cls}/{fn}'); not_found += 1\n")
        f.write("print(f'\\nDeleted: {deleted}  Not found: {not_found}')\n")

    print(f"\nDone. Review audit_report.txt, then run: python audit_delete.py")


if __name__ == "__main__":
    run_audit()
