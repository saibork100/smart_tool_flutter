"""
image_downloader.py — Download training images for 152 product-type classes.

Strategy
────────
The YOLO model classifies PRODUCT TYPE (e.g. "hex bolt zinc 4.8 DIN933"), not size.
After detection the UI shows a scrollable list of size sub-items so the user picks
the exact bolt they need (M6×30, M8×50, etc.).

For training variety we download images for EACH size sub-item of every type, using
size-specific queries (e.g. "hex bolt zinc DIN933 M6x30"). All images for one type
go into the same class folder — so the model learns to recognise the TYPE across
all its sizes.

Usage
─────
  # Download all 152 classes (default 60 images/class)
  python image_downloader.py

  # Limit images per class
  python image_downloader.py --per-class 40

  # Only one family
  python image_downloader.py --family vis

  # Dry-run — print queries without downloading
  python image_downloader.py --dry-run

  # Skip classes that already have enough images
  python image_downloader.py --skip-existing

Output
──────
  E:\\photo coliction\\type_dataset\\
  ├── train\\
  │   ├── vis__th__zinc__48__din933\\   ← 80% of images
  │   └── ...
  └── val\\
      ├── vis__th__zinc__48__din933\\   ← 20% of images
      └── ...

Install
───────
  pip install icrawler tqdm pillow
"""

from __future__ import annotations

import argparse
import logging
import os
import random
import shutil
import time
from pathlib import Path

from tqdm import tqdm

# ── Output paths ───────────────────────────────────────────────────────────────
DATASET_ROOT = Path(r"E:\photo coliction\type_dataset")
TRAIN_DIR    = DATASET_ROOT / "train"
VAL_DIR      = DATASET_ROOT / "val"
TEMP_DIR     = DATASET_ROOT / "_download_tmp"

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}

# ── Catalogue: 152 product-type classes ───────────────────────────────────────
# Each entry:
#   class_id  — folder name (safe for all OS, no spaces)
#   name_fr   — French catalogue name (used in search queries)
#   name_en   — English equivalent
#   family    — vis | boulon | ecrou | rondelle | rivet | cheville
#   sizes     — list of size sub-items; each generates its own search queries.
#               All images land in the SAME class folder for type classification.
#               Format: "MdxL" for bolts/screws, "Md" for nuts/washers.

# Helper: all hex-bolt sizes from the existing catalogue
_VIS_TH_SIZES = [
    "M4x10", "M4x16", "M4x20", "M4x25", "M4x30", "M4x40", "M4x50",
    "M5x10", "M5x16", "M5x20", "M5x25", "M5x30", "M5x40", "M5x50",
    "M6x12", "M6x16", "M6x20", "M6x25", "M6x30", "M6x40", "M6x50",
    "M6x60", "M6x70", "M6x80", "M6x100", "M6x120",
    "M8x16", "M8x20", "M8x25", "M8x30", "M8x40", "M8x50",
    "M8x60", "M8x70", "M8x80", "M8x100", "M8x120", "M8x150",
    "M10x16", "M10x20", "M10x25", "M10x30", "M10x40", "M10x50",
    "M10x60", "M10x70", "M10x80", "M10x100", "M10x120",
    "M12x20", "M12x25", "M12x30", "M12x40", "M12x50",
    "M12x60", "M12x70", "M12x80", "M12x100", "M12x120",
    "M14x30", "M14x40", "M14x50", "M14x60", "M14x80", "M14x100",
    "M16x30", "M16x40", "M16x50", "M16x60", "M16x80", "M16x100",
    "M18x50", "M18x60", "M18x80", "M18x100",
    "M20x50", "M20x60", "M20x80", "M20x100",
    "M24x60", "M24x80", "M24x100",
]

_SOCKET_SIZES = [
    "M4x8", "M4x10", "M4x16", "M4x20", "M4x25", "M4x30",
    "M5x8", "M5x10", "M5x16", "M5x20", "M5x25", "M5x30", "M5x40",
    "M6x10", "M6x12", "M6x16", "M6x20", "M6x25", "M6x30", "M6x40", "M6x50",
    "M8x10", "M8x16", "M8x20", "M8x25", "M8x30", "M8x40", "M8x50", "M8x60",
    "M10x20", "M10x25", "M10x30", "M10x40", "M10x50", "M10x60",
    "M12x20", "M12x25", "M12x30", "M12x40", "M12x50", "M12x60",
    "M16x30", "M16x40", "M16x50", "M16x60",
]

_NUT_SIZES = ["M4", "M5", "M6", "M8", "M10", "M12", "M14", "M16", "M18", "M20", "M24"]

_WASHER_SIZES = ["M4", "M5", "M6", "M8", "M10", "M12", "M14", "M16", "M20", "M24"]

_RIVET_SIZES = [
    "3x6", "3x8", "3x10", "3x12",
    "4x6", "4x8", "4x10", "4x12", "4x16",
    "5x8", "5x10", "5x12", "5x16",
    "6x10", "6x12", "6x16",
]

_ANCHOR_SIZES = [
    "6x30", "6x35", "6x40", "6x50",
    "8x40", "8x50", "8x60", "8x80",
    "10x50", "10x60", "10x80", "10x100",
    "12x60", "12x80", "12x100",
]

