#!/usr/bin/env python3
"""Fetch and parse NPR Books We Love metadata into a CSV."""

import csv
import json
import os
import re
import sys
from html.parser import HTMLParser

try:
    import requests
except ImportError:
    sys.exit("requests is required: pip install requests")

BASE_URL = "https://apps.npr.org/best-books"
YEARS = range(2014, 2026)
OUTPUT_FILE = "data/processed/books-npr.csv"
FIELDNAMES = ["year", "title", "author", "genre", "description", "book_picture", "amazon_link", "image_path", "tags"]


class HTMLStripper(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []

    def handle_data(self, data):
        self.parts.append(data)

    def get_text(self):
        return "".join(self.parts)


def strip_html(text):
    s = HTMLStripper()
    s.feed(text or "")
    return s.get_text().strip()


def fetch_json(url):
    resp = requests.get(url, timeout=15)
    if resp.status_code == 404:
        return None
    resp.raise_for_status()
    return resp.json()


def build_amazon_link(book):
    asin = book.get("amazon_asin") or book.get("isbn10")
    if asin:
        return f"https://amazon.com/dp/{asin}?tag=npr-5-20"
    return ""


def get_genre(tags):
    for tag in tags:
        tl = tag.lower()
        if tl == "fiction":
            return "Fiction"
        if tl in ("nonfiction", "non-fiction"):
            return "Nonfiction"
    return ""


def _title(s):
    """Title-case without capitalizing after apostrophes (ASCII or curly)."""
    return re.sub(r"[A-Za-z]+(['\u2019][A-Za-z]+)*", lambda m: m.group(0).capitalize(), s)


def get_display_tags(tags):
    excluded = {"fiction", "nonfiction", "non-fiction", "staff picks"}
    return [_title(t) for t in tags if t.lower() not in excluded]


def make_image_path(year, title):
    safe = re.sub(r"[^\w\s]", "", title).strip().replace(" ", "_")
    return f"data/images/{year}_{safe}.jpeg"


def main():
    rows = []

    for year in YEARS:
        print(f"Fetching {year}...", file=sys.stderr)

        index = fetch_json(f"{BASE_URL}/{year}.json")
        if index is None:
            print(f"  No data for {year}, skipping", file=sys.stderr)
            continue

        detail = fetch_json(f"{BASE_URL}/{year}-detail.json") or {}

        for book in index:
            book_id = str(book.get("id"))
            merged = {**book, **(detail.get(book_id, {}))}

            tags = merged.get("tags", [])
            cover = merged.get("cover", "")
            title = merged.get("title", "")

            rows.append({
                "year": year,
                "title": title,
                "author": merged.get("author", ""),
                "genre": get_genre(tags),
                "description": strip_html(merged.get("text", "")),
                "book_picture": f"{BASE_URL}/assets/synced/covers/{year}/{cover}.jpg" if cover else "",
                "amazon_link": build_amazon_link(merged),
                "image_path": make_image_path(year, title),
                "tags": json.dumps(get_display_tags(tags), ensure_ascii=False),
            })

        print(f"  {len(index)} books", file=sys.stderr)

    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)

    years_found = len({r["year"] for r in rows})
    print(f"\nWrote {len(rows)} books across {years_found} years to {OUTPUT_FILE}", file=sys.stderr)


if __name__ == "__main__":
    main()
