# Copyright © 2026 Mahmoud Triki (W2069987), University of Westminster. All rights reserved.
"""
dataset_builder.py — Download, stage, augment, and train the Smart Tool
Recognition YOLOv8n-cls model via a 2-phase pipeline.

CLI subcommands
───────────────
  python dataset_builder.py download          # pull all public datasets
  python dataset_builder.py augment           # augment the 184-class training set
  python dataset_builder.py train-full        # download + stage + augment + phase1 + phase2
  python dataset_builder.py train-finetune    # augment + phase2 (skip download & phase1)
  python dataset_builder.py summary           # print dataset counts and exit

Global options (work on every subcommand):
  --no-kaggle            skip Kaggle downloads
  --no-roboflow          skip Roboflow downloads
  --no-augment           skip in-place augmentation of the 25-class set
  --aug-multiplier N     copies per image (default: 5)
  --split R              train ratio when building pretrain set (default: 0.8)
  --roboflow-key KEY     override ROBOFLOW_API_KEY env var
  --epochs-pretrain N    phase-1 epochs (default: 30)
  --epochs-finetune N    phase-2 epochs (default: 50)

Dependencies:
    pip install kaggle roboflow albumentations pillow tqdm pyyaml python-dotenv

Kaggle credentials:  ~/.kaggle/kaggle.json  OR  KAGGLE_CONFIG_DIR env var
Roboflow credentials: ROBOFLOW_API_KEY env var  OR  --roboflow-key
"""

from __future__ import annotations

import argparse
import logging
import os
import random
import re
import shutil
from pathlib import Path
from typing import Callable, Optional

import yaml
from dotenv import load_dotenv
from PIL import Image
from tqdm import tqdm

load_dotenv()

# ── Paths ──────────────────────────────────────────────────────────────────────
SERVICES_DIR = Path(__file__).parent

# Public-dataset workspace
BASE_DIR     = Path(r"E:\photo coliction\public_datasets")
RAW_DIR      = BASE_DIR / "raw"
STAGED_DIR   = BASE_DIR / "staged"
AUG_DIR      = BASE_DIR / "augmented"       # staged augmentation output
GENERIC_DIR  = STAGED_DIR / "generic_fasteners"
SIZED_DIR    = STAGED_DIR / "sized_fasteners"
PRETRAIN_DIR = BASE_DIR / "pretrain_dataset" # temp Phase-1 dataset

# Model weights
RUNS_DIR            = SERVICES_DIR / "runs"
WEIGHTS_DIR         = SERVICES_DIR / "ultralytics"
BASE_MODEL          = "yolov8n-cls.pt"
YOLO11_MODEL        = "yolo11s-cls.pt"   # YOLO11 small classifier
PRETRAINED_WEIGHTS  = WEIGHTS_DIR / "pretrained_fastener.pt"
FINAL_WEIGHTS       = WEIGHTS_DIR / "best.pt"
TYPE_WEIGHTS        = WEIGHTS_DIR / "type_classifier.pt"  # 152-class type model

# 25-class training dataset
TRAIN_DATASET = Path(r"E:\photo coliction\dataset")

# YOLO11 parent-class dataset (17 diameter classes — superseded)
YOLO11_PARENT_DATASET = BASE_DIR / "parent_dataset"

# YOLO11 type-classifier dataset (152 product-type classes — current strategy)
# Populated by image_downloader.py
YOLO11_TYPE_DATASET = Path(r"E:\photo coliction\type_dataset")

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff"}

# ── Size classes (184 unique labels, M4–M39) ─────────────────────────────────
# Derived from products_rows.csv via `python services/extract_skus.py`
# Each entry maps to a training folder under TRAIN_DATASET/train/{label}/
SIZED_CLASSES = {
    # M4 — 7 sizes
    "4mm_10mm", "4mm_16mm", "4mm_20mm", "4mm_25mm", "4mm_30mm",
    "4mm_40mm", "4mm_50mm",
    # M5 — 7 sizes
    "5mm_10mm", "5mm_16mm", "5mm_20mm", "5mm_25mm", "5mm_30mm",
    "5mm_40mm", "5mm_50mm",
    # M6 — 12 sizes
    "6mm_12mm", "6mm_16mm", "6mm_20mm", "6mm_25mm", "6mm_30mm",
    "6mm_40mm", "6mm_50mm", "6mm_60mm", "6mm_70mm", "6mm_80mm",
    "6mm_100mm", "6mm_120mm",
    # M8 — 12 sizes
    "8mm_16mm", "8mm_20mm", "8mm_25mm", "8mm_30mm", "8mm_40mm",
    "8mm_50mm", "8mm_60mm", "8mm_70mm", "8mm_80mm",
    "8mm_100mm", "8mm_120mm", "8mm_150mm",
    # M10 — 16 sizes
    "10mm_16mm", "10mm_20mm", "10mm_25mm", "10mm_30mm", "10mm_40mm",
    "10mm_45mm", "10mm_50mm", "10mm_60mm", "10mm_70mm", "10mm_80mm",
    "10mm_90mm", "10mm_100mm", "10mm_120mm", "10mm_140mm",
    "10mm_150mm", "10mm_160mm",
    # M12 — 16 sizes
    "12mm_20mm", "12mm_25mm", "12mm_30mm", "12mm_40mm", "12mm_45mm",
    "12mm_50mm", "12mm_60mm", "12mm_70mm", "12mm_80mm", "12mm_90mm",
    "12mm_100mm", "12mm_120mm", "12mm_140mm", "12mm_150mm",
    "12mm_160mm", "12mm_180mm",
    # M14 — 18 sizes
    "14mm_25mm", "14mm_30mm", "14mm_35mm", "14mm_40mm", "14mm_45mm",
    "14mm_50mm", "14mm_60mm", "14mm_70mm", "14mm_80mm", "14mm_90mm",
    "14mm_100mm", "14mm_120mm", "14mm_140mm", "14mm_150mm",
    "14mm_160mm", "14mm_180mm", "14mm_200mm", "14mm_220mm",
    # M16 — 22 sizes
    "16mm_25mm", "16mm_30mm", "16mm_35mm", "16mm_40mm", "16mm_45mm",
    "16mm_50mm", "16mm_55mm", "16mm_60mm", "16mm_70mm", "16mm_80mm",
    "16mm_90mm", "16mm_100mm", "16mm_120mm", "16mm_130mm",
    "16mm_140mm", "16mm_150mm", "16mm_160mm", "16mm_180mm",
    "16mm_200mm", "16mm_220mm", "16mm_240mm", "16mm_260mm",
    # M18 — 12 sizes
    "18mm_40mm", "18mm_50mm", "18mm_60mm", "18mm_70mm", "18mm_80mm",
    "18mm_90mm", "18mm_100mm", "18mm_120mm", "18mm_140mm",
    "18mm_160mm", "18mm_180mm", "18mm_200mm",
    # M20 — 17 sizes
    "20mm_40mm", "20mm_50mm", "20mm_60mm", "20mm_70mm", "20mm_80mm",
    "20mm_90mm", "20mm_100mm", "20mm_110mm", "20mm_120mm",
    "20mm_130mm", "20mm_140mm", "20mm_150mm", "20mm_160mm",
    "20mm_180mm", "20mm_200mm", "20mm_220mm", "20mm_240mm",
    # M22 — 10 sizes
    "22mm_50mm", "22mm_60mm", "22mm_70mm", "22mm_80mm", "22mm_90mm",
    "22mm_100mm", "22mm_120mm", "22mm_140mm", "22mm_160mm", "22mm_180mm",
    # M24 — 13 sizes
    "24mm_50mm", "24mm_60mm", "24mm_70mm", "24mm_80mm", "24mm_90mm",
    "24mm_100mm", "24mm_120mm", "24mm_140mm", "24mm_160mm",
    "24mm_180mm", "24mm_200mm", "24mm_220mm", "24mm_260mm",
    # M27 — 10 sizes
    "27mm_60mm", "27mm_70mm", "27mm_80mm", "27mm_100mm", "27mm_120mm",
    "27mm_130mm", "27mm_140mm", "27mm_160mm", "27mm_220mm", "27mm_280mm",
    # M30 — 12 sizes
    "30mm_60mm", "30mm_70mm", "30mm_80mm", "30mm_90mm", "30mm_100mm",
    "30mm_120mm", "30mm_130mm", "30mm_140mm", "30mm_150mm",
    "30mm_160mm", "30mm_180mm", "30mm_200mm",
    # M33 — 7 sizes
    "33mm_100mm", "33mm_120mm", "33mm_140mm", "33mm_180mm",
    "33mm_200mm", "33mm_220mm", "33mm_250mm",
    # M36 — 2 sizes
    "36mm_120mm", "36mm_160mm",
    # M39 — 1 size
    "39mm_160mm",
}