CATALOGUE: list[dict] = [

    # ══════════════════════════════════════════════════════════════════════════
    # VIS (screws / bolts) — 67 types
    # ══════════════════════════════════════════════════════════════════════════

    # ── Vis Tête Hexagonale (hex-head bolt) ───────────────────────────────────
    {
        "class_id": "vis__th__zinc__48__din933",
        "name_fr": "VIS TETE HEXAGONALE ACIER ZINGUE 4.8 DIN933",
        "name_en": "hex bolt zinc plated grade 4.8 DIN933 full thread",
        "family": "vis",
        "sizes": _VIS_TH_SIZES,
    },
    {
        "class_id": "vis__th__zinc__88__din933",
        "name_fr": "VIS TETE HEXAGONALE ACIER ZINGUE 8.8 DIN933",
        "name_en": "hex bolt zinc plated grade 8.8 DIN933 full thread",
        "family": "vis",
        "sizes": _VIS_TH_SIZES,
    },
    {
        "class_id": "vis__th__zinc__48__din931",
        "name_fr": "VIS TETE HEXAGONALE ACIER ZINGUE 4.8 DIN931",
        "name_en": "hex bolt zinc plated grade 4.8 DIN931 partial thread",
        "family": "vis",
        "sizes": _VIS_TH_SIZES,
    },
    {
        "class_id": "vis__th__zinc__88__din931",
        "name_fr": "VIS TETE HEXAGONALE ACIER ZINGUE 8.8 DIN931",
        "name_en": "hex bolt zinc plated grade 8.8 DIN931 partial thread",
        "family": "vis",
        "sizes": _VIS_TH_SIZES,
    },
    {
        "class_id": "vis__th__inox__a2__din933",
        "name_fr": "VIS TETE HEXAGONALE INOX A2 DIN933",
        "name_en": "hex bolt stainless steel A2 DIN933 full thread",
        "family": "vis",
        "sizes": _VIS_TH_SIZES,
    },
    {
        "class_id": "vis__th__inox__a4__din933",
        "name_fr": "VIS TETE HEXAGONALE INOX A4 DIN933",
        "name_en": "hex bolt stainless steel A4 marine grade DIN933",
        "family": "vis",
        "sizes": _VIS_TH_SIZES,
    },
    {
        "class_id": "vis__th__inox__a2__din931",
        "name_fr": "VIS TETE HEXAGONALE INOX A2 DIN931",
        "name_en": "hex bolt stainless steel A2 DIN931 partial thread",
        "family": "vis",
        "sizes": _VIS_TH_SIZES,
    },
    {
        "class_id": "vis__th__brut__88__din933",
        "name_fr": "VIS TETE HEXAGONALE BRUT 8.8 DIN933",
        "name_en": "hex bolt black steel grade 8.8 DIN933",
        "family": "vis",
        "sizes": _VIS_TH_SIZES,
    },
    {
        "class_id": "vis__th__brut__109__din931",
        "name_fr": "VIS TETE HEXAGONALE BRUT 10.9 DIN931",
        "name_en": "hex bolt black steel grade 10.9 DIN931 high tensile",
        "family": "vis",
        "sizes": _VIS_TH_SIZES,
    },
    {
        "class_id": "vis__th__hdr__din933",
        "name_fr": "VIS TETE HEXAGONALE HDR GALVANISE A CHAUD DIN933",
        "name_en": "hex bolt hot-dip galvanized HDR DIN933",
        "family": "vis",
        "sizes": ["M8x30", "M8x50", "M8x80", "M10x40", "M10x60", "M10x80",
                  "M12x40", "M12x60", "M12x80", "M16x50", "M16x80", "M16x100"],
    },

    # ── Vis Cylindrique Hexagonale Creuse / CHC (socket head cap screw) ───────
    {
        "class_id": "vis__chc__zinc__din912",
        "name_fr": "VIS CHC ACIER ZINGUE DIN912",
        "name_en": "socket head cap screw zinc plated DIN912",
        "family": "vis",
        "sizes": _SOCKET_SIZES,
    },
    {
        "class_id": "vis__chc__inox__a2__din912",
        "name_fr": "VIS CHC INOX A2 DIN912",
        "name_en": "socket head cap screw stainless steel A2 DIN912",
        "family": "vis",
        "sizes": _SOCKET_SIZES,
    },
    {
        "class_id": "vis__chc__inox__a4__din912",
        "name_fr": "VIS CHC INOX A4 DIN912",
        "name_en": "socket head cap screw stainless steel A4 marine DIN912",
        "family": "vis",
        "sizes": _SOCKET_SIZES,
    },
    {
        "class_id": "vis__chc__brut__88__din912",
        "name_fr": "VIS CHC BRUT 8.8 DIN912",
        "name_en": "socket head cap screw black steel grade 8.8 DIN912",
        "family": "vis",
        "sizes": _SOCKET_SIZES,
    },
    {
        "class_id": "vis__chc__brut__129__din912",
        "name_fr": "VIS CHC BRUT 12.9 DIN912",
        "name_en": "socket head cap screw black steel grade 12.9 DIN912",
        "family": "vis",
        "sizes": _SOCKET_SIZES,
    },

    # ── Vis Tête Fraisée Hexagonale Creuse / TCHC (countersunk socket) ────────
    {
        "class_id": "vis__tchc__zinc__din7991",
        "name_fr": "VIS TETE FRAISEE CHC ACIER ZINGUE DIN7991",
        "name_en": "flat countersunk socket screw zinc DIN7991",
        "family": "vis",
        "sizes": ["M4x10", "M4x16", "M4x20", "M4x25", "M4x30",
                  "M5x10", "M5x16", "M5x20", "M5x25", "M5x30", "M5x40",
                  "M6x12", "M6x16", "M6x20", "M6x25", "M6x30", "M6x40", "M6x50",
                  "M8x16", "M8x20", "M8x25", "M8x30", "M8x40", "M8x50",
                  "M10x25", "M10x30", "M10x40", "M10x50",
                  "M12x30", "M12x40", "M12x50"],
    },
    {
        "class_id": "vis__tchc__inox__a2__din7991",
        "name_fr": "VIS TETE FRAISEE CHC INOX A2 DIN7991",
        "name_en": "flat countersunk socket screw stainless A2 DIN7991",
        "family": "vis",
        "sizes": ["M4x16", "M4x20", "M4x25", "M5x16", "M5x20", "M5x25",
                  "M6x16", "M6x20", "M6x25", "M6x30", "M6x40",
                  "M8x20", "M8x25", "M8x30", "M8x40",
                  "M10x25", "M10x30", "M10x40", "M12x30", "M12x40"],
    },
    {
        "class_id": "vis__tchc__brut__88__din7991",
        "name_fr": "VIS TETE FRAISEE CHC BRUT 8.8 DIN7991",
        "name_en": "flat countersunk socket screw black 8.8 DIN7991",
        "family": "vis",
        "sizes": ["M5x20", "M5x25", "M6x20", "M6x25", "M6x30",
                  "M8x25", "M8x30", "M8x40", "M10x30", "M10x40", "M12x40"],
    },

    # ── Vis Tête Bombée Hexagonale Creuse / TBHC (button head socket) ─────────
    {
        "class_id": "vis__tbhc__zinc__din7380",
        "name_fr": "VIS TETE BOMBEE CHC ACIER ZINGUE DIN7380",
        "name_en": "button head socket screw zinc DIN7380",
        "family": "vis",
        "sizes": ["M4x8", "M4x10", "M4x16", "M4x20",
                  "M5x8", "M5x10", "M5x16", "M5x20", "M5x25",
                  "M6x10", "M6x12", "M6x16", "M6x20", "M6x25", "M6x30",
                  "M8x12", "M8x16", "M8x20", "M8x25", "M8x30",
                  "M10x20", "M10x25", "M10x30"],
    },
    {
        "class_id": "vis__tbhc__inox__a2__din7380",
        "name_fr": "VIS TETE BOMBEE CHC INOX A2 DIN7380",
        "name_en": "button head socket screw stainless A2 DIN7380",
        "family": "vis",
        "sizes": ["M4x10", "M4x16", "M5x10", "M5x16", "M5x20",
                  "M6x12", "M6x16", "M6x20", "M6x25",
                  "M8x16", "M8x20", "M8x25", "M10x20", "M10x25"],
    },

    # ── Vis BTR / Carrosserie (carriage bolt, round head square neck) ──────────
    {
        "class_id": "vis__btr__zinc__din603",
        "name_fr": "VIS BTR CARROSSERIE ACIER ZINGUE DIN603",
        "name_en": "carriage bolt round head square neck zinc DIN603",
        "family": "vis",
        "sizes": ["M6x20", "M6x25", "M6x30", "M6x40", "M6x50", "M6x60",
                  "M8x20", "M8x25", "M8x30", "M8x40", "M8x50", "M8x60", "M8x80",
                  "M10x30", "M10x40", "M10x50", "M10x60", "M10x80",
                  "M12x40", "M12x50", "M12x60", "M12x80"],
    },
    {
        "class_id": "vis__btr__inox__a2__din603",
        "name_fr": "VIS BTR CARROSSERIE INOX A2 DIN603",
        "name_en": "carriage bolt stainless steel A2 DIN603",
        "family": "vis",
        "sizes": ["M6x25", "M6x30", "M6x40", "M6x50",
                  "M8x25", "M8x30", "M8x40", "M8x50", "M8x60",
                  "M10x40", "M10x50", "M10x60", "M12x50", "M12x60"],
    },

    # ── Vis Tête Cylindrique (cylinder head, Phillips/Pozidriv) ───────────────
    {
        "class_id": "vis__tc__zinc__din84",
        "name_fr": "VIS TETE CYLINDRIQUE FENDUE ACIER ZINGUE DIN84",
        "name_en": "slotted cylinder head machine screw zinc DIN84",
        "family": "vis",
        "sizes": ["M3x6", "M3x8", "M3x10", "M3x16", "M3x20",
                  "M4x8", "M4x10", "M4x16", "M4x20", "M4x25",
                  "M5x10", "M5x16", "M5x20", "M5x25", "M5x30",
                  "M6x10", "M6x16", "M6x20", "M6x25", "M6x30"],
    },
    {
        "class_id": "vis__tcp__zinc__din7985",
        "name_fr": "VIS TETE CYLINDRIQUE PHILLIPS ACIER ZINGUE DIN7985",
        "name_en": "Phillips cylinder head machine screw zinc DIN7985",
        "family": "vis",
        "sizes": ["M3x6", "M3x8", "M3x10", "M3x16",
                  "M4x8", "M4x10", "M4x16", "M4x20", "M4x25",
                  "M5x10", "M5x16", "M5x20", "M5x25", "M5x30",
                  "M6x12", "M6x16", "M6x20", "M6x25"],
    },

    # ── Vis Tête Fraisée (countersunk flat head) ──────────────────────────────
    {
        "class_id": "vis__tf__zinc__din965",
        "name_fr": "VIS TETE FRAISEE PHILLIPS ACIER ZINGUE DIN965",
        "name_en": "countersunk flat head Phillips machine screw zinc DIN965",
        "family": "vis",
        "sizes": ["M3x6", "M3x8", "M3x10", "M3x16",
                  "M4x8", "M4x10", "M4x16", "M4x20", "M4x25",
                  "M5x10", "M5x16", "M5x20", "M5x25",
                  "M6x12", "M6x16", "M6x20", "M6x25", "M6x30"],
    },
    {
        "class_id": "vis__tf__inox__a2__din965",
        "name_fr": "VIS TETE FRAISEE PHILLIPS INOX A2 DIN965",
        "name_en": "countersunk Phillips machine screw stainless A2 DIN965",
        "family": "vis",
        "sizes": ["M4x10", "M4x16", "M4x20", "M5x10", "M5x16", "M5x20",
                  "M6x16", "M6x20", "M6x25", "M6x30"],
    },

    # ── Vis Auto-taraudeuse / autoperceuse (self-tapping / self-drilling) ──────
    {
        "class_id": "vis__autotaraudeuse__zinc__din7976",
        "name_fr": "VIS AUTOTARAUDEUSE TETE HEXAGONALE ACIER ZINGUE DIN7976",
        "name_en": "self-tapping hex head screw zinc DIN7976",
        "family": "vis",
        "sizes": ["ST3.5x13", "ST3.5x19", "ST3.5x25",
                  "ST4.2x13", "ST4.2x19", "ST4.2x25", "ST4.2x32",
                  "ST4.8x13", "ST4.8x19", "ST4.8x25", "ST4.8x32", "ST4.8x38",
                  "ST5.5x25", "ST5.5x32", "ST5.5x38", "ST5.5x50",
                  "ST6.3x25", "ST6.3x32", "ST6.3x38", "ST6.3x50"],
    },
    {
        "class_id": "vis__autoperceuse__zinc__din7504",
        "name_fr": "VIS AUTOPERCEUSE TETE HEXAGONALE ACIER ZINGUE DIN7504",
        "name_en": "self-drilling hex washer head screw zinc DIN7504",
        "family": "vis",
        "sizes": ["4.2x13", "4.2x19", "4.2x25", "4.2x32",
                  "4.8x19", "4.8x25", "4.8x32", "4.8x38",
                  "5.5x25", "5.5x32", "5.5x38", "5.5x50",
                  "6.3x25", "6.3x38", "6.3x50"],
    },

    # ── Vis à Bois (wood screws) ───────────────────────────────────────────────
    {
        "class_id": "vis__bois__zinc__txstar",
        "name_fr": "VIS A BOIS TETE FRAISEE TORX ACIER ZINGUE",
        "name_en": "wood screw countersunk Torx zinc plated",
        "family": "vis",
        "sizes": ["3x16", "3x20", "3x25", "3x30", "3.5x16", "3.5x20", "3.5x25",
                  "3.5x30", "3.5x35", "4x20", "4x25", "4x30", "4x35", "4x40", "4x50",
                  "4.5x30", "4.5x40", "4.5x50", "5x40", "5x50", "5x60", "5x70",
                  "6x40", "6x50", "6x60", "6x70", "6x80", "6x100"],
    },
    {
        "class_id": "vis__bois__inox__a2__txstar",
        "name_fr": "VIS A BOIS TETE FRAISEE TORX INOX A2",
        "name_en": "wood screw countersunk Torx stainless A2",
        "family": "vis",
        "sizes": ["3.5x20", "3.5x25", "3.5x30", "4x20", "4x25", "4x30", "4x40",
                  "4.5x30", "4.5x40", "4.5x50", "5x40", "5x50", "5x60",
                  "6x40", "6x50", "6x60", "6x80"],
    },

    # ── Vis Tirefond (lag bolt / coach screw) ─────────────────────────────────
    {
        "class_id": "vis__tirefond__zinc__din571",
        "name_fr": "VIS TIREFOND TETE HEXAGONALE ACIER ZINGUE DIN571",
        "name_en": "lag bolt hex head coach screw zinc DIN571",
        "family": "vis",
        "sizes": ["M6x40", "M6x50", "M6x60", "M6x70", "M6x80", "M6x100",
                  "M8x40", "M8x50", "M8x60", "M8x80", "M8x100", "M8x120", "M8x150",
                  "M10x50", "M10x60", "M10x80", "M10x100", "M10x120",
                  "M12x60", "M12x80", "M12x100", "M12x120"],
    },

    # ── Vis Inviolable (tamper-proof security screw) ──────────────────────────
    {
        "class_id": "vis__inviolable__zinc__torx_plus",
        "name_fr": "VIS INVIOLABLE TETE FRAISEE TORX PLUS ACIER ZINGUE",
        "name_en": "tamper-proof security screw countersunk Torx Plus zinc",
        "family": "vis",
        "sizes": ["M4x16", "M4x20", "M5x16", "M5x20", "M5x25",
                  "M6x16", "M6x20", "M6x25", "M6x30"],
    },

    # ── Vis moletée / oreilles (knurled thumb / wing screw) ───────────────────
    {
        "class_id": "vis__oreilles__zinc__din316",
        "name_fr": "VIS A OREILLES ACIER ZINGUE DIN316",
        "name_en": "wing screw butterfly zinc DIN316",
        "family": "vis",
        "sizes": ["M4x20", "M4x25", "M4x30", "M5x20", "M5x25", "M5x30",
                  "M6x20", "M6x25", "M6x30", "M6x40", "M8x25", "M8x30", "M8x40"],
    },

    # ── Vis tête bombée fendue (round slotted head machine screw) ─────────────
    {
        "class_id": "vis__tb__fendue__zinc__din7985",
        "name_fr": "VIS TETE BOMBEE FENDUE ACIER ZINGUE DIN7985",
        "name_en": "round slotted head machine screw zinc DIN7985",
        "family": "vis",
        "sizes": ["M3x6", "M3x8", "M3x10", "M4x8", "M4x10", "M4x16",
                  "M5x10", "M5x16", "M5x20", "M6x12", "M6x16", "M6x20"],
    },

    # ── Vis épaulée / à épaulement (shoulder screw) ───────────────────────────
    {
        "class_id": "vis__epaulee__inox__a2__din9841",
        "name_fr": "VIS EPAULEE INOX A2 DIN9841",
        "name_en": "shoulder bolt screw stainless A2 DIN9841",
        "family": "vis",
        "sizes": ["6x10", "6x15", "6x20", "8x10", "8x15", "8x20", "8x25",
                  "10x15", "10x20", "10x25", "10x30", "12x20", "12x25", "12x30"],
    },

    # ══════════════════════════════════════════════════════════════════════════
    # BOULON (bolt + nut assemblies) — 4 types
    # ══════════════════════════════════════════════════════════════════════════

    {
        "class_id": "boulon__zinc__48",
        "name_fr": "BOULON COMPLET ACIER ZINGUE 4.8 (VIS + ECROU + RONDELLES)",
        "name_en": "bolt assembly zinc plated 4.8 hex bolt nut washers set",
        "family": "boulon",
        "sizes": ["M6x30", "M6x40", "M6x50",
                  "M8x30", "M8x40", "M8x50", "M8x60", "M8x80",
                  "M10x40", "M10x50", "M10x60", "M10x80",
                  "M12x50", "M12x60", "M12x80"],
    },
    {
        "class_id": "boulon__inox__a2",
        "name_fr": "BOULON COMPLET INOX A2 (VIS + ECROU + RONDELLES)",
        "name_en": "bolt assembly stainless A2 hex bolt nut washers set",
        "family": "boulon",
        "sizes": ["M6x30", "M6x40", "M8x30", "M8x40", "M8x50",
                  "M10x40", "M10x50", "M10x60", "M12x50", "M12x60"],
    },
    {
        "class_id": "boulon__brut__88",
        "name_fr": "BOULON COMPLET BRUT 8.8 (VIS + ECROU + RONDELLES)",
        "name_en": "bolt assembly black steel 8.8 hex bolt nut washers set",
        "family": "boulon",
        "sizes": ["M8x40", "M8x50", "M8x60", "M8x80",
                  "M10x50", "M10x60", "M10x80",
                  "M12x60", "M12x80", "M12x100",
                  "M16x60", "M16x80", "M16x100"],
    },
    {
        "class_id": "boulon__charpente__hdr",
        "name_fr": "BOULON CHARPENTE HDR GALVANISE A CHAUD",
        "name_en": "structural bolt hot-dip galvanized HDR assembly",
        "family": "boulon",
        "sizes": ["M12x40", "M12x50", "M12x60",
                  "M16x50", "M16x60", "M16x80",
                  "M20x60", "M20x80", "M20x100",
                  "M24x80", "M24x100"],
    },

    # ══════════════════════════════════════════════════════════════════════════
    # ECROU (nuts) — 38 types
    # ══════════════════════════════════════════════════════════════════════════

    {
        "class_id": "ecrou__hex__zinc__din934",
        "name_fr": "ECROU HEXAGONAL ACIER ZINGUE DIN934",
        "name_en": "hex nut zinc plated DIN934",
        "family": "ecrou",
        "sizes": _NUT_SIZES,
    },
    {
        "class_id": "ecrou__hex__inox__a2__din934",
        "name_fr": "ECROU HEXAGONAL INOX A2 DIN934",
        "name_en": "hex nut stainless steel A2 DIN934",
        "family": "ecrou",
        "sizes": _NUT_SIZES,
    },
    {
        "class_id": "ecrou__hex__inox__a4__din934",
        "name_fr": "ECROU HEXAGONAL INOX A4 DIN934",
        "name_en": "hex nut stainless steel A4 marine DIN934",
        "family": "ecrou",
        "sizes": _NUT_SIZES,
    },
    {
        "class_id": "ecrou__hex__brut__88__din934",
        "name_fr": "ECROU HEXAGONAL BRUT 8.8 DIN934",
        "name_en": "hex nut black steel grade 8.8 DIN934",
        "family": "ecrou",
        "sizes": _NUT_SIZES,
    },
    {
        "class_id": "ecrou__hex__hdr__din934",
        "name_fr": "ECROU HEXAGONAL HDR GALVANISE A CHAUD DIN934",
        "name_en": "hex nut hot-dip galvanized DIN934",
        "family": "ecrou",
        "sizes": ["M8", "M10", "M12", "M16", "M20", "M24"],
    },
    {
        "class_id": "ecrou__hex__bas__zinc__din439",
        "name_fr": "ECROU HEXAGONAL BAS ACIER ZINGUE DIN439",
        "name_en": "thin hex nut jam nut zinc plated DIN439",
        "family": "ecrou",
        "sizes": _NUT_SIZES,
    },
    {
        "class_id": "ecrou__hex__bas__inox__a2__din439",
        "name_fr": "ECROU HEXAGONAL BAS INOX A2 DIN439",
        "name_en": "thin hex nut jam nut stainless A2 DIN439",
        "family": "ecrou",
        "sizes": _NUT_SIZES,
    },
    {
        "class_id": "ecrou__hex__haut__zinc__din9241",
        "name_fr": "ECROU HEXAGONAL HAUT ACIER ZINGUE DIN9241",
        "name_en": "heavy hex nut zinc plated DIN9241",
        "family": "ecrou",
        "sizes": ["M8", "M10", "M12", "M16", "M20", "M24"],
    },
    {
        "class_id": "ecrou__frein__zinc__din985",
        "name_fr": "ECROU FREIN NYLSTOP ACIER ZINGUE DIN985",
        "name_en": "nylock nylon insert lock nut zinc DIN985",
        "family": "ecrou",
        "sizes": _NUT_SIZES,
    },
    {
        "class_id": "ecrou__frein__inox__a2__din985",
        "name_fr": "ECROU FREIN NYLSTOP INOX A2 DIN985",
        "name_en": "nylock lock nut stainless steel A2 DIN985",
        "family": "ecrou",
        "sizes": _NUT_SIZES,
    },
    {
        "class_id": "ecrou__frein__inox__a4__din985",
        "name_fr": "ECROU FREIN NYLSTOP INOX A4 DIN985",
        "name_en": "nylock lock nut stainless steel A4 marine DIN985",
        "family": "ecrou",
        "sizes": _NUT_SIZES,
    },
    {
        "class_id": "ecrou__frein__brut__din985",
        "name_fr": "ECROU FREIN NYLSTOP BRUT DIN985",
        "name_en": "nylock lock nut black steel DIN985",
        "family": "ecrou",
        "sizes": _NUT_SIZES,
    },
    {
        "class_id": "ecrou__borgne__zinc__din1587",
        "name_fr": "ECROU BORGNE ACIER ZINGUE DIN1587",
        "name_en": "cap nut dome acorn nut zinc DIN1587",
        "family": "ecrou",
        "sizes": ["M4", "M5", "M6", "M8", "M10", "M12"],
    },
    {
        "class_id": "ecrou__borgne__inox__a2__din1587",
        "name_fr": "ECROU BORGNE INOX A2 DIN1587",
        "name_en": "cap nut acorn nut stainless A2 DIN1587",
        "family": "ecrou",
        "sizes": ["M4", "M5", "M6", "M8", "M10", "M12"],
    },
    {
        "class_id": "ecrou__papillon__zinc__din315",
        "name_fr": "ECROU PAPILLON ACIER ZINGUE DIN315",
        "name_en": "wing nut butterfly nut zinc DIN315",
        "family": "ecrou",
        "sizes": ["M4", "M5", "M6", "M8", "M10", "M12"],
    },
    {
        "class_id": "ecrou__papillon__inox__a2__din315",
        "name_fr": "ECROU PAPILLON INOX A2 DIN315",
        "name_en": "wing nut stainless A2 DIN315",
        "family": "ecrou",
        "sizes": ["M4", "M5", "M6", "M8", "M10"],
    },
    {
        "class_id": "ecrou__carre__zinc__din557",
        "name_fr": "ECROU CARRE ACIER ZINGUE DIN557",
        "name_en": "square nut zinc plated DIN557",
        "family": "ecrou",
        "sizes": ["M4", "M5", "M6", "M8", "M10", "M12"],
    },
    {
        "class_id": "ecrou__embase__rond__zinc__din6923",
        "name_fr": "ECROU A EMBASE RONDE ACIER ZINGUE DIN6923",
        "name_en": "flange nut serrated zinc DIN6923",
        "family": "ecrou",
        "sizes": ["M5", "M6", "M8", "M10", "M12", "M16"],
    },
    {
        "class_id": "ecrou__embase__rond__inox__a2__din6923",
        "name_fr": "ECROU A EMBASE RONDE INOX A2 DIN6923",
        "name_en": "flange nut stainless A2 DIN6923",
        "family": "ecrou",
        "sizes": ["M5", "M6", "M8", "M10", "M12"],
    },
    {
        "class_id": "ecrou__hexagonal__autofreinant__zinc__din980",
        "name_fr": "ECROU HEXAGONAL AUTOFREINANT TOUT METAL ACIER ZINGUE DIN980",
        "name_en": "all-metal prevailing torque hex nut zinc DIN980",
        "family": "ecrou",
        "sizes": _NUT_SIZES,
    },
    {
        "class_id": "ecrou__hexagonal__autofreinant__inox__a2__din980",
        "name_fr": "ECROU HEXAGONAL AUTOFREINANT TOUT METAL INOX A2 DIN980",
        "name_en": "all-metal prevailing torque hex nut stainless A2 DIN980",
        "family": "ecrou",
        "sizes": _NUT_SIZES,
    },
    {
        "class_id": "ecrou__cheville__hex__zinc",
        "name_fr": "ECROU HEXAGONAL LONG POUR CHEVILLE ACIER ZINGUE",
        "name_en": "long coupling hex nut for anchor zinc",
        "family": "ecrou",
        "sizes": ["M6", "M8", "M10", "M12", "M16"],
    },
    {
        "class_id": "ecrou__molette__zinc__din466",
        "name_fr": "ECROU MOLETTE ACIER ZINGUE DIN466",
        "name_en": "knurled thumb nut zinc DIN466",
        "family": "ecrou",
        "sizes": ["M4", "M5", "M6", "M8", "M10"],
    },
    {
        "class_id": "ecrou__chapeaux__hexagonal__nylon",
        "name_fr": "ECROU CHAPEAU HEXAGONAL NYLON",
        "name_en": "plastic nylon cap nut hex",
        "family": "ecrou",
        "sizes": ["M4", "M5", "M6", "M8", "M10"],
    },

    # ══════════════════════════════════════════════════════════════════════════
    # RONDELLE (washers) — 27 types
    # ══════════════════════════════════════════════════════════════════════════

    {
        "class_id": "rondelle__plate__zinc__din125a",
        "name_fr": "RONDELLE PLATE ACIER ZINGUE DIN125A",
        "name_en": "flat washer zinc plated DIN125A",
        "family": "rondelle",
        "sizes": _WASHER_SIZES,
    },
    {
        "class_id": "rondelle__plate__inox__a2__din125a",
        "name_fr": "RONDELLE PLATE INOX A2 DIN125A",
        "name_en": "flat washer stainless steel A2 DIN125A",
        "family": "rondelle",
        "sizes": _WASHER_SIZES,
    },
    {
        "class_id": "rondelle__plate__inox__a4__din125a",
        "name_fr": "RONDELLE PLATE INOX A4 DIN125A",
        "name_en": "flat washer stainless steel A4 marine DIN125A",
        "family": "rondelle",
        "sizes": _WASHER_SIZES,
    },
    {
        "class_id": "rondelle__plate__brut__din125a",
        "name_fr": "RONDELLE PLATE BRUT DIN125A",
        "name_en": "flat washer black steel DIN125A",
        "family": "rondelle",
        "sizes": _WASHER_SIZES,
    },
    {
        "class_id": "rondelle__plate__hdr__din125a",
        "name_fr": "RONDELLE PLATE HDR GALVANISE A CHAUD DIN125A",
        "name_en": "flat washer hot-dip galvanized DIN125A",
        "family": "rondelle",
        "sizes": ["M8", "M10", "M12", "M16", "M20", "M24"],
    },
    {
        "class_id": "rondelle__large__zinc__din9021",
        "name_fr": "RONDELLE LARGE ACIER ZINGUE DIN9021",
        "name_en": "large flat washer wide zinc DIN9021",
        "family": "rondelle",
        "sizes": _WASHER_SIZES,
    },
    {
        "class_id": "rondelle__large__inox__a2__din9021",
        "name_fr": "RONDELLE LARGE INOX A2 DIN9021",
        "name_en": "large flat washer stainless A2 DIN9021",
        "family": "rondelle",
        "sizes": _WASHER_SIZES,
    },
    {
        "class_id": "rondelle__grower__zinc__din127",
        "name_fr": "RONDELLE GROWER RESSORT ACIER ZINGUE DIN127",
        "name_en": "spring lock washer Grower zinc DIN127",
        "family": "rondelle",
        "sizes": _WASHER_SIZES,
    },
    {
        "class_id": "rondelle__grower__inox__a2__din127",
        "name_fr": "RONDELLE GROWER RESSORT INOX A2 DIN127",
        "name_en": "spring lock washer stainless A2 DIN127",
        "family": "rondelle",
        "sizes": _WASHER_SIZES,
    },
    {
        "class_id": "rondelle__grower__brut__din127",
        "name_fr": "RONDELLE GROWER RESSORT BRUT DIN127",
        "name_en": "spring lock washer black steel DIN127",
        "family": "rondelle",
        "sizes": _WASHER_SIZES,
    },
    {
        "class_id": "rondelle__eventail__zinc__din6798a",
        "name_fr": "RONDELLE EVENTAIL EXTERNE ACIER ZINGUE DIN6798A",
        "name_en": "external tooth lock washer star zinc DIN6798A",
        "family": "rondelle",
        "sizes": ["M4", "M5", "M6", "M8", "M10", "M12", "M16"],
    },
    {
        "class_id": "rondelle__eventail__interne__zinc__din6798j",
        "name_fr": "RONDELLE EVENTAIL INTERNE ACIER ZINGUE DIN6798J",
        "name_en": "internal tooth lock washer star zinc DIN6798J",
        "family": "rondelle",
        "sizes": ["M4", "M5", "M6", "M8", "M10", "M12"],
    },
    {
        "class_id": "rondelle__carree__zinc__din434",
        "name_fr": "RONDELLE CARREE ACIER ZINGUE DIN434",
        "name_en": "square washer zinc DIN434",
        "family": "rondelle",
        "sizes": ["M8", "M10", "M12", "M16", "M20"],
    },
    {
        "class_id": "rondelle__plate__nylon",
        "name_fr": "RONDELLE PLATE NYLON",
        "name_en": "nylon flat washer plastic",
        "family": "rondelle",
        "sizes": ["M4", "M5", "M6", "M8", "M10", "M12"],
    },
    {
        "class_id": "rondelle__plate__cuivre",
        "name_fr": "RONDELLE PLATE CUIVRE",
        "name_en": "copper flat washer sealing",
        "family": "rondelle",
        "sizes": ["M6", "M8", "M10", "M12", "M14", "M16"],
    },
    {
        "class_id": "rondelle__embase__frein__zinc__din6902",
        "name_fr": "RONDELLE A EMBASE FREIN ACIER ZINGUE DIN6902",
        "name_en": "conical spring washer disc Belleville zinc DIN6902",
        "family": "rondelle",
        "sizes": ["M6", "M8", "M10", "M12", "M16", "M20"],
    },

    # ══════════════════════════════════════════════════════════════════════════
    # RIVET (rivets) — 6 types
    # ══════════════════════════════════════════════════════════════════════════

    {
        "class_id": "rivet__aveugle__alu__acier",
        "name_fr": "RIVET AVEUGLE TETE RONDE ALU CORPS ACIER",
        "name_en": "blind pop rivet aluminium body steel mandrel",
        "family": "rivet",
        "sizes": _RIVET_SIZES,
    },
    {
        "class_id": "rivet__aveugle__inox__inox",
        "name_fr": "RIVET AVEUGLE TETE RONDE INOX CORPS INOX",
        "name_en": "blind pop rivet stainless steel body and mandrel",
        "family": "rivet",
        "sizes": _RIVET_SIZES,
    },
    {
        "class_id": "rivet__aveugle__alu__inox__large",
        "name_fr": "RIVET AVEUGLE TETE LARGE ALU CORPS INOX",
        "name_en": "blind pop rivet large flange head aluminium stainless mandrel",
        "family": "rivet",
        "sizes": ["3x8", "3x10", "4x8", "4x10", "4x12", "4x16", "5x10", "5x12", "5x16"],
    },
    {
        "class_id": "rivet__plein__alu__din660",
        "name_fr": "RIVET PLEIN ALUMINIUM DIN660",
        "name_en": "solid rivet aluminium DIN660",
        "family": "rivet",
        "sizes": ["3x6", "3x8", "3x10", "4x6", "4x8", "4x10", "4x12",
                  "5x8", "5x10", "5x12", "6x10", "6x12", "6x16"],
    },
    {
        "class_id": "rivet__plein__acier__zinc__din660",
        "name_fr": "RIVET PLEIN ACIER ZINGUE DIN660",
        "name_en": "solid rivet zinc plated steel DIN660",
        "family": "rivet",
        "sizes": ["3x6", "3x8", "3x10", "4x6", "4x8", "4x10", "4x12",
                  "5x8", "5x10", "5x12", "6x10", "6x12", "6x16"],
    },
    {
        "class_id": "rivet__etanche__alu__acier",
        "name_fr": "RIVET ETANCHE TETE RONDE ALU CORPS ACIER",
        "name_en": "sealed waterproof blind rivet aluminium steel",
        "family": "rivet",
        "sizes": ["4x8", "4x10", "4x12", "5x10", "5x12", "5x16", "6x12", "6x16"],
    },

    # ══════════════════════════════════════════════════════════════════════════
    # CHEVILLE (wall anchors / plugs) — 10 types
    # ══════════════════════════════════════════════════════════════════════════

    {
        "class_id": "cheville__nylon__universelle",
        "name_fr": "CHEVILLE NYLON UNIVERSELLE",
        "name_en": "universal nylon wall plug anchor",
        "family": "cheville",
        "sizes": ["5x25", "6x30", "6x35", "8x40", "8x50", "10x50", "10x60", "12x60", "14x70"],
    },
    {
        "class_id": "cheville__nylon__frame__sxr",
        "name_fr": "CHEVILLE FRAME NYLON SXR FISCHER",
        "name_en": "frame nylon wall anchor SXR Fischer",
        "family": "cheville",
        "sizes": ["8x80", "10x100", "10x140", "12x100", "12x140", "14x100"],
    },
    {
        "class_id": "cheville__metal__a_expansion__m6",
        "name_fr": "CHEVILLE METAL A EXPANSION POUR BETON",
        "name_en": "metal expansion anchor bolt concrete",
        "family": "cheville",
        "sizes": ["M6x40", "M8x50", "M8x65", "M10x65", "M10x80", "M12x80", "M12x100"],
    },
    {
        "class_id": "cheville__chimique__epoxy",
        "name_fr": "CHEVILLE CHIMIQUE RESINE EPOXY",
        "name_en": "chemical anchor epoxy injection resin",
        "family": "cheville",
        "sizes": ["M8", "M10", "M12", "M16", "M20", "M24"],
    },
    {
        "class_id": "cheville__tige__filetee__laiton",
        "name_fr": "CHEVILLE A TIGE FILETEE LAITON",
        "name_en": "brass threaded rod anchor insert",
        "family": "cheville",
        "sizes": ["M4x30", "M5x35", "M6x40", "M8x50", "M10x60"],
    },
    {
        "class_id": "cheville__papillon__metal",
        "name_fr": "CHEVILLE PAPILLON METAL PLAQUE DE PLATRE",
        "name_en": "metal toggle bolt butterfly anchor plasterboard",
        "family": "cheville",
        "sizes": ["M4x45", "M5x52", "M6x65"],
    },
    {
        "class_id": "cheville__autoperceuse__metal",
        "name_fr": "CHEVILLE AUTOPERCEUSE METAL PLAQUE DE PLATRE",
        "name_en": "self-drilling metal anchor screw plasterboard",
        "family": "cheville",
        "sizes": ["3.9x32", "3.9x38", "3.9x52"],
    },
    {
        "class_id": "cheville__molly__metal",
        "name_fr": "CHEVILLE MOLLY METAL PLAQUE DE PLATRE",
        "name_en": "molly bolt hollow wall anchor metal",
        "family": "cheville",
        "sizes": ["M4x32", "M5x40", "M6x50"],
    },
    {
        "class_id": "cheville__tasseau__nylon__bois",
        "name_fr": "CHEVILLE TASSEAU NYLON POUR BOIS",
        "name_en": "nylon batten clip anchor wood",
        "family": "cheville",
        "sizes": ["5x50", "6x60", "8x80", "10x100"],
    },
    {
        "class_id": "cheville__percage__nylon__beton_cellulaire",
        "name_fr": "CHEVILLE NYLON POUR BETON CELLULAIRE YTONG",
        "name_en": "nylon anchor aerated concrete Ytong cellular",
        "family": "cheville",
        "sizes": ["8x60", "10x80", "12x100"],
    },
]


