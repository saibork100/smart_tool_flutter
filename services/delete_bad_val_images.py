"""
delete_bad_val_images.py — Deletes all val images identified as wrong/duplicate/corrupt
during the manual audit of E:\\photo coliction\\type_dataset\\val\\

Run from anywhere:
    python services/delete_bad_val_images.py

Pass --dry-run to preview without deleting:
    python services/delete_bad_val_images.py --dry-run
"""

from __future__ import annotations
import sys
from pathlib import Path

VAL = Path(r"E:\photo coliction\type_dataset\val")

# fmt: off
BAD_IMAGES: dict[str, list[str]] = {

    # ── vis__th__zinc__48__din933 ─────────────────────────────────────────────
    "vis__th__zinc__48__din933": [
        "000011.jpg",  # technical drawing of socket set screw
        "000022.jpg",  # black button head socket screws (TBHC)
        "000034.jpg",  # threaded rods
        "000036.jpg",  # duplicate of 000022 + wrong type
    ],

    # ── vis__th__zinc__88__din933 ─────────────────────────────────────────────
    "vis__th__zinc__88__din933": [
        "000012.jpg",  # technical drawing of socket set screw
        "000048.jpg",  # flat countersunk socket screw (TCHC)
    ],

    # ── vis__th__zinc__48__din931 ─────────────────────────────────────────────
    "vis__th__zinc__48__din931": [
        "000012.jpg",  # socket head cap screw technical drawing
        "000015.jpg",  # WEIFENG DIN933 fully threaded bolt (wrong spec)
        "000019.jpg",  # duplicate of 000015
        "000028.jpg",  # yellow zinc bolt diagram
        "000035.jpg",  # flat countersunk Phillips screws
        "000042.jpg",  # grade 8.8 bolt in 4.8 folder
        "000046.jpg",  # plastic knurled thumb screw
        "000056.jpg",  # duplicate of 000002
        "000060.jpg",  # fully threaded short bolt (DIN933 not DIN931)
    ],

    # ── vis__th__zinc__88__din931 ─────────────────────────────────────────────
    "vis__th__zinc__88__din931": [
        "000012.jpg",  # CHC socket screw drawing
        "000016.jpg",  # duplicate of 000004
        "000022.jpg",  # black button head socket screws
        "000024.jpg",  # wing bolt (vis à ailettes)
        "000026.jpg",  # black brut hex bolts (wrong finish)
        "000028.jpg",  # duplicate of 000004/000016
        "000030.jpg",  # fully threaded bolt (DIN933 not DIN931)
        "000037.jpg",  # Chinese ad with human model
        "000042.jpg",  # duplicate DIN933 8.8 bolt
        "000047.jpg",  # spec sheet for knurled thumb screw
        "000056.jpg",  # stainless bolt+nut+washer assemblies
    ],

    # ── vis__th__inox__a2__din933 ─────────────────────────────────────────────
    "vis__th__inox__a2__din933": [
        "000001.jpg",  # stainless threaded rods
        "000007.jpg",  # black structural bolt assembly
        "000014.jpg",  # zinc "A3" bolt (Shenzhen Bede Mold)
        "000023.jpg",  # stainless steel round bars
        "000025.jpg",  # duplicate of 000014
        "000032.jpg",  # duplicate of 000014 (3rd copy)
        "000038.jpg",  # black structural bolts in box
        "000039.jpg",  # A4-70 grade bolt (wrong grade)
        "000044.jpg",  # zinc bolt+nut assortment (SanThriving)
        "000059.jpg",  # stainless steel plate stock (FengYang)
    ],

    # ── vis__th__inox__a4__din933 ─────────────────────────────────────────────
    "vis__th__inox__a4__din933": [
        "000001.jpg",  # HDR bolt+nut+washer assembly
        "000010.jpg",  # steel plate stock collage with phone numbers
        "000036.jpg",  # stainless eye bolt
        "000049.jpg",  # black structural bolts (Qi jing)
        "000051.jpg",  # duplicate of 000044
        "000053.jpg",  # duplicate of 000017
        "000057.jpg",  # duplicate of 000044/000051
    ],

    # ── vis__th__inox__a2__din931 ─────────────────────────────────────────────
    "vis__th__inox__a2__din931": [
        "000006.jpg",  # fully threaded (DIN933 not DIN931)
        "000010.jpg",  # steel plate collage (cross-class dup)
        "000024.jpg",  # stainless round bar stock (MTP)
        "000035.jpg",  # countersunk Phillips screw (TGK M4x20)
        "000048.jpg",  # stainless threaded rod/stud
        "000049.jpg",  # duplicate of 000043
        "000051.jpg",  # gold socket button screws
        "000058.jpg",  # stainless round bar stock
    ],

    # ── vis__th__brut__88__din933 ─────────────────────────────────────────────
    "vis__th__brut__88__din933": [
        "000003.jpg",  # HDR hot-dip galvanized bolt
        "000009.jpg",  # HDR galvanized bolt (JDS 8.8)
        "000011.jpg",  # black TBHC socket screw
        "000017.jpg",  # HDR galvanized bolt
        "000023.jpg",  # black flanged CHC socket screws
        "000038.jpg",  # zinc bolt (wrong finish)
        "000046.jpg",  # slotted round head screw
        "000050.jpg",  # duplicate of 000037
        "000057.jpg",  # duplicate of 000045
    ],

    # ── vis__th__brut__109__din931 ────────────────────────────────────────────
    "vis__th__brut__109__din931": [
        "000011.jpg",  # button head socket screw (TBHC)
        "000012.jpg",  # fully threaded DIN933 (not DIN931)
        "000014.jpg",  # zinc/chrome bolt (wrong finish)
        "000020.jpg",  # bright stainless hex bolt (wrong class)
        "000023.jpg",  # black flanged CHC socket screws
        "000027.jpg",  # flat washer
        "000037.jpg",  # duplicate of 000001
        "000043.jpg",  # duplicate of 000026
        "000045.jpg",  # factory/workshop machines photo
        "000051.jpg",  # duplicate of 000014
    ],

    # ── vis__chc__zinc__din912 ────────────────────────────────────────────────
    "vis__chc__zinc__din912": [
        "000006.jpg",  # VIS CHC dimensions table (no real photo)
        "000010.jpg",  # slotted countersunk flat head screw (vis FHC)
        "000012.jpg",  # carriage bolt (vis BTR)
        "000018.jpg",  # duplicate of 000006
        "000032.jpg",  # duplicate of 000003
        "000036.jpg",  # leveling bolt on square plate
        "000044.jpg",  # duplicate of 000003 (3rd copy)
        "000047.jpg",  # zinc threaded rod
        "000051.jpg",  # duplicate of 000003 (4th copy)
        "000052.jpg",  # black 3D CAD render (no real photo)
    ],

    # ── vis__chc__inox__a2__din912 ────────────────────────────────────────────
    "vis__chc__inox__a2__din912": [
        "000013.jpg",  # duplicate of 000001 (NEWSTAR render)
        "000018.jpg",  # stainless button head (TBHC), wrong subtype
        "000021.jpg",  # duplicate of 000003
        "000029.jpg",  # flat countersunk socket screw (TCHC), wrong subtype
        "000031.jpg",  # duplicate of 000002
        "000032.jpg",  # duplicate of 000020
        "000060.jpg",  # SolidWorks/CAD model render
    ],

    # ── vis__chc__inox__a4__din912 ────────────────────────────────────────────
    "vis__chc__inox__a4__din912": [
        "000008.jpg",  # cross-class dup of inox_a2 folder
        "000014.jpg",  # duplicate of 000008
        "000022.jpg",  # "International Paper Sizes" chart
        "000026.jpg",  # cross-class dup of vis__chc__inox__a2/000002
        "000038.jpg",  # duplicate of 000026
        "000058.jpg",  # "A4" paper size diagram (Chinese)
    ],

    # ── vis__chc__brut__88__din912 ────────────────────────────────────────────
    "vis__chc__brut__88__din912": [
        "000011.jpg",  # office stock photo ("seamless communication")
        "000019.jpg",  # duplicate of 000001
        "000024.jpg",  # slotted set screws (wrong type)
        "000028.jpg",  # VIS CHC dimensions table
        "000040.jpg",  # duplicate of 000028
        "000042.jpg",  # zinc CHC (wrong finish)
        "000043.jpg",  # Anji Xinchi zinc CHC (wrong finish)
        "000046.jpg",  # stainless flanged hex bolt
        "000052.jpg",  # third copy of VIS CHC dimensions table
        "000055.jpg",  # duplicate of 000043
    ],

    # ── vis__chc__brut__129__din912 ───────────────────────────────────────────
    "vis__chc__brut__129__din912": [
        "000010.jpg",  # "12.9 Grade" button head (TBHC), wrong subtype
        "000011.jpg",  # zinc-plated CHC (wrong finish)
        "000019.jpg",  # tiny electronics screw in tweezers
        "000057.jpg",  # duplicate of 000051
        "000058.jpg",  # M12 industrial connector drawing
    ],

    # ── vis__tchc__zinc__din7991 — ALL 12 images bad ─────────────────────────
    "vis__tchc__zinc__din7991": [
        "000009.jpg",  "000012.jpg",  "000015.jpg",  "000016.jpg",
        "000017.jpg",  "000018.jpg",  "000023.jpg",  "000031.jpg",
        "000034.jpg",  "000036.jpg",  "000051.jpg",  "000053.jpg",
    ],

    # ── vis__tbhc__zinc__din7380 — 11/12 bad ─────────────────────────────────
    "vis__tbhc__zinc__din7380": [
        "000007.jpg",  # stainless TBHC (Sweet Hardware), wrong finish
        "000009.jpg",  # technical drawing, no real photo
        "000012.jpg",  # stainless CHC cylinder head, wrong subtype
        "000019.jpg",  # duplicate of 000007
        "000026.jpg",  # duplicate of 000009
        "000031.jpg",  # 3rd copy of Sweet Hardware stainless TBHC
        "000035.jpg",  # stainless CHC (kit-electronique), wrong type+finish
        "000041.jpg",  # zinc CHC cylinder head, wrong subtype
        "000048.jpg",  # stainless flat TCHC screw, wrong type+finish
        "000057.jpg",  # stainless TBHC (wrong finish)
        "000059.jpg",  # "COTES VIS CHC DIN 912" dimensions table
    ],

    # ── vis__btr__zinc__din603 (partial audit) ────────────────────────────────
    "vis__btr__zinc__din603": [
        "000008.jpg",  # DIN603 dimensions table (Hungarian)
        "000011.jpg",  # long coupling barrel nut (wrong product)
        "000016.jpg",  # zinc CHC socket screws (wrong type)
        "000019.jpg",  # duplicate of 000013
        "000022.jpg",  # flat countersunk slotted screws (wrong type)
        "000028.jpg",  # zinc CHC socket screw (wrong type)
        "000041.jpg",  # duplicate of 000028
        "000058.jpg",  # black TCHC flat countersunk socket screw
    ],

    # ── ecrou__hex__zinc__din934 ──────────────────────────────────────────────
    "ecrou__hex__zinc__din934": [
        "000034.jpg",  # pipe clamp (collier de serrage)
        "000046.jpg",  # flat washer (rondelle plate)
        "000060.jpg",  # socket head cap screws (vis CHC)
    ],

    # ── ecrou__hex__inox__a2__din934 ─────────────────────────────────────────
    "ecrou__hex__inox__a2__din934": [
        "000019.jpg",  # duplicate image of stainless nut
        "000031.jpg",  # duplicate of 000019
        "000036.jpg",  # "M2" sci-fi logo / tech animation
    ],

    # ── ecrou__papillon__inox__a2__din315 ────────────────────────────────────
    "ecrou__papillon__inox__a2__din315": [
        "000031.jpg",  # duplicate of another wing nut photo
        "000032.jpg",  # duplicate of 000031
        "000038.jpg",  # eye bolt + wing nut mixed
        "000042.jpg",  # plastic/aluminum star knob
        "000051.jpg",  # duplicate of 000038
    ],

    # ── rondelle__plate__zinc__din125a ────────────────────────────────────────
    "rondelle__plate__zinc__din125a": [
        "000050.jpg",  # stainless washers (wrong class)
    ],

    # ── boulon__inox__a2 ──────────────────────────────────────────────────────
    "boulon__inox__a2": [
        "000012.jpg",  # paper sizes A0–A4 diagram
        "000024.jpg",  # CAD/3D rendering of cylindrical pin
        "000055.jpg",  # bolt/nut/washer assortment kit box
    ],

    # ── ecrou__embase__rond__inox__a2__din6923 ────────────────────────────────
    "ecrou__embase__rond__inox__a2__din6923": [
        "000004.jpg",  # technical drawing only (no real photo)
        "000023.jpg",  # electrical ring terminal / crimp connector
        "000026.jpg",  # duplicate of serrated flange nut
        "000034.jpg",  # thread-cutting die (filière)
        "000035.jpg",  # CAD render of carriage bolt + serrated flange nut
        "000036.jpg",  # round head Phillips machine screws
        "000041.jpg",  # plain hex nut (no embase flange)
        "000050.jpg",  # duplicate of 000026
        "000060.jpg",  # socket wrench tool
    ],

    # ── vis__epaulee__inox__a2__din9841 ──────────────────────────────────────
    "vis__epaulee__inox__a2__din9841": [
        "000011.jpg",  # A4/A3 paper sizes diagram
        "000013.jpg",  # black/oxide shoulder screws (wrong finish)
        "000016.jpg",  # pile of stainless socket head screws
        "000024.jpg",  # Chinese paper sizes table
        "000028.jpg",  # technical drawing of shoulder bolt (no real photo)
        "000032.jpg",  # black oxide socket cap screws (wrong type+finish)
        "000035.jpg",  # Chinese paper/notebook photo
        "000049.jpg",  # black shoulder bolts (wrong finish)
        "000053.jpg",  # dimension drawing only
        "000056.jpg",  # duplicate of 000032
        "000057.jpg",  # "Our Company" marketing page
    ],
}
# fmt: on


def main(dry_run: bool = False) -> None:
    total_bad = sum(len(v) for v in BAD_IMAGES.values())
    mode = "[DRY RUN] " if dry_run else ""
    print(f"{mode}Targeting {total_bad} bad images across {len(BAD_IMAGES)} classes\n")

    deleted = 0
    not_found = 0

    for class_id, filenames in BAD_IMAGES.items():
        class_dir = VAL / class_id
        for fn in filenames:
            path = class_dir / fn
            if path.exists():
                if not dry_run:
                    path.unlink()
                print(f"  {'WOULD DELETE' if dry_run else 'DELETED'}  {class_id}/{fn}")
                deleted += 1
            else:
                print(f"  MISSING   {class_id}/{fn}")
                not_found += 1

    print(f"\n{'[DRY RUN] ' if dry_run else ''}Done.")
    print(f"  {'Would delete' if dry_run else 'Deleted'} : {deleted}")
    print(f"  Not found  : {not_found}")

    if not dry_run and deleted:
        print(
            "\nNext steps:"
            "\n  1. python services/clean_dataset.py   (re-sync train/val splits)"
            "\n  2. Re-train the YOLO11s-cls model"
        )


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    main(dry_run=dry_run)
