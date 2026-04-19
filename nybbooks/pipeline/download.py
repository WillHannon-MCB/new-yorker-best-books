"""
Download book cover images and add a relative path column to the dataframe.

Usage:
    nybbooks-download                                    # reads data/processed/books.csv
    nybbooks-download --input path/to/books.csv          # specify input CSV
    nybbooks-download --output path/to/out.csv           # specify output CSV
    nybbooks-download --images-dir path/to/covers        # specify image folder (default: data/images/)
"""

import argparse
import time
from pathlib import Path
from urllib.parse import urlparse

import pandas as pd
import requests


def url_to_filename(url: str, row: pd.Series) -> str:
    title = str(row.get("title", "")).strip()
    if title:
        safe_title = "".join(c if c.isalnum() or c in " -_" else "_" for c in title)
        safe_title = safe_title.strip().replace(" ", "_")
    else:
        safe_title = "book"

    path = urlparse(url).path
    suffix = Path(path).suffix or ".jpg"

    year = str(row.get("year", ""))
    return f"{year}_{safe_title}{suffix}" if year else f"{safe_title}{suffix}"


def download_images(input_csv: str, output_csv: str, images_dir: str) -> None:
    df = pd.read_csv(input_csv)

    if "book_picture" not in df.columns:
        raise ValueError("Input CSV must have a 'book_picture' column.")

    images_path = Path(images_dir)
    images_path.mkdir(parents=True, exist_ok=True)

    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0"})

    local_paths = []
    total = len(df)

    for i, row in df.iterrows():
        url = str(row.get("book_picture", "")).strip()

        if not url:
            local_paths.append("")
            continue

        filename = url_to_filename(url, row)
        dest = images_path / filename

        if dest.exists():
            local_paths.append(str(dest))
            print(f"[{i+1}/{total}] Skipped (exists): {filename}")
            continue

        try:
            response = session.get(url, timeout=15)
            response.raise_for_status()
            dest.write_bytes(response.content)
            local_paths.append(str(dest))
            print(f"[{i+1}/{total}] Downloaded: {filename}")
        except requests.RequestException as e:
            print(f"[{i+1}/{total}] FAILED: {url}\n  {e}")
            local_paths.append("")

        time.sleep(0.1)

    df["image_path"] = local_paths
    df.to_csv(output_csv, index=False)
    success = sum(1 for p in local_paths if p)
    print(f"\nDone. {success}/{total} images downloaded.")
    print(f"Saved updated dataframe to '{output_csv}'")


def main():
    parser = argparse.ArgumentParser(description="Download book cover images and update the CSV.")
    parser.add_argument("--input",      default="data/processed/books.csv",             help="Input CSV (default: data/processed/books.csv)")
    parser.add_argument("--output",     default="data/processed/books_with_images.csv", help="Output CSV (default: data/processed/books_with_images.csv)")
    parser.add_argument("--images-dir", default="data/images",                          help="Folder to save images (default: data/images/)")
    args = parser.parse_args()

    download_images(args.input, args.output, args.images_dir)


if __name__ == "__main__":
    main()