# ── Search query builder ───────────────────────────────────────────────────────

def build_queries(entry: dict, size: str) -> list[str]:
    """
    Build search queries for one class + one size sub-item.

    For a threaded size like "M8x30":
        "hex bolt zinc 4.8 DIN933 M8x30"
        "VIS TETE HEXAGONALE ACIER ZINGUE DIN933 M8 30mm"
        "vis hexagonale zinguee M8 30 mm DIN933"

    For a plain-diameter size like "M8" (nuts / washers):
        "hex nut zinc DIN934 M8"
        "ECROU HEXAGONAL ACIER ZINGUE DIN934 M8"
    """
    name_en = entry["name_en"]
    name_fr = entry["name_fr"]

    # Normalise size into readable forms
    size_upper = size.upper()            # "M8X30" or "M8"
    size_lower = size.lower()            # "m8x30" or "m8"
    if "x" in size_lower:
        diam_part, len_part = size_lower.split("x", 1)
        size_readable = f"{diam_part.upper()}×{len_part}mm"  # "M8×30mm"
        size_compact  = f"{diam_part.upper()}x{len_part}"    # "M8x30"
    else:
        size_readable = size_upper       # "M8"
        size_compact  = size_upper

    return [
        f"{name_en} {size_compact}",
        f"{name_fr} {size_readable}",
        f"{name_en} {size_readable} fastener",
        f"{name_fr.split()[0:4][-1]} {size_compact}",   # short French prefix + size
    ]


