"""
Run the full data pipeline end-to-end: extract → download → embed → tag.

Steps:
  1. Extract  — parse HTML files in data/raw/ → data/processed/books.csv
  2. Download — fetch cover images           → data/processed/books_with_images.csv + data/images/
  3. Embed    — build sentence embeddings    → data/embeddings.npy
  4. Tag      — assign tags via Claude API   → data/processed/books_tagged.csv

Usage:
    nybbooks-run                  # run all steps; skip any whose output already exists
    nybbooks-run --force          # re-run every step from scratch
    nybbooks-run --skip-download  # skip image download (images already present)
    nybbooks-run --skip-tag       # skip Claude tagging (no ANTHROPIC_API_KEY needed)
"""

import argparse
import sys
from pathlib import Path

DATA_DIR = Path("data")
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"

BOOKS_CSV = PROCESSED_DIR / "books.csv"
BOOKS_WITH_IMAGES_CSV = PROCESSED_DIR / "books_with_images.csv"
BOOKS_TAGGED_CSV = PROCESSED_DIR / "books_tagged.csv"
EMBEDDINGS_NPY = DATA_DIR / "embeddings.npy"
IMAGES_DIR = DATA_DIR / "images"
TAGS_FILE = Path("tags.txt")


def _header(label: str) -> None:
    print(f"\n{'─' * 50}")
    print(f"  {label}")
    print(f"{'─' * 50}")


def _run_step(label: str, output: Path, force: bool, fn) -> None:
    if not force and output.exists():
        print(f"\n[skip] {label}  ({output} already exists)")
        return
    _header(label)
    fn()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the full New Yorker Best Books data pipeline."
    )
    parser.add_argument("--force",         action="store_true", help="Re-run all steps even if output exists")
    parser.add_argument("--skip-download", action="store_true", help="Skip cover image download")
    parser.add_argument("--skip-tag",      action="store_true", help="Skip Claude API tagging")
    args = parser.parse_args()

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    from nybbooks.pipeline.extract import extract_books
    from nybbooks.pipeline.download import download_images
    from nybbooks.pipeline.embed import build_embeddings
    from nybbooks.pipeline.tag import tag_books

    _run_step(
        "Step 1/4 — Extract book metadata from HTML",
        BOOKS_CSV,
        args.force,
        lambda: extract_books(str(RAW_DIR), str(BOOKS_CSV)),
    )

    if not args.skip_download:
        _run_step(
            "Step 2/4 — Download cover images",
            BOOKS_WITH_IMAGES_CSV,
            args.force,
            lambda: download_images(str(BOOKS_CSV), str(BOOKS_WITH_IMAGES_CSV), str(IMAGES_DIR)),
        )
    else:
        print("\n[skip] Step 2/4 — Download cover images  (--skip-download)")
        if not BOOKS_WITH_IMAGES_CSV.exists():
            import shutil
            shutil.copy(str(BOOKS_CSV), str(BOOKS_WITH_IMAGES_CSV))

    _run_step(
        "Step 3/4 — Generate sentence embeddings",
        EMBEDDINGS_NPY,
        args.force,
        lambda: build_embeddings(str(BOOKS_WITH_IMAGES_CSV), str(EMBEDDINGS_NPY), "all-mpnet-base-v2"),
    )

    if not args.skip_tag:
        _run_step(
            "Step 4/4 — Tag books with Claude",
            BOOKS_TAGGED_CSV,
            args.force,
            lambda: tag_books(str(BOOKS_WITH_IMAGES_CSV), str(TAGS_FILE), str(BOOKS_TAGGED_CSV), 5, False),
        )
    else:
        print("\n[skip] Step 4/4 — Tag books with Claude  (--skip-tag)")

    print(f"\n{'═' * 50}")
    print("  Pipeline complete!")
    print(f"{'═' * 50}")
    print(f"  Dataset:    {BOOKS_TAGGED_CSV}")
    print(f"  Embeddings: {EMBEDDINGS_NPY}")
    print("\n  Run 'nybbooks' to start the search app.")


if __name__ == "__main__":
    main()