# ── YOLO11 parent classes (diameter-based, 17 classes) ───────────────────────
# Key insight: bolt DIAMETER is visually learnable from photos — a 27mm bolt is
# visually much larger than an 8mm bolt. Length is NOT learnable without scale.
# The new model learns diameter; ArUco / ruler measures length.
# After retraining, `/detect` returns parent_class → API returns all size variants.
DIAMETER_TO_CLASS: dict[int, str] = {
    4:  "bolt_M4",   5:  "bolt_M5",   6:  "bolt_M6",
    8:  "bolt_M8",   10: "bolt_M10",  12: "bolt_M12",
    14: "bolt_M14",  16: "bolt_M16",  18: "bolt_M18",
    20: "bolt_M20",  22: "bolt_M22",  24: "bolt_M24",
    27: "bolt_M27",  30: "bolt_M30",  33: "bolt_M33",
    36: "bolt_M36",  39: "bolt_M39",
}
PARENT_CLASSES: set[str] = set(DIAMETER_TO_CLASS.values())

# Phase-1 broad categories
BROAD_CLASSES = {"screw", "bolt", "nut", "washer", "other"}

BROAD_KEYWORDS: dict[str, list[str]] = {
    "screw":  ["screw", "vis", "schraube", "tornillo", "philips",
               "flathead", "countersink", "torx", "hex_socket"],
    "bolt":   ["bolt", "stud", "hexhead", "hex_head", "carriage",
               "machine_bolt", "boulon"],
    "nut":    ["nut", "hexnut", "locknut", "lock_nut", "ecrou", "mutter"],
    "washer": ["washer", "rondelle", "scheibe", "ring"],
}

# ── Kaggle / Roboflow sources ─────────────────────────────────────────────────
KAGGLE_DATASETS = [
    "wjybuqi/screwwasher-dataset-for-small-object-detection",
    "ipythonx/mvtec-screws",
    "yartinz/npu-bolt",
    "sujan97/screws-and-nuts-image",
    "alexandrparkhomenko/the-fasteners",
    "manikantanrnair/images-of-mechanical-parts-boltnut-washerpin",
]

ROBOFLOW_PROJECTS = [
    {"workspace": "automated-disassembly", "project": "fastener-object-detection", "version": 1},
    {"workspace": "testworkspace-z10xl",   "project": "bolt-and-nuts-detection",   "version": 1},
]


# ── Logging ────────────────────────────────────────────────────────────────────

LOG_FILE = RUNS_DIR / "dataset_builder_log.txt"

def _setup_logging():
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    fmt = "%(asctime)s  %(levelname)-8s  %(message)s"
    logging.basicConfig(
        level=logging.INFO,
        format=fmt,
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.FileHandler(str(LOG_FILE), encoding="utf-8"),
            logging.StreamHandler(),
        ],
        force=True,
    )

log = logging.getLogger(__name__)


# ── Label utilities ────────────────────────────────────────────────────────────

def _normalize_label(raw: str) -> Optional[str]:
    """
    Map an arbitrary folder / class name to one of the 25 size classes.
    Accepts: m4x16, m4_16, 4x16, 4mm_16mm, 4mm-16mm, etc.
    Returns None when no match.
    """
    s = raw.lower().strip().replace(" ", "_")
    if s in SIZED_CLASSES:
        return s
    m = re.search(r"(?:m)?([456])(?:mm)?[x_\-](\d{2,3})(?:mm)?", s)
    if m:
        candidate = f"{m.group(1)}mm_{m.group(2)}mm"
        if candidate in SIZED_CLASSES:
            return candidate
    return None


def _broad_category(label: str) -> str:
    """Map a label to one of: screw, bolt, nut, washer, other."""
    # All sized M4/M5/M6 screws → screw
    if label in SIZED_CLASSES or _normalize_label(label) is not None:
        return "screw"
    low = label.lower()
    for cat, keywords in BROAD_KEYWORDS.items():
        if any(kw in low for kw in keywords):
            return cat
    return "other"


# ── Directory helpers ──────────────────────────────────────────────────────────

def setup_dirs():
    for d in [RAW_DIR, GENERIC_DIR, SIZED_DIR, AUG_DIR, RUNS_DIR, WEIGHTS_DIR]:
        d.mkdir(parents=True, exist_ok=True)
    log.info("Output root: %s", BASE_DIR)