# ── Image count helper ─────────────────────────────────────────────────────────

def count_images(folder: Path) -> int:
    if not folder.exists():
        return 0
    return sum(1 for f in folder.iterdir() if f.suffix.lower() in IMAGE_EXTS)


# ── Core download function ─────────────────────────────────────────────────────

def download_for_class(
    entry: dict,
    target_count: int,
    dry_run: bool = False,
    images_per_size: int = 4,
) -> int:
    """
    Download images for one catalogue entry into TEMP_DIR/<class_id>/.

    Iterates over all size sub-items, generates size-specific queries, and
    downloads `images_per_size` images per size.  All images land in the same
    class folder because the ML task is TYPE classification, not size.

    Returns number of new images downloaded.
    """
    class_id = entry["class_id"]
    sizes    = entry["sizes"]
    temp_dir = TEMP_DIR / class_id
    existing = count_images(temp_dir)

    if existing >= target_count:
        print(f"  [skip] {class_id} — already {existing} images")
        return 0

    if dry_run:
        sample_query = build_queries(entry, sizes[0])[0] if sizes else "—"
        print(f"  [dry]  {class_id} ({len(sizes)} sizes) — e.g. {sample_query!r}")
        return 0

    try:
        from icrawler.builtin import BingImageCrawler
    except ImportError:
        print("ERROR: icrawler not installed.  Run: pip install icrawler")
        raise SystemExit(1)

    temp_dir.mkdir(parents=True, exist_ok=True)
    before = count_images(temp_dir)

    for size in sizes:
        if count_images(temp_dir) >= target_count:
            break   # enough images collected

        queries = build_queries(entry, size)
        for query in queries:
            if count_images(temp_dir) >= target_count:
                break

            crawler = BingImageCrawler(
                storage={"root_dir": str(temp_dir)},
                log_level=logging.WARNING,
            )
            try:
                crawler.crawl(
                    keyword=query,
                    max_num=images_per_size,
                    min_size=(80, 80),
                    file_idx_offset="auto",
                )
            except Exception as e:
                tqdm.write(f"    [warn] {query!r}: {e}")

            time.sleep(1.0)   # polite pause

    after = count_images(temp_dir)
    return after - before


