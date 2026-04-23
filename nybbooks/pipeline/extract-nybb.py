"""
Extract book data from New Yorker "Best Books of 20XX" HTML files.

Usage:
    nybbooks-extract                           # processes all HTML files in data/raw/
    nybbooks-extract --dir path/to/html        # specify a different folder
    nybbooks-extract --output path/to/out.csv  # specify output CSV path
"""

import json
import re
import glob
import argparse
from pathlib import Path

import pandas as pd
from bs4 import BeautifulSoup


def extract_year_from_filename(filepath: str) -> str:
    match = re.search(r"(\d{4})", Path(filepath).stem)
    return match.group(1) if match else "unknown"


def get_amazon_links(soup: BeautifulSoup) -> dict[str, str]:
    amazon_map = {}
    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"]
        if "cna.st/affiliate-link" in href and a_tag.get_text(strip=True) == "Amazon":
            li = a_tag.find_parent("li")
            if li:
                title_el = li.find("h3")
                if title_el:
                    title = title_el.get_text(strip=True)
                    amazon_map[title] = href
    return amazon_map


def parse_html_file(filepath: str) -> list[dict]:
    with open(filepath, encoding="utf-8") as f:
        content = f.read()

    soup = BeautifulSoup(content, "html.parser")
    year = extract_year_from_filename(filepath)

    books_json = []
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "")
        except (json.JSONDecodeError, TypeError):
            continue
        if data.get("@type") == "ItemList" and "itemListElement" in data:
            books_json = data["itemListElement"]
            break

    if not books_json:
        print(f"  [WARN] No ItemList JSON-LD found in {filepath}")
        return []

    amazon_map = get_amazon_links(soup)

    rows = []
    for item in books_json:
        raw_authors = item.get("author", "")
        if isinstance(raw_authors, str):
            author_names = raw_authors
        elif isinstance(raw_authors, dict):
            author_names = raw_authors.get("name", "")
        elif isinstance(raw_authors, list):
            author_names = ", ".join(
                a.get("name", "") for a in raw_authors if isinstance(a, dict)
            )
        else:
            author_names = ""

        title = item.get("name", "").strip()

        rows.append(
            {
                "year": year,
                "title": title,
                "author": author_names,
                "genre": item.get("genre", ""),
                "description": item.get("about", "").strip(),
                "book_picture": item.get("image", ""),
                "amazon_link": amazon_map.get(title, ""),
            }
        )

    return rows


def extract_books(html_dir: str, output_csv: str) -> None:
    html_files = sorted(glob.glob(f"{html_dir}/*.html"))
    if not html_files:
        print(f"No HTML files found in '{html_dir}/'. Check the --dir argument.")
        return

    all_rows = []
    for filepath in html_files:
        print(f"Processing {filepath} ...")
        rows = parse_html_file(filepath)
        print(f"  -> {len(rows)} books found")
        all_rows.extend(rows)

    if not all_rows:
        print("No data extracted. Exiting.")
        return

    output_path = Path(output_csv)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    df = pd.DataFrame(all_rows, columns=["year", "title", "author", "genre", "description", "book_picture", "amazon_link"])
    df.to_csv(output_csv, index=False)
    print(f"\nSaved {len(df)} rows to '{output_csv}'")


def main():
    parser = argparse.ArgumentParser(description="Extract book data from New Yorker HTML files.")
    parser.add_argument("--dir",    default="data/raw",                 help="Folder containing HTML files (default: data/raw)")
    parser.add_argument("--output", default="data/processed/books-nybb.csv", help="Output CSV path (default: data/processed/books-nybb.csv)")
    args = parser.parse_args()

    extract_books(args.dir, args.output)


if __name__ == "__main__":
    main()