def _copy_image(src: Path, dst: Path):
    """Copy src → dst as JPEG, resized to 640×640 max. No-ops if dst exists."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists():
        return
    try:
        img = Image.open(src).convert("RGB")
        img.thumbnail((640, 640), Image.LANCZOS)
        img.save(str(dst.with_suffix(".jpg")), "JPEG", quality=92)
    except Exception as exc:
        log.warning("Could not convert %s: %s", src.name, exc)


# ── Downloads ──────────────────────────────────────────────────────────────────

def download_kaggle_datasets(datasets: list[str] = KAGGLE_DATASETS):
    try:
        from kaggle.api.kaggle_api_extended import KaggleApiExtended
        api = KaggleApiExtended()
        api.authenticate()
    except Exception as exc:
        log.warning("[kaggle] Cannot authenticate — skipping. %s", exc)
        return

    for slug in datasets:
        _, name = slug.split("/")
        dest = RAW_DIR / "kaggle" / name
        if dest.exists() and any(dest.rglob("*")):
            log.info("[kaggle] %s — already cached, skipping.", slug)
            continue
        dest.mkdir(parents=True, exist_ok=True)
        log.info("[kaggle] Downloading %s …", slug)
        try:
            api.dataset_download_files(slug, path=str(dest), unzip=True, quiet=False)
            log.info("[kaggle] %s — done (%s)", slug, dest)
        except Exception as exc:
            log.error("[kaggle] %s — FAILED: %s", slug, exc)
            shutil.rmtree(dest, ignore_errors=True)


def download_roboflow_datasets(projects: list[dict] = ROBOFLOW_PROJECTS,
                               api_key: str = ""):
    if not api_key:
        log.warning("[roboflow] No API key — skipping.")
        return
    try:
        from roboflow import Roboflow
    except ImportError:
        log.warning("[roboflow] `roboflow` package not installed — skipping.")
        return

    rf = Roboflow(api_key=api_key)
    for proj in projects:
        ws, name, ver = proj["workspace"], proj["project"], proj["version"]
        dest = RAW_DIR / "roboflow" / f"{ws}_{name}_v{ver}"
        if dest.exists() and any(dest.rglob("*.jpg")):
            log.info("[roboflow] %s/%s v%s — already cached, skipping.", ws, name, ver)
            continue
        dest.mkdir(parents=True, exist_ok=True)
        log.info("[roboflow] Downloading %s/%s v%s …", ws, name, ver)
        try:
            dataset = rf.workspace(ws).project(name).version(ver).download(
                "yolov8", location=str(dest)
            )
            log.info("[roboflow] %s — done (%s)", name, dest)
        except Exception as exc:
            log.error("[roboflow] %s/%s v%s — FAILED: %s", ws, name, ver, exc)
            shutil.rmtree(dest, ignore_errors=True)


# ── Staging ────────────────────────────────────────────────────────────────────

def _load_class_names(dataset_root: Path) -> dict[int, str]:
    for yaml_file in ["data.yaml", "dataset.yaml", "classes.yaml"]:
        p = dataset_root / yaml_file
        if p.exists():
            with open(p) as f:
                data = yaml.safe_load(f)
            names = data.get("names", {})
            if isinstance(names, list):
                return {i: n for i, n in enumerate(names)}
            if isinstance(names, dict):
                return {int(k): v for k, v in names.items()}
    return {}


def _stage_classification_tree(source_root: Path, source_name: str) -> dict:
    counts = {"generic": 0, "sized": 0}
    pairs: list[tuple[Path, str]] = [
        (img, img.parent.name)
        for img in source_root.rglob("*")
        if img.suffix.lower() in IMAGE_EXTS
        and img.parent.name.lower() != "images"
    ]
    for img, raw_label in tqdm(pairs, desc=f"  staging {source_name}", unit="img"):
        normalized = _normalize_label(raw_label)
        if normalized:
            _copy_image(img, SIZED_DIR / normalized / f"{source_name}_{img.stem}.jpg")
            counts["sized"] += 1
        else:
            safe = re.sub(r"[^\w]", "_", raw_label.lower())
            _copy_image(img, GENERIC_DIR / safe / f"{source_name}_{img.stem}.jpg")
            counts["generic"] += 1
    return counts


def _stage_detection_dataset(source_root: Path, source_name: str) -> dict:
    counts = {"generic": 0, "sized": 0}
    class_names = _load_class_names(source_root)
    if not class_names:
        log.warning("  No class names found in %s, treating all as generic.", source_root.name)

    image_paths = (
        list(source_root.rglob("images/*.jpg"))
        + list(source_root.rglob("images/*.png"))
    )

    for img in tqdm(image_paths, desc=f"  staging {source_name}", unit="img"):
        label_file = Path(str(img).replace("images", "labels")).with_suffix(".txt")
        dominant_label = "unknown"
        if label_file.exists() and class_names:
            try:
                cls_counts: dict[int, int] = {}
                for line in label_file.read_text().splitlines():
                    parts = line.strip().split()
                    if parts:
                        cid = int(parts[0])
                        cls_counts[cid] = cls_counts.get(cid, 0) + 1
                if cls_counts:
                    dominant_id = max(cls_counts, key=lambda k: cls_counts[k])
                    dominant_label = class_names.get(dominant_id, "unknown")
            except Exception:
                pass

        normalized = _normalize_label(dominant_label)
        if normalized:
            _copy_image(img, SIZED_DIR / normalized / f"{source_name}_{img.stem}.jpg")
            counts["sized"] += 1
        else:
            safe = re.sub(r"[^\w]", "_", dominant_label.lower())
            _copy_image(img, GENERIC_DIR / safe / f"{source_name}_{img.stem}.jpg")
            counts["generic"] += 1
    return counts


def _is_detection_dataset(root: Path) -> bool:
    return any(root.glob("*.yaml")) and any(root.rglob("images/"))


def stage_all_downloads():
    total = {"generic": 0, "sized": 0}
    for source_dir in sorted(RAW_DIR.rglob("*")):
        if not source_dir.is_dir():
            continue
        rel = source_dir.relative_to(RAW_DIR)
        if len(rel.parts) != 2:
            continue
        if not any(source_dir.rglob(f"*{ext}") for ext in IMAGE_EXTS):
            continue
        source_name = rel.parts[1]
        log.info("[stage] Processing: %s", source_name)
        if _is_detection_dataset(source_dir):
            counts = _stage_detection_dataset(source_dir, source_name)
        else:
            counts = _stage_classification_tree(source_dir, source_name)
        log.info("  → generic: %d  sized: %d", counts["generic"], counts["sized"])
        total["generic"] += counts["generic"]
        total["sized"]   += counts["sized"]
    log.info("[stage] Total — generic: %d, sized: %d", total["generic"], total["sized"])
    return total


# ── Phase 1 — build broad-category dataset ────────────────────────────────────

def build_pretrain_dataset(train_ratio: float = 0.8) -> Path:
    """
    Collect ALL staged images (generic + sized), map them to 5 broad classes
    (screw / bolt / nut / washer / other), and write a clean train/val split
    to PRETRAIN_DIR.  Existing files are never overwritten.

    Returns the PRETRAIN_DIR path (suitable as YOLO data= argument).
    """
    log.info("[phase1] Building pre-training dataset in %s", PRETRAIN_DIR)
    rng = random.Random(0)

    # Gather all images from both staged trees
    all_images: list[tuple[Path, str]] = []

    for root, tag in [(SIZED_DIR, "sized"), (GENERIC_DIR, "generic")]:
        if not root.exists():
            continue
        for class_dir in root.iterdir():
            if not class_dir.is_dir():
                continue
            category = _broad_category(class_dir.name)
            imgs = [p for p in class_dir.iterdir() if p.suffix.lower() in IMAGE_EXTS]
            for img in imgs:
                all_images.append((img, category))

    if not all_images:
        log.warning("[phase1] No staged images found — run 'download' first.")
        return PRETRAIN_DIR

    # Count per broad class
    class_counts: dict[str, int] = {}
    for _, cat in all_images:
        class_counts[cat] = class_counts.get(cat, 0) + 1
    for cat, n in sorted(class_counts.items()):
        log.info("  %s: %d images", cat, n)

    # Copy with train/val split
    rng.shuffle(all_images)
    split_idx = int(len(all_images) * train_ratio)
    splits = {"train": all_images[:split_idx], "val": all_images[split_idx:]}

    for split, items in splits.items():
        for img, cat in tqdm(items, desc=f"  copying {split}", unit="img"):
            dst = PRETRAIN_DIR / split / cat / img.name
            _copy_image(img, dst)

    total_train = sum(
        1 for p in (PRETRAIN_DIR / "train").rglob("*")
        if p.suffix.lower() in IMAGE_EXTS
    ) if (PRETRAIN_DIR / "train").exists() else 0
    total_val = sum(
        1 for p in (PRETRAIN_DIR / "val").rglob("*")
        if p.suffix.lower() in IMAGE_EXTS
    ) if (PRETRAIN_DIR / "val").exists() else 0
    log.info("[phase1] Dataset ready — train: %d  val: %d", total_train, total_val)
    return PRETRAIN_DIR


def run_phase1(
    epochs: int = 30,
    on_epoch_end: Optional[Callable] = None,
) -> Path:
    """
    Train YOLOv8n-cls on 5 broad categories.
    Saves weights to PRETRAINED_WEIGHTS.
    Returns the path to the saved weights.
    """
    if not PRETRAIN_DIR.exists() or not any(PRETRAIN_DIR.rglob("*.jpg")):
        raise RuntimeError(
            "Pre-training dataset not found. Run build_pretrain_dataset() first."
        )

    log.info("[phase1] Starting pre-training: %d epochs, imgsz=224", epochs)
    log.info("[phase1] Dataset: %s", PRETRAIN_DIR)

    try:
        from ultralytics import YOLO
    except ImportError:
        raise RuntimeError("ultralytics not installed — pip install ultralytics")

    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    WEIGHTS_DIR.mkdir(parents=True, exist_ok=True)

    model = YOLO(BASE_MODEL)

    if on_epoch_end:
        model.add_callback("on_train_epoch_end", on_epoch_end)
    else:
        def _log_epoch(trainer):
            ep  = trainer.epoch + 1
            acc = round(float(trainer.metrics.get("metrics/accuracy_top1", 0)), 4)
            log.info("[phase1] Epoch %d/%d — top1_acc: %.4f", ep, epochs, acc)
        model.add_callback("on_train_epoch_end", _log_epoch)

    model.train(
        data=str(PRETRAIN_DIR),
        epochs=epochs,
        imgsz=224,
        project=str(RUNS_DIR),
        name="pretrain_fastener",
        exist_ok=True,
        verbose=False,
    )

    best_src = RUNS_DIR / "pretrain_fastener" / "weights" / "best.pt"
    if not best_src.exists():
        raise RuntimeError(f"Expected weights not found at {best_src}")

    shutil.copy2(best_src, PRETRAINED_WEIGHTS)
    log.info("[phase1] Pre-trained weights saved to %s", PRETRAINED_WEIGHTS)
    return PRETRAINED_WEIGHTS


# ── Phase 2 — in-place augmentation of the 25-class training set ──────────────

def _build_finetune_transform():
    """Build albumentations transform matching the Phase-2 spec."""
    import albumentations as A
    return A.Compose([
        # Full 360° rotation
        A.Rotate(limit=180, border_mode=0, p=1.0),
        # Brightness / contrast ±20 %
        A.RandomBrightnessContrast(brightness_limit=0.2, contrast_limit=0.2, p=0.8),
        # Horizontal flip
        A.HorizontalFlip(p=0.5),
        # Scale 0.8×–1.2× (crop to original size after)
        A.RandomScale(scale_limit=0.2, p=0.8),
        A.PadIfNeeded(min_height=224, min_width=224,
                      border_mode=0, p=1.0),
        A.CenterCrop(height=224, width=224, p=1.0),
        # Slight Gaussian blur to simulate camera focus variation
        A.GaussianBlur(blur_limit=(3, 7), p=0.3),
    ])


def _finetune_augment_pil(img: Image.Image, rng: random.Random) -> Image.Image:
    """PIL-only fallback for Phase-2 augmentation."""
    import PIL.ImageEnhance as E
    import PIL.ImageFilter  as F

    # Full 360° rotation
    angle = rng.uniform(0, 360)
    img = img.rotate(angle, expand=False, fillcolor=(0, 0, 0))

    # Horizontal flip
    if rng.random() < 0.5:
        img = img.transpose(Image.FLIP_LEFT_RIGHT)

    # Brightness / contrast ±20 %
    img = E.Brightness(img).enhance(rng.uniform(0.8, 1.2))
    img = E.Contrast(img).enhance(rng.uniform(0.8, 1.2))

    # Scale 0.8×–1.2×
    factor = rng.uniform(0.8, 1.2)
    new_w = max(1, int(img.width * factor))
    new_h = max(1, int(img.height * factor))
    img = img.resize((new_w, new_h), Image.LANCZOS)
    # Crop / pad back to original size
    orig_w, orig_h = 224, 224
    img = img.crop((0, 0, orig_w, orig_h)) if factor > 1 else img.resize(
        (orig_w, orig_h), Image.LANCZOS
    )

    # Slight Gaussian blur
    if rng.random() < 0.3:
        img = img.filter(F.GaussianBlur(radius=rng.uniform(0.5, 1.5)))

    return img


def augment_training_dataset(multiplier: int = 5) -> int:
    """
    Augment the 25-class training set **in-place** (train split only).

    For each original image (those NOT already tagged _augN), generate
    `multiplier` copies saved alongside the original as:
        <stem>_aug0.jpg … <stem>_aug{N-1}.jpg

    Idempotent: skips images where all aug copies already exist.
    Returns the number of new images written.
    """
    train_dir = TRAIN_DATASET / "train"
    if not train_dir.exists():
        log.warning("[augment] Training dir not found: %s", train_dir)
        return 0

    try:
        import numpy as np
        transform = _build_finetune_transform()
        use_albu  = True
        log.info("[augment] Using albumentations.")
    except ImportError:
        transform = None
        use_albu  = False
        log.info("[augment] albumentations not found — using PIL fallback.")

    rng = random.Random(42)

    # Collect originals only (skip files already tagged _aug)
    originals = [
        p for p in train_dir.rglob("*")
        if p.suffix.lower() in IMAGE_EXTS
        and "_aug" not in p.stem
    ]

    log.info(
        "[augment] %d original images × %d = up to %d new images.",
        len(originals), multiplier, len(originals) * multiplier,
    )

    generated = 0
    for img_path in tqdm(originals, desc="[augment] phase2", unit="img"):
        try:
            pil_img = Image.open(img_path).convert("RGB")
        except Exception as exc:
            log.warning("  Cannot open %s: %s", img_path.name, exc)
            continue

        for i in range(multiplier):
            dst = img_path.parent / f"{img_path.stem}_aug{i}.jpg"
            if dst.exists():
                continue
            try:
                if use_albu:
                    import numpy as np
                    arr = np.array(pil_img)
                    result = Image.fromarray(transform(image=arr)["image"])
                else:
                    result = _finetune_augment_pil(pil_img.copy(), rng)
                result.save(str(dst), "JPEG", quality=92)
                generated += 1
            except Exception as exc:
                log.warning("  Augmentation failed for %s: %s", img_path.name, exc)

    log.info("[augment] Done — %d new images written into %s", generated, train_dir)
    return generated


# ── Phase 2 — fine-tuning on 25 classes ───────────────────────────────────────

def run_phase2(
    epochs: int = 50,
    on_epoch_end: Optional[Callable] = None,
) -> Path:
    """
    Fine-tune on the 25-class screw dataset.

    Uses PRETRAINED_WEIGHTS if it exists, otherwise falls back to yolov8n-cls.pt.
    Saves the best weights to FINAL_WEIGHTS (ultralytics/best.pt).
    Returns path to saved weights.
    """
    if not TRAIN_DATASET.exists():
        raise RuntimeError(f"Training dataset not found: {TRAIN_DATASET}")

    weights_src = str(PRETRAINED_WEIGHTS) if PRETRAINED_WEIGHTS.exists() else BASE_MODEL
    log.info("[phase2] Starting fine-tuning: %d epochs, imgsz=224", epochs)
    log.info("[phase2] Base weights: %s", weights_src)
    log.info("[phase2] Dataset: %s", TRAIN_DATASET)

    try:
        from ultralytics import YOLO
    except ImportError:
        raise RuntimeError("ultralytics not installed — pip install ultralytics")

    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    WEIGHTS_DIR.mkdir(parents=True, exist_ok=True)

    model = YOLO(weights_src)

    if on_epoch_end:
        model.add_callback("on_train_epoch_end", on_epoch_end)
    else:
        def _log_epoch(trainer):
            ep  = trainer.epoch + 1
            acc = round(float(trainer.metrics.get("metrics/accuracy_top1", 0)), 4)
            log.info("[phase2] Epoch %d/%d — top1_acc: %.4f", ep, epochs, acc)
        model.add_callback("on_train_epoch_end", _log_epoch)

    model.train(
        data=str(TRAIN_DATASET),
        epochs=epochs,
        imgsz=224,
        project=str(RUNS_DIR),
        name="screw_classifier",
        exist_ok=True,
        verbose=False,
    )

    best_src = RUNS_DIR / "screw_classifier" / "weights" / "best.pt"
    if not best_src.exists():
        raise RuntimeError(f"Expected weights not found at {best_src}")

    shutil.copy2(best_src, FINAL_WEIGHTS)
    log.info("[phase2] Fine-tuned weights saved to %s", FINAL_WEIGHTS)
    return FINAL_WEIGHTS


# ── Staged augmentation (public datasets → AUG_DIR) ───────────────────────────

def _build_staged_transform():
    import albumentations as A
    return A.Compose([
        A.RandomRotate90(p=0.5),
        A.Rotate(limit=30, p=0.7),
        A.HorizontalFlip(p=0.5),
        A.VerticalFlip(p=0.3),
        A.ShiftScaleRotate(shift_limit=0.1, scale_limit=0.2, rotate_limit=20, p=0.5),
        A.RandomBrightnessContrast(brightness_limit=0.3, contrast_limit=0.3, p=0.6),
        A.HueSaturationValue(hue_shift_limit=10, sat_shift_limit=20,
                             val_shift_limit=20, p=0.4),
        A.GaussNoise(var_limit=(10.0, 50.0), p=0.3),
        A.GaussianBlur(blur_limit=(3, 5), p=0.2),
        A.CLAHE(clip_limit=2.0, p=0.3),
        A.ImageCompression(quality_lower=75, quality_upper=100, p=0.2),
    ])


def augment_staged(multiplier: int = 3) -> int:
    """Augment SIZED_DIR → AUG_DIR (generic images are skipped)."""
    try:
        transform = _build_staged_transform()
        import numpy as np
        use_albu = True
        log.info("[augment-staged] Using albumentations.")
    except ImportError:
        transform = None
        use_albu  = False
        log.info("[augment-staged] albumentations not found — using PIL fallback.")

    rng = random.Random(42)
    all_images = [p for p in SIZED_DIR.rglob("*") if p.suffix.lower() in IMAGE_EXTS]
    log.info("[augment-staged] %d source images × %d", len(all_images), multiplier)

    generated = 0
    for img_path in tqdm(all_images, desc="[augment-staged]", unit="img"):
        rel = img_path.relative_to(SIZED_DIR)
        try:
            pil_img = Image.open(img_path).convert("RGB")
        except Exception as exc:
            log.warning("  Cannot open %s: %s", img_path.name, exc)
            continue

        for i in range(multiplier):
            dst = AUG_DIR / rel.parent / f"{img_path.stem}_aug{i}.jpg"
            if dst.exists():
                continue
            dst.parent.mkdir(parents=True, exist_ok=True)
            try:
                if use_albu:
                    import numpy as np
                    arr = np.array(pil_img)
                    result = Image.fromarray(transform(image=arr)["image"])
                else:
                    result = _finetune_augment_pil(pil_img.copy(), rng)
                result.save(str(dst), "JPEG", quality=92)
                generated += 1
            except Exception as exc:
                log.warning("  Augmentation failed for %s: %s", img_path.name, exc)

    log.info("[augment-staged] Done — %d images written to %s", generated, AUG_DIR)
    return generated


# ── Merge staged images into training dataset ─────────────────────────────────

def merge_to_training(train_ratio: float = 0.8, use_augmented: bool = True):
    """Copy sized (and optionally augmented) staged images into TRAIN_DATASET."""
    sources: list[Path] = [SIZED_DIR]
    if use_augmented and AUG_DIR.exists():
        sources.append(AUG_DIR)

    stats: dict[str, int] = {}
    for source_root in sources:
        for class_dir in sorted(source_root.iterdir()):
            if not class_dir.is_dir() or class_dir.name not in SIZED_CLASSES:
                continue
            images = [p for p in class_dir.iterdir() if p.suffix.lower() in IMAGE_EXTS]
            random.shuffle(images)
            split_idx = max(1, int(len(images) * train_ratio))
            for split, imgs in [("train", images[:split_idx]), ("val", images[split_idx:])]:
                for img in imgs:
                    dst = TRAIN_DATASET / split / class_dir.name / img.name
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    if not dst.exists():
                        shutil.copy2(img, dst)
                        stats[class_dir.name] = stats.get(class_dir.name, 0) + 1

    total = sum(stats.values())
    log.info("[merge] Copied %d new images into %s", total, TRAIN_DATASET)
    for cls, n in sorted(stats.items()):
        log.info("  %-16s +%d", cls, n)
    return stats


# ── YOLO11 parent-class pipeline ─────────────────────────────────────────────

def build_parent_dataset(train_ratio: float = 0.8) -> Path:
    """
    Reorganise the 184-class training set (TRAIN_DATASET) into 17 diameter-based
    parent classes in YOLO11_PARENT_DATASET.

    e.g., all images from  train/8mm_16mm/, train/8mm_20mm/, …, train/8mm_150mm/
    are copied into  parent_dataset/train/bolt_M8/

    Why 17 classes instead of 184?
      Bolt DIAMETER is visually learnable — a 27mm bolt is obviously wider than an
      8mm bolt even without a scale reference.  Length is NOT learnable: an M8×70mm
      bolt looks identical to M8×120mm in a 224px crop.  With a ruler/ArUco the API
      then measures exact length and returns the full size list to the user.
    """
    log.info("[yolo11] Building parent-class dataset → %s", YOLO11_PARENT_DATASET)

    if not TRAIN_DATASET.exists():
        raise RuntimeError(f"Source dataset not found: {TRAIN_DATASET}")

    counts: dict[str, int] = {}
    rng = random.Random(0)

    for split in ["train", "val"]:
        split_dir = TRAIN_DATASET / split
        if not split_dir.exists():
            continue
        for class_dir in sorted(split_dir.iterdir()):
            if not class_dir.is_dir():
                continue
            # Parse diameter from folder name (e.g., "8mm_70mm" → 8)
            m = re.match(r'^(\d+)mm_', class_dir.name)
            if not m:
                continue
            diameter = int(m.group(1))
            parent_class = DIAMETER_TO_CLASS.get(diameter)
            if not parent_class:
                log.warning("[yolo11]  Unknown diameter %dmm in folder %s", diameter, class_dir.name)
                continue

            images = [p for p in class_dir.iterdir() if p.suffix.lower() in IMAGE_EXTS]
            for img in images:
                # Use original split assignments from the source dataset
                dst = YOLO11_PARENT_DATASET / split / parent_class / img.name
                dst.parent.mkdir(parents=True, exist_ok=True)
                if not dst.exists():
                    _copy_image(img, dst)
                    counts[parent_class] = counts.get(parent_class, 0) + 1

    for cls in sorted(counts):
        log.info("  %-14s +%d images", cls, counts[cls])
    total = sum(counts.values())
    log.info(
        "[yolo11] Parent dataset ready — %d images across %d classes",
        total, len(counts),
    )
    return YOLO11_PARENT_DATASET


def run_yolo11_training(
    epochs: int = 100,
    imgsz: int = 640,
    on_epoch_end: Optional[Callable] = None,
) -> Path:
    """
    Train YOLO11s-cls on 17 bolt-diameter parent classes.

    Why YOLO11 over YOLOv8?
      - YOLO11 (ultralytics ≥ 8.3) features improved backbone attention blocks,
        better small-object feature extraction, and ~10% higher mAP on benchmarks.
      - Larger imgsz=640 (vs 224) lets the model see bolt-width details clearly.
      - Fewer classes (17 vs 184) means vastly more images per class and a much
        better-balanced training set.

    Saves final weights to FINAL_WEIGHTS (ultralytics/best.pt).
    """
    if not YOLO11_PARENT_DATASET.exists() or not any(YOLO11_PARENT_DATASET.rglob("*.jpg")):
        raise RuntimeError(
            "Parent dataset not found. Run build_parent_dataset() first.\n"
            "  python dataset_builder.py build-parent-dataset"
        )

    log.info("[yolo11] Starting YOLO11s-cls training: %d epochs, imgsz=%d", epochs, imgsz)
    log.info("[yolo11] Dataset  : %s", YOLO11_PARENT_DATASET)
    log.info("[yolo11] Base model: %s", YOLO11_MODEL)

    try:
        from ultralytics import YOLO
    except ImportError:
        raise RuntimeError("ultralytics not installed — pip install ultralytics")

    # Verify ultralytics version supports YOLO11
    try:
        import ultralytics
        ver = tuple(int(x) for x in ultralytics.__version__.split(".")[:2])
        if ver < (8, 3):
            log.warning(
                "[yolo11] ultralytics %s may not support YOLO11. "
                "Upgrade: pip install --upgrade ultralytics",
                ultralytics.__version__,
            )
    except Exception:
        pass

    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    WEIGHTS_DIR.mkdir(parents=True, exist_ok=True)

    model = YOLO(YOLO11_MODEL)

    if on_epoch_end:
        model.add_callback("on_train_epoch_end", on_epoch_end)
    else:
        def _log_epoch(trainer):
            ep  = trainer.epoch + 1
            acc = round(float(trainer.metrics.get("metrics/accuracy_top1", 0)), 4)
            log.info("[yolo11] Epoch %d/%d — top1_acc=%.4f", ep, epochs, acc)
        model.add_callback("on_train_epoch_end", _log_epoch)

    model.train(
        data=str(YOLO11_PARENT_DATASET),
        epochs=epochs,
        imgsz=imgsz,
        batch=16,
        project=str(RUNS_DIR),
        name="bolt_diameter_classifier",
        exist_ok=True,
        verbose=False,
    )

    best_src = RUNS_DIR / "bolt_diameter_classifier" / "weights" / "best.pt"
    if not best_src.exists():
        raise RuntimeError(f"Expected weights not found at {best_src}")

    shutil.copy2(best_src, FINAL_WEIGHTS)
    log.info("[yolo11] Weights saved → %s", FINAL_WEIGHTS)
    return FINAL_WEIGHTS


# ── YOLO11 type-classifier pipeline (152 product-type classes) ───────────────

def run_yolo11_type_training(
    epochs: int = 100,
    imgsz: int = 640,
    batch: int = 8,
    workers: int = 2,
    on_epoch_end: Optional[Callable] = None,
) -> Path:
    """
    Train YOLO11s-cls on the 152 product-type classes downloaded by
    image_downloader.py into YOLO11_TYPE_DATASET.

    Why type classes (not size classes)?
      A "hex bolt zinc DIN933" looks completely different from a "socket head
      screw DIN912" or a "wing nut DIN315" — those differences are in head
      shape, drive type, thread pattern, and coating colour.  The model learns
      TYPE reliably from web photos.  After detection the UI shows the full
      size sub-item list so the user picks the exact bolt they need.

    Saves weights to TYPE_WEIGHTS (ultralytics/type_classifier.pt).
    Returns path to saved weights.
    """
    if not YOLO11_TYPE_DATASET.exists() or not any(YOLO11_TYPE_DATASET.rglob("*.jpg")):
        raise RuntimeError(
            f"Type dataset not found: {YOLO11_TYPE_DATASET}\n"
            "  Run image_downloader.py first:\n"
            "    python image_downloader.py --per-class 60"
        )

    # Count classes and images
    train_dir = YOLO11_TYPE_DATASET / "train"
    classes   = [d.name for d in train_dir.iterdir() if d.is_dir()] if train_dir.exists() else []
    n_images  = sum(
        1 for p in train_dir.rglob("*")
        if p.suffix.lower() in IMAGE_EXTS
    ) if train_dir.exists() else 0

    log.info("[type] Starting YOLO11s-cls type training")
    log.info("[type]   Classes   : %d", len(classes))
    log.info("[type]   Images    : %d  (train split)", n_images)
    log.info("[type]   Epochs    : %d", epochs)
    log.info("[type]   imgsz     : %d", imgsz)
    log.info("[type]   Dataset   : %s", YOLO11_TYPE_DATASET)
    log.info("[type]   Base model: %s", YOLO11_MODEL)

    try:
        from ultralytics import YOLO
    except ImportError:
        raise RuntimeError("ultralytics not installed — pip install ultralytics")

    try:
        import ultralytics
        ver = tuple(int(x) for x in ultralytics.__version__.split(".")[:2])
        if ver < (8, 3):
            log.warning(
                "[type] ultralytics %s may not support YOLO11. "
                "Upgrade: pip install --upgrade ultralytics",
                ultralytics.__version__,
            )
    except Exception:
        pass

    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    WEIGHTS_DIR.mkdir(parents=True, exist_ok=True)

    model = YOLO(YOLO11_MODEL)

    if on_epoch_end:
        model.add_callback("on_train_epoch_end", on_epoch_end)
    else:
        def _log_epoch(trainer):
            ep   = trainer.epoch + 1
            top1 = round(float(trainer.metrics.get("metrics/accuracy_top1", 0)), 4)
            top5 = round(float(trainer.metrics.get("metrics/accuracy_top5", 0)), 4)
            log.info("[type] Epoch %d/%d — top1=%.4f  top5=%.4f", ep, epochs, top1, top5)
        model.add_callback("on_train_epoch_end", _log_epoch)

    model.train(
        data=str(YOLO11_TYPE_DATASET),
        epochs=epochs,
        imgsz=imgsz,
        batch=batch,
        workers=workers,
        project=str(RUNS_DIR),
        name="type_classifier",
        exist_ok=True,
        verbose=False,
    )

    best_src = RUNS_DIR / "type_classifier" / "weights" / "best.pt"
    if not best_src.exists():
        raise RuntimeError(f"Expected weights not found at {best_src}")

    shutil.copy2(best_src, TYPE_WEIGHTS)
    # Also promote to active model
    shutil.copy2(best_src, FINAL_WEIGHTS)
    log.info("[type] Weights saved → %s", TYPE_WEIGHTS)
    log.info("[type] Active model updated → %s", FINAL_WEIGHTS)
    return TYPE_WEIGHTS


# ── Summary ────────────────────────────────────────────────────────────────────

def print_summary():
    log.info("── Dataset Summary ──────────────────────────────────────────────────")
    for label, root in [
        ("staged/sized",    SIZED_DIR),
        ("staged/generic",  GENERIC_DIR),
        ("augmented",       AUG_DIR),
        ("pretrain",        PRETRAIN_DIR),
    ]:
        if not root.exists():
            continue
        total   = sum(1 for p in root.rglob("*") if p.suffix.lower() in IMAGE_EXTS)
        classes = [d.name for d in root.iterdir() if d.is_dir()]
        log.info("  %-22s %6d images  (%d classes)", label, total, len(classes))

    log.info("")
    log.info("  Training dataset (25-class):")
    for split in ["train", "val"]:
        split_dir = TRAIN_DATASET / split
        if not split_dir.exists():
            continue
        for cls_dir in sorted(split_dir.iterdir()):
            if cls_dir.is_dir():
                n = sum(1 for p in cls_dir.iterdir() if p.suffix.lower() in IMAGE_EXTS)
                log.info("    [%s] %-16s %5d images", split, cls_dir.name, n)

    log.info("────────────────────────────────────────────────────────────────────")


# ── CLI ────────────────────────────────────────────────────────────────────────

def _add_common_args(p: argparse.ArgumentParser):
    p.add_argument("--no-kaggle",       action="store_true")
    p.add_argument("--no-roboflow",     action="store_true")
    p.add_argument("--no-augment",      action="store_true",
                   help="Skip in-place augmentation of the 25-class training set.")
    p.add_argument("--aug-multiplier",  type=int,   default=5, metavar="N")
    p.add_argument("--split",           type=float, default=0.8, metavar="R")
    p.add_argument("--roboflow-key",    type=str,   default=None, metavar="KEY")
    p.add_argument("--epochs-pretrain", type=int,   default=30,  metavar="N")
    p.add_argument("--epochs-finetune", type=int,   default=50,  metavar="N")
    p.add_argument("--epochs-yolo11",   type=int,   default=100, metavar="N")
    p.add_argument("--epochs-type",     type=int,   default=100, metavar="N",
                   help="Epochs for 152-class type classifier (default: 100)")
    p.add_argument("--batch",           type=int,   default=8,  metavar="N",
                   help="Batch size for training (default: 8, lower if GPU crashes)")
    p.add_argument("--workers",         type=int,   default=2,  metavar="N",
                   help="DataLoader workers (default: 2, use 0 if OOM persists on Windows)")
    p.add_argument("--imgsz",           type=int,   default=640, metavar="PX")


def _resolve_rf_key(args) -> str:
    return args.roboflow_key or os.getenv("ROBOFLOW_API_KEY", "")


def _cmd_download(args):
    setup_dirs()
    if not args.no_kaggle:
        log.info("── Kaggle downloads ─────────────────────────────────────────────")
        download_kaggle_datasets()
    if not args.no_roboflow:
        log.info("── Roboflow downloads ───────────────────────────────────────────")
        download_roboflow_datasets(api_key=_resolve_rf_key(args))
    log.info("── Staging ──────────────────────────────────────────────────────────")
    stage_all_downloads()
    print_summary()


def _cmd_augment(args):
    log.info("── Augmenting 25-class training set ─────────────────────────────────")
    augment_training_dataset(multiplier=args.aug_multiplier)
    print_summary()


def _cmd_train_full(args):
    setup_dirs()

    # Downloads + staging
    if not args.no_kaggle:
        log.info("── Kaggle downloads ─────────────────────────────────────────────")
        download_kaggle_datasets()
    if not args.no_roboflow:
        log.info("── Roboflow downloads ───────────────────────────────────────────")
        download_roboflow_datasets(api_key=_resolve_rf_key(args))
    log.info("── Staging ──────────────────────────────────────────────────────────")
    stage_all_downloads()

    # Phase 1
    log.info("── Phase 1: broad pre-training ──────────────────────────────────────")
    build_pretrain_dataset(train_ratio=args.split)
    run_phase1(epochs=args.epochs_pretrain)

    # Phase 2
    if not args.no_augment:
        log.info("── Augmentation (Phase 2 prep) ───────────────────────────────────")
        augment_training_dataset(multiplier=args.aug_multiplier)
    log.info("── Phase 2: fine-tuning 184 classes ─────────────────────────────────")
    run_phase2(epochs=args.epochs_finetune)

    print_summary()


def _cmd_train_finetune(args):
    if not args.no_augment:
        log.info("── Augmentation (Phase 2 prep) ───────────────────────────────────")
        augment_training_dataset(multiplier=args.aug_multiplier)
    log.info("── Phase 2: fine-tuning 184 classes ─────────────────────────────────")
    run_phase2(epochs=args.epochs_finetune)
    print_summary()


def _cmd_build_parent_dataset(args):
    """Build the 17-class diameter dataset from the existing 184-class set."""
    log.info("── Building YOLO11 parent-class dataset ─────────────────────────────")
    build_parent_dataset(train_ratio=args.split)
    print_summary()


def _cmd_train_yolo11(args):
    """Build parent dataset (if not already done) then train YOLO11s-cls."""
    if not YOLO11_PARENT_DATASET.exists() or not any(YOLO11_PARENT_DATASET.rglob("*.jpg")):
        log.info("── Building YOLO11 parent-class dataset ─────────────────────────")
        build_parent_dataset(train_ratio=args.split)
    log.info("── Training YOLO11s-cls (17 diameter classes) ───────────────────────")
    run_yolo11_training(epochs=args.epochs_yolo11, imgsz=args.imgsz)
    print_summary()


def _cmd_train_type(args):
    """Train YOLO11s-cls on the 152 product-type classes."""
    log.info("── Training YOLO11s-cls (152 product-type classes) ──────────────────")
    run_yolo11_type_training(
        epochs=args.epochs_type,
        imgsz=args.imgsz,
        batch=args.batch,
        workers=args.workers,
    )
    print_summary()


def _cmd_summary(_args):
    print_summary()


def main():
    _setup_logging()

    root = argparse.ArgumentParser(
        prog="dataset_builder",
        description="Smart Tool Recognition — dataset & training pipeline.",
    )
    sub = root.add_subparsers(dest="cmd", required=True)

    # download
    p_dl = sub.add_parser("download", help="Download & stage all public datasets.")
    _add_common_args(p_dl)

    # augment
    p_aug = sub.add_parser("augment", help="Augment the 25-class training set in-place.")
    _add_common_args(p_aug)

    # train-full
    p_full = sub.add_parser(
        "train-full",
        help="Full pipeline: download → stage → augment → phase1 → phase2.",
    )
    _add_common_args(p_full)

    # train-finetune
    p_ft = sub.add_parser(
        "train-finetune",
        help="Phase-2 only (skip download & phase1; assumes phase1 already done).",
    )
    _add_common_args(p_ft)

    # build-parent-dataset
    p_bpd = sub.add_parser(
        "build-parent-dataset",
        help="Reorganise 184-class dataset → 17 diameter-class dataset for YOLO11.",
    )
    _add_common_args(p_bpd)

    # train-yolo11
    p_y11 = sub.add_parser(
        "train-yolo11",
        help="Train YOLO11s-cls on 17 bolt-diameter classes.",
    )
    _add_common_args(p_y11)

    # train-type  ← NEW: 152 product-type classes
    p_type = sub.add_parser(
        "train-type",
        help="Train YOLO11s-cls on 152 product-type classes (run image_downloader.py first).",
    )
    _add_common_args(p_type)

    # summary
    p_sum = sub.add_parser("summary", help="Print dataset counts and exit.")
    _add_common_args(p_sum)

    args = root.parse_args()

    dispatch = {
        "download":             _cmd_download,
        "augment":              _cmd_augment,
        "train-full":           _cmd_train_full,
        "train-finetune":       _cmd_train_finetune,
        "build-parent-dataset": _cmd_build_parent_dataset,
        "train-yolo11":         _cmd_train_yolo11,
        "train-type":           _cmd_train_type,
        "summary":              _cmd_summary,
    }
    dispatch[args.cmd](args)


if __name__ == "__main__":
    main()
