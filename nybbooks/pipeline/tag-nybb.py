"""
Tag books using Claude based on their descriptions and a curated tag list.

Usage:
    nybbooks-tag                                       # reads data/processed/books-nybb-images.csv, tags.txt
    nybbooks-tag --input path/to/books.csv             # specify input CSV
    nybbooks-tag --tags path/to/tags.txt               # specify tag file
    nybbooks-tag --output path/to/tagged.csv           # specify output CSV
    nybbooks-tag --overwrite                           # re-tag books that already have tags
    nybbooks-tag --batch-size 5                        # books per API call (default: 5)
"""

import argparse
import json
import time

import anthropic
import pandas as pd


def load_tags(tags_file: str) -> list[str]:
    with open(tags_file) as f:
        tags = [line.strip() for line in f if line.strip()]
    print(f"Loaded {len(tags)} tags from '{tags_file}':")
    for tag in tags:
        print(f"  - {tag}")
    return tags


def build_prompt(batch: list[dict], tags: list[str]) -> str:
    tag_list = "\n".join(f"- {t}" for t in tags)
    books_block = "\n\n".join(
        f'TITLE: {b["title"]}\nDESCRIPTION: {b["description"]}' for b in batch
    )
    return f"""You are a well-read, clever book critic tagging books for a searchable library.
For each book below, select all tags from the provided list that clearly apply based on the description.
Be selective — only apply a tag if it is a genuine, strong match. Most books should get 2–5 tags.
If no tag is a perfect fit, apply at least the most relevant one, even if it's not a 100% match. Never return an empty list.

AVAILABLE TAGS:
{tag_list}

BOOKS TO TAG:
{books_block}

Respond with a single JSON object where each key is the exact book title and each value is a list of applicable tags.
Return only the JSON — no explanation, no markdown, no code fences.

Example format:
{{"Book Title One": ["Tag A", "Tag B"], "Book Title Two": ["Tag C"]}}"""


def tag_batch(
    client: anthropic.Anthropic,
    batch: list[dict],
    tags: list[str],
    retries: int = 3,
) -> dict[str, list[str]]:
    prompt = build_prompt(batch, tags)
    for attempt in range(retries):
        try:
            message = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=2048,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = message.content[0].text.strip()
            print(f"  Raw response preview: {repr(raw[:100])}")

            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
                raw = raw.strip()

            return json.loads(raw)
        except (json.JSONDecodeError, anthropic.APIError) as e:
            print(f"  Attempt {attempt + 1} failed: {e}")
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
    print(f"  Giving up on batch starting with '{batch[0]['title']}'")
    return {}


def tag_books(
    input_csv: str,
    tags_file: str,
    output_csv: str,
    batch_size: int,
    overwrite: bool,
) -> None:
    df = pd.read_csv(input_csv)
    tags = load_tags(tags_file)
    client = anthropic.Anthropic()

    if "tags" not in df.columns:
        df["tags"] = None

    if overwrite:
        to_tag = df.index.tolist()
    else:
        to_tag = df[df["tags"].isna()].index.tolist()

    total = len(to_tag)
    if total == 0:
        print("All books already tagged. Use --overwrite to re-tag.")
        return

    print(f"\nTagging {total} books in batches of {batch_size}...")

    for batch_start in range(0, total, batch_size):
        batch_indices = to_tag[batch_start : batch_start + batch_size]
        batch_rows = df.loc[batch_indices]

        batch = [
            {
                "title": row["title"],
                "description": str(row.get("description", "")),
            }
            for _, row in batch_rows.iterrows()
        ]

        batch_num = batch_start // batch_size + 1
        total_batches = (total + batch_size - 1) // batch_size
        print(f"  Batch {batch_num}/{total_batches}: {[b['title'][:40] for b in batch]}")

        results = tag_batch(client, batch, tags)

        for idx, row in batch_rows.iterrows():
            title = row["title"]
            if title in results:
                df.at[idx, "tags"] = json.dumps(results[title])
            else:
                print(f"    [WARN] No tags returned for '{title}'")
                df.at[idx, "tags"] = json.dumps([])

        df.to_csv(output_csv, index=False)
        time.sleep(0.5)

    tagged_count = df["tags"].notna().sum()
    print(f"\nDone. {tagged_count}/{len(df)} books tagged.")
    print(f"Saved to '{output_csv}'")


def main():
    parser = argparse.ArgumentParser(description="Tag books using Claude.")
    parser.add_argument("--input",      default="data/processed/books-nybb-images.csv", help="Input CSV (default: data/processed/books-nybb-images.csv)")
    parser.add_argument("--tags",       default="tags.txt",                             help="Tag list file (default: tags.txt)")
    parser.add_argument("--output",     default="data/processed/books-nybb-tagged.csv", help="Output CSV (default: data/processed/books-nybb-tagged.csv)")
    parser.add_argument("--batch-size", type=int, default=5,                            help="Books per API call (default: 5)")
    parser.add_argument("--overwrite",  action="store_true",                            help="Re-tag books that already have tags")
    args = parser.parse_args()

    tag_books(args.input, args.tags, args.output, args.batch_size, args.overwrite)


if __name__ == "__main__":
    main()