# ── Train/val split ────────────────────────────────────────────────────────────

def split_to_train_val(class_id: str, val_ratio: float = 0.2) -> tuple[int, int]:
    src    = TEMP_DIR / class_id
    if not src.exists():
        return 0, 0
    images = [f for f in src.iterdir() if f.suffix.lower() in IMAGE_EXTS]
    if not images:
        return 0, 0

    random.shuffle(images)
    split = max(1, int(len(images) * (1 - val_ratio)))
    train_imgs = images[:split]
    val_imgs   = images[split:]

    train_out = TRAIN_DIR / class_id
    val_out   = VAL_DIR   / class_id
    train_out.mkdir(parents=True, exist_ok=True)
    val_out.mkdir(parents=True, exist_ok=True)

    for img in train_imgs:
        shutil.copy2(img, train_out / img.name)
    for img in val_imgs:
        shutil.copy2(img, val_out   / img.name)

    return len(train_imgs), len(val_imgs)


# ── Main ───────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Download training images for 152 product-type classes"
    )
    parser.add_argument("--per-class",      type=int,   default=60,
        help="Target total images per class (default: 60)")
    parser.add_argument("--images-per-size", type=int,  default=4,
        help="Images downloaded per size sub-item per query (default: 4)")
    parser.add_argument("--val-ratio",      type=float, default=0.2,
        help="Fraction to put in val/ (default: 0.2)")
    parser.add_argument("--skip-existing",  action="store_true",
        help="Skip classes that already have enough images in train/")
    parser.add_argument("--family",         default=None,
        choices=["vis", "boulon", "ecrou", "rondelle", "rivet", "cheville"],
        help="Download only one family")
    parser.add_argument("--class-id",       default=None,
        help="Download only one specific class_id")
    parser.add_argument("--dry-run",        action="store_true",
        help="Print queries without downloading")
    args = parser.parse_args()

    # Filter catalogue
    catalogue = CATALOGUE
    if args.family:
        catalogue = [e for e in catalogue if e["family"] == args.family]
    if args.class_id:
        catalogue = [e for e in catalogue if e["class_id"] == args.class_id]

    if not catalogue:
        print("No matching classes found.")
        return

    # Count by family
    family_counts: dict[str, int] = {}
    for e in catalogue:
        family_counts[e["family"]] = family_counts.get(e["family"], 0) + 1

    print(f"\n{'DRY RUN — ' if args.dry_run else ''}Downloading {len(catalogue)} classes")
    for fam, cnt in sorted(family_counts.items()):
        print(f"  {fam}: {cnt} classes")
    print(f"\nTarget: {args.per_class} images/class  |  "
          f"{args.images_per_size} images/size-query  |  "
          f"val ratio: {args.val_ratio:.0%}")
    print(f"Output: {DATASET_ROOT}\n")

    results: list[tuple[str, int, int, int]] = []

    for entry in tqdm(catalogue, desc="Classes", unit="class"):
        class_id = entry["class_id"]

        if args.skip_existing:
            n_train = count_images(TRAIN_DIR / class_id)
            min_needed = int(args.per_class * (1 - args.val_ratio))
            if n_train >= min_needed:
                tqdm.write(f"  [skip] {class_id} — {n_train} train images")
                results.append((class_id, 0, n_train, count_images(VAL_DIR / class_id)))
                continue

        tqdm.write(f"  ↓ {class_id}  ({len(entry['sizes'])} sizes)")
        n_dl = download_for_class(
            entry,
            target_count=args.per_class,
            dry_run=args.dry_run,
            images_per_size=args.images_per_size,
        )

        if args.dry_run:
            results.append((class_id, 0, 0, 0))
            continue

        n_train, n_val = split_to_train_val(class_id, val_ratio=args.val_ratio)
        results.append((class_id, n_dl, n_train, n_val))
        tqdm.write(f"     → {n_dl} downloaded  |  train={n_train}  val={n_val}")

    # ── Summary ───────────────────────────────────────────────────────────────
    if not args.dry_run:
        print("\n" + "─" * 70)
        print("SUMMARY")
        print("─" * 70)
        total_dl  = sum(r[1] for r in results)
        total_tr  = sum(r[2] for r in results)
        total_val = sum(r[3] for r in results)
        empty     = [r[0] for r in results if r[2] == 0]

        print(f"  Total downloaded : {total_dl}")
        print(f"  Total train      : {total_tr}")
        print(f"  Total val        : {total_val}")
        print(f"  Classes          : {len(results)}")

        if empty:
            print(f"\n  Classes with 0 train images ({len(empty)}):")
            for lbl in empty[:20]:
                print(f"    • {lbl}")
            if len(empty) > 20:
                print(f"    ... and {len(empty) - 20} more")

        print(f"\nDataset saved to: {DATASET_ROOT}")
        print("Next step: python dataset_builder.py train-type")

    # Clean up temp folder
    if TEMP_DIR.exists() and not args.dry_run:
        shutil.rmtree(TEMP_DIR, ignore_errors=True)


if __name__ == "__main__":
    main()
