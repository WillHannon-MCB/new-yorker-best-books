#!/usr/bin/env python3
"""Process raw NPR books CSV: filter and remap tags to match tags.txt."""

import csv
import json
import sys

INPUT_FILE = "data/processed/books-npr.csv"
OUTPUT_FILE = "data/processed/books-npr-processed.csv"

FIELDNAMES = [
    "year", "title", "author", "genre", "description",
    "book_picture", "amazon_link", "image_path", "tags",
]

# Books containing any of these tags are removed entirely.
EXCLUDE_TAGS = {
    "Comics & Graphic Novels",
    "Cookbooks & Food",
    "Kids' Books",
    "Young Adult",
}

# Maps NPR tags to NYer tags. None = drop the tag. List = expand to multiple tags.
TAG_MAP = {
    "Biography & Memoir":               "Biography & Memoir",
    "Book Club Ideas":                   None,
    "Eye-Opening Reads":                 None,
    "Family Matters":                    "Family Matters",
    "For Art Lovers":                    "Art",
    "For History Lovers":                "History",
    "For Music Lovers":                  "Music",
    "For Sports Lovers":                 None,
    "Funny Stuff":                       "Humor & Comedy",
    "Historical Fiction":                "Historical Fiction",
    "Identity & Culture":               "Identity & Culture",
    "It's All Geek To Me":              None,
    "Let\u2019s Talk About Sex":         None,
    "Love & Romance":                    "Love & Romance",
    "Mysteries & Thrillers":            ["Mysteries", "Thrillers"],
    "No Biz Like Show Biz":             None,
    "Rather Long":                       None,
    "Rather Short":                      None,
    "Sci Fi, Fantasy & Speculative Fiction": "Sci Fi, Fantasy & Speculative Fiction",
    "Science!":                          "Science",
    "Seriously Great Writing":           "Seriously Great Writing",
    "Short Stories, Essays & Poetry":   "Short Stories & Essays",
    "Tales From Around The World":      "Tales From Around The World",
    "The Dark Side":                    "Dark",
    "The States We\u2019re In":          "Americana",
}


def map_tags(raw_tags: list[str]) -> list[str]:
    result = []
    for tag in raw_tags:
        mapped = TAG_MAP.get(tag)
        if mapped is None:
            continue
        if isinstance(mapped, list):
            result.extend(mapped)
        else:
            result.append(mapped)
    # Deduplicate while preserving order.
    seen = set()
    return [t for t in result if not (t in seen or seen.add(t))]


def main():
    rows_in = rows_out = excluded = no_genre = 0

    with open(INPUT_FILE, newline="", encoding="utf-8") as fin, \
         open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as fout:

        reader = csv.DictReader(fin)
        writer = csv.DictWriter(fout, fieldnames=FIELDNAMES)
        writer.writeheader()

        for row in reader:
            rows_in += 1
            tags = json.loads(row.get("tags") or "[]")

            if EXCLUDE_TAGS & set(tags):
                excluded += 1
                continue

            if not row.get("genre"):
                no_genre += 1
                continue

            row["tags"] = json.dumps(map_tags(tags), ensure_ascii=False)
            writer.writerow({k: row.get(k, "") for k in FIELDNAMES})
            rows_out += 1

    print(f"Input:        {rows_in} books", file=sys.stderr)
    print(f"Excluded:     {excluded} (filtered tags)", file=sys.stderr)
    print(f"No genre:     {no_genre}", file=sys.stderr)
    print(f"Output:       {rows_out} books → {OUTPUT_FILE}", file=sys.stderr)


if __name__ == "__main__":
    main()
