"""
Run the full data pipeline end-to-end.

Steps:
  ── New Yorker Best Books ──────────────────────────────────────────
  1. extract-nybb   — parse HTML files           → books-nybb.csv
  2. download-nybb  — fetch cover images         → books-nybb-images.csv + data/images/
  3. tag-nybb       — assign tags via Claude     → books-nybb-tagged.csv

  ── NPR Book Concierge ────────────────────────────────────────────
  4. download-npr   — fetch NPR JSON             → books-npr.csv
  5. process-npr    — filter & remap tags        → books-npr-processed.csv

  ── Combined ──────────────────────────────────────────────────────
  6. join           — merge sources, deduplicate → books-combined.csv
  7. embed          — build sentence embeddings  → embeddings.npy

Usage:
    nybbooks-run                   # run all steps; skip any whose output already exists
    nybbooks-run --force           # re-run every step from scratch
    nybbooks-run --skip-download   # skip cover image download (Step 2)
    nybbooks-run --skip-tag        # skip Claude tagging (Step 3, no API key needed)
    nybbooks-run --skip-npr        # skip NPR fetch + process (Steps 4–5)
"""

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

PIPELINE_DIR = Path(__file__).parent
DATA_DIR      = Path("data")
PROCESSED_DIR = DATA_DIR / "processed"

BOOKS_NYBB_CSV       = PROCESSED_DIR / "books-nybb.csv"
BOOKS_NYBB_IMG_CSV   = PROCESSED_DIR / "books-nybb-images.csv"
BOOKS_NYBB_TAG_CSV   = PROCESSED_DIR / "books-nybb-tagged.csv"
BOOKS_NPR_CSV        = PROCESSED_DIR / "books-npr.csv"
BOOKS_NPR_PROC_CSV   = PROCESSED_DIR / "books-npr-processed.csv"
BOOKS_COMBINED_CSV   = PROCESSED_DIR / "books-combined.csv"
EMBEDDINGS_NPY       = DATA_DIR / "embeddings.npy"


def _run(script: str) -> None:
    result = subprocess.run([sys.executable, str(PIPELINE_DIR / script)])
    if result.returncode != 0:
        sys.exit(result.returncode)


def _header(label: str) -> None:
    print(f"\n{'─' * 56}")
    print(f"  {label}")
    print(f"{'─' * 56}")


def _step(label: str, output: Path, force: bool, fn) -> None:
    if not force and output.exists():
        print(f"\n[skip] {label}  ({output.name} exists)")
        return
    _header(label)
    fn()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the full Best Books data pipeline."
    )
    parser.add_argument("--force",         action="store_true", help="Re-run all steps even if output exists")
    parser.add_argument("--skip-download", action="store_true", help="Skip cover image download (Step 2)")
    parser.add_argument("--skip-tag",      action="store_true", help="Skip Claude API tagging (Step 3)")
    parser.add_argument("--skip-npr",      action="store_true", help="Skip NPR fetch and process (Steps 4–5)")
    args = parser.parse_args()

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    # ── New Yorker Best Books ────────────────────────────────────
    _step(
        "Step 1/7 — Extract NYBB metadata from HTML",
        BOOKS_NYBB_CSV, args.force,
        lambda: _run("extract-nybb.py"),
    )

    if args.skip_download:
        print(f"\n[skip] Step 2/7 — Download NYBB cover images  (--skip-download)")
        if not BOOKS_NYBB_IMG_CSV.exists():
            shutil.copy(BOOKS_NYBB_CSV, BOOKS_NYBB_IMG_CSV)
    else:
        _step(
            "Step 2/7 — Download NYBB cover images",
            BOOKS_NYBB_IMG_CSV, args.force,
            lambda: _run("download-nybb.py"),
        )

    if args.skip_tag:
        print(f"\n[skip] Step 3/7 — Tag NYBB books with Claude  (--skip-tag)")
    else:
        _step(
            "Step 3/7 — Tag NYBB books with Claude",
            BOOKS_NYBB_TAG_CSV, args.force,
            lambda: _run("tag-nybb.py"),
        )

    # ── NPR Book Concierge ───────────────────────────────────────
    if args.skip_npr:
        print(f"\n[skip] Step 4/7 — Download NPR books  (--skip-npr)")
        print(f"\n[skip] Step 5/7 — Process NPR books   (--skip-npr)")
    else:
        _step(
            "Step 4/7 — Download NPR Book Concierge data",
            BOOKS_NPR_CSV, args.force,
            lambda: _run("download-npr.py"),
        )
        _step(
            "Step 5/7 — Process & filter NPR books",
            BOOKS_NPR_PROC_CSV, args.force,
            lambda: _run("process-npr.py"),
        )

    # ── Combined ─────────────────────────────────────────────────
    _step(
        "Step 6/7 — Join NYBB + NPR, deduplicate",
        BOOKS_COMBINED_CSV, args.force,
        lambda: _run("join.py"),
    )

    _step(
        "Step 7/7 — Generate sentence embeddings",
        EMBEDDINGS_NPY, args.force,
        lambda: _run("embed.py"),
    )

    print(f"\n{'═' * 56}")
    print("  Pipeline complete!")
    print(f"{'═' * 56}")
    print(f"  Dataset:    {BOOKS_COMBINED_CSV}")
    print(f"  Embeddings: {EMBEDDINGS_NPY}")
    print("\n  Run 'nybbooks' to start the search app.")


if __name__ == "__main__":
    main()
