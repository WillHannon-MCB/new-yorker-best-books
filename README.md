# New Yorker Best Books

Semantic search over The New Yorker's annual "Best Books" lists (2022–2026). Search 1,446 books with free-form text queries via a Streamlit web app.

## Setup

```bash
poetry install
```

The sentence-transformers model (`all-mpnet-base-v2`, ~90 MB) is downloaded automatically on first run.

Set your Anthropic API key before running the tagging step:

```bash
export ANTHROPIC_API_KEY="sk-..."
```

## Running the app

```bash
poetry run nybbooks
```

Launches the Streamlit app in your browser. Enter a query like `"dark family saga"` or `"funny memoir"` and optionally filter by genre or tag.

## Pipeline

The processed data files (`data/processed/books_tagged.csv`, `data/embeddings.npy`) are included. To rebuild them from the source HTML:

### Run the full pipeline at once

```bash
poetry run nybbooks-run
```

Each step is skipped automatically if its output already exists. Use `--force` to re-run everything from scratch, or see individual flags:

```
--force          Re-run all steps even if output exists
--skip-download  Skip cover image download
--skip-tag       Skip Claude API tagging (no API key needed)
```

### Run steps individually

```bash
# 1. Parse HTML → data/processed/books.csv
poetry run nybbooks-extract

# 2. Download cover images → data/processed/books_with_images.csv + data/images/
poetry run nybbooks-download

# 3. Build sentence embeddings → data/embeddings.npy
poetry run nybbooks-embed

# 4. Tag books via Claude API → data/processed/books_tagged.csv
export ANTHROPIC_API_KEY="sk-..."
poetry run nybbooks-tag
```

Each script accepts `--help` for available options (custom paths, model names, batch sizes, etc.).

## Project structure

```
├── pyproject.toml
├── tags.txt                           # 22 curated tag categories
├── data/
│   ├── raw/                           # Source HTML from The New Yorker (2022–2026)
│   ├── processed/                     # Pipeline output CSVs (gitignored)
│   │   ├── books.csv                  #   step 1: title, author, genre, description, URLs
│   │   ├── books_with_images.csv      #   step 2: + local image_path column
│   │   └── books_tagged.csv           #   step 4: + tags column (final dataset)
│   ├── embeddings.npy                 # Sentence embeddings, 1446 × 768 (gitignored)
│   └── images/                        # Downloaded cover images (gitignored)
└── nybbooks/
    ├── app.py                         # Streamlit search app
    └── pipeline/
        ├── run.py                     # Full-pipeline entry point
        ├── extract.py                 # Step 1: parse HTML → books.csv
        ├── download.py                # Step 2: download cover images
        ├── embed.py                   # Step 3: build sentence embeddings
        └── tag.py                     # Step 4: tag books via Claude API
```

## Tags

The 22 curated categories used for filtering:

Biography & Memoir · Graphic Novels · Historical Fiction · Love & Romance · Mysteries · Thrillers · Sci Fi, Fantasy & Speculative Fiction · Short Stories & Essays · Family Matters · Art · History · Music · Humor & Comedy · Identity & Culture · Tales From Around The World · Dark · Science · War & Conflict · Nature & Environment · True Crime · Politics & Power · Americana

## Data files

| File | Description |
|---|---|
| `data/raw/*.html` | Raw HTML pages from The New Yorker (one per year, 2022–2026) |
| `data/processed/books.csv` | Extracted metadata: title, author, genre, description, image URL, Amazon link |
| `data/processed/books_with_images.csv` | Same as above with `image_path` column pointing to local cover images |
| `data/processed/books_tagged.csv` | Final dataset — all columns plus `tags` (JSON array) |
| `data/embeddings.npy` | Normalised sentence embeddings (1,446 × 768 float32) |
| `data/images/` | Downloaded book cover images |
