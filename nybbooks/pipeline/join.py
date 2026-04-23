#!/usr/bin/env python3
"""Join New Yorker and NPR book CSVs, deduplicating by title+author."""

import csv
import json
import re
import sys

NYR_FILE = "data/processed/books-nybb-tagged.csv"
NPR_FILE = "data/processed/books-npr-processed.csv"
OUTPUT_FILE = "data/processed/books-combined.csv"

FIELDNAMES = [
    "year", "title", "author", "genre", "description",
    "book_picture", "amazon_link", "image_path", "tags",
]


def normalize(text: str) -> str:
    """Lowercase, strip non-alphanumeric (except spaces), collapse whitespace."""
    text = text.lower()
    text = re.sub(r"[^\w\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    # Drop leading articles so "The Road" == "Road"
    text = re.sub(r"^(the|a|an) ", "", text)
    return text


def dedup_key(row: dict) -> tuple[str, str]:
    title_key = normalize(row.get("title", ""))
    # For authors, normalize and sort individual names to handle reordering.
    author_raw = normalize(row.get("author", ""))
    author_key = " ".join(sorted(author_raw.split()))
    return (title_key, author_key)


def add_source_tag(row: dict, tag: str) -> dict:
    tags = json.loads(row.get("tags") or "[]")
    if tag not in tags:
        tags.append(tag)
    row["tags"] = json.dumps(tags, ensure_ascii=False)
    return row


def load_csv(path: str) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def main():
    nyr_rows = load_csv(NYR_FILE)
    npr_rows = load_csv(NPR_FILE)

    # Tag each source.
    nyr_rows = [add_source_tag(r, "New Yorker Pick") for r in nyr_rows]
    npr_rows = [add_source_tag(r, "NPR Pick") for r in npr_rows]

    # Build a set of keys from New Yorker books.
    nyr_keys = {dedup_key(r) for r in nyr_rows}

    # Filter NPR rows, logging any duplicates.
    npr_unique = []
    duplicates = []
    for row in npr_rows:
        key = dedup_key(row)
        if key in nyr_keys:
            duplicates.append(row)
        else:
            npr_unique.append(row)

    combined = nyr_rows + npr_unique

    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        for row in combined:
            writer.writerow({k: row.get(k, "") for k in FIELDNAMES})

    print(f"New Yorker books:  {len(nyr_rows)}", file=sys.stderr)
    print(f"NPR books:         {len(npr_rows)}", file=sys.stderr)
    print(f"Duplicates removed:{len(duplicates)}", file=sys.stderr)
    print(f"Combined total:    {len(combined)} → {OUTPUT_FILE}", file=sys.stderr)

    if duplicates:
        print("\nDuplicates (NPR removed, New Yorker kept):", file=sys.stderr)
        for r in duplicates:
            print(f"  {r['year']}  {r['title']} — {r['author']}", file=sys.stderr)


if __name__ == "__main__":
    main()
