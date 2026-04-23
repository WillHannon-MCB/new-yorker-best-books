"""
Generate sentence embeddings from book descriptions and save them to disk.

Usage:
    nybbooks-embed                                         # reads data/processed/books-combined.csv
    nybbooks-embed --input path/to/books.csv               # specify input CSV
    nybbooks-embed --output path/to/embeddings.npy         # specify output file
"""

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer


def build_embeddings(input_csv: str, output_file: str, model_name: str) -> None:
    print(f"Loading data from '{input_csv}'...")
    df = pd.read_csv(input_csv)

    if "description" not in df.columns:
        raise ValueError("Input CSV must have a 'description' column.")

    descriptions = df["description"].fillna("").tolist()
    print(f"  {len(descriptions)} books loaded.")

    print(f"\nLoading model '{model_name}'...")
    print("  (This will download ~90 MB the first time, then cache locally.)")
    model = SentenceTransformer(model_name)

    print("\nGenerating embeddings...")
    embeddings = model.encode(
        descriptions,
        show_progress_bar=True,
        batch_size=64,
        convert_to_numpy=True,
    )
    print(f"  Embeddings shape: {embeddings.shape}")

    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    norms = np.where(norms == 0, 1, norms)
    embeddings_normalised = embeddings / norms

    output_path = Path(output_file)
    np.save(output_path, embeddings_normalised)
    print(f"\nSaved normalised embeddings to '{output_path}'")
    print("Done.")


def main():
    parser = argparse.ArgumentParser(description="Build sentence embeddings from book descriptions.")
    parser.add_argument("--input",  default="data/processed/books-combined.csv", help="Input CSV (default: data/processed/books-combined.csv)")
    parser.add_argument("--output", default="data/embeddings.npy",               help="Output .npy file (default: data/embeddings.npy)")
    parser.add_argument("--model",  default="all-mpnet-base-v2",                   help="Sentence-transformers model name (default: all-mpnet-base-v2)")
    args = parser.parse_args()

    build_embeddings(args.input, args.output, args.model)


if __name__ == "__main__":
    main()
