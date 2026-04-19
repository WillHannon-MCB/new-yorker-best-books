"""Streamlit app for searching New Yorker Best Books."""

import json
import subprocess
import sys
from pathlib import Path

import markdown as md
import numpy as np
import pandas as pd
import streamlit as st
from sentence_transformers import SentenceTransformer

MODEL_NAME = "all-mpnet-base-v2"
CSV_PATH = "data/processed/books_tagged.csv"
EMBEDDINGS_PATH = "data/embeddings.npy"
TAGS_PATH = "tags.txt"

GENRE_COLORS = {
    "Fiction": ("#2D6A4F", "#d8f3dc"),
    "Nonfiction": ("#1D3557", "#dbe9f9"),
    "Poetry": ("#6B2737", "#f9dde2"),
}


# ── Data loading ──────────────────────────────────────────────────────────────

@st.cache_resource
def load_model() -> SentenceTransformer:
    return SentenceTransformer(MODEL_NAME)


@st.cache_resource
def load_data() -> tuple[pd.DataFrame, np.ndarray, list[str]]:
    csv = Path(CSV_PATH) if Path(CSV_PATH).exists() else Path("data/processed/books_with_images.csv")
    df = pd.read_csv(csv)
    embeddings = np.load(EMBEDDINGS_PATH)
    tags = [
        line.strip()
        for line in Path(TAGS_PATH).read_text().splitlines()
        if line.strip()
    ]
    return df, embeddings, tags


# ── Helpers ───────────────────────────────────────────────────────────────────

def parse_tags(cell) -> list[str]:
    try:
        return json.loads(cell) if isinstance(cell, str) else []
    except (json.JSONDecodeError, TypeError):
        return []


GENRE_OPTIONS = ["Fiction", "Nonfiction", "Poetry"]


def get_results(
    query: str,
    df: pd.DataFrame,
    embeddings: np.ndarray,
    model: SentenceTransformer,
    top_k: int,
    selected_tags: list[str],
) -> pd.DataFrame:
    selected_genres = [t for t in selected_tags if t in GENRE_OPTIONS]
    selected_topic_tags = [t for t in selected_tags if t not in GENRE_OPTIONS]

    # Genre mask: book must match ANY selected genre (OR logic)
    if selected_genres and "genre" in df.columns:
        genre_mask = df["genre"].isin(selected_genres).values
    else:
        genre_mask = np.ones(len(df), dtype=bool)

    # Tag mask: book must contain ALL selected topic tags (AND logic)
    if selected_topic_tags and "tags" in df.columns:
        tag_mask = df["tags"].apply(
            lambda cell: all(t in parse_tags(cell) for t in selected_topic_tags)
        ).values
    else:
        tag_mask = np.ones(len(df), dtype=bool)

    tag_mask = tag_mask & genre_mask

    if query.strip():
        query_vec = model.encode([query], convert_to_numpy=True)
        query_vec = query_vec / np.linalg.norm(query_vec)
        scores = (embeddings @ query_vec.T).flatten()

        # Push tag-filtered-out books to the bottom
        masked = scores.copy()
        masked[~tag_mask] = -np.inf

        top_idx = np.argsort(masked)[::-1][:top_k]
        top_idx = top_idx[np.isfinite(masked[top_idx])]  # drop excluded books

        result = df.iloc[top_idx].copy()
        result["_score"] = scores[top_idx].round(3)
    else:
        result = df[tag_mask].sort_values("year", ascending=False).head(top_k).copy()

    return result


# ── Card rendering ────────────────────────────────────────────────────────────

def genre_badge(genre: str) -> str:
    fg, bg = GENRE_COLORS.get(genre, ("#444", "#eee"))
    return (
        f'<span style="background:{bg};color:{fg};padding:2px 10px;'
        f'border-radius:12px;font-size:0.72rem;font-weight:700;'
        f'letter-spacing:0.03em">{genre}</span>'
    )


def tag_pills_html(tags: list[str]) -> str:
    return " ".join(
        f'<span style="background:#f0f2f6;color:#555;padding:2px 8px;'
        f'border-radius:8px;font-size:0.70rem;display:inline-block;margin:1px">{t}</span>'
        for t in tags
    )


def render_card(row: pd.Series) -> None:
    with st.container(border=True):
        # Cover image — prefer local file, fall back to remote URL
        img_path = str(row.get("image_path") or "")
        img_url = str(row.get("book_picture") or "")
        if img_path and Path(img_path).exists():
            st.image(img_path, width="stretch")
        elif img_url:
            st.image(img_url, width="stretch")

        # Title
        title = str(row.get("title") or "Unknown")
        st.markdown(f"**{title}**")

        # Author + year (muted)
        author = str(row.get("author") or "")
        year = str(row.get("year") or "")
        st.caption(" · ".join(x for x in [author, year] if x))

        # Genre badge + tags
        genre = str(row.get("genre") or "")
        tags = parse_tags(row.get("tags"))
        badge = genre_badge(genre) if genre else ""
        pills = tag_pills_html(tags) if tags else ""
        if badge or pills:
            st.markdown(
                f'<div style="margin:4px 0 6px">{badge}&nbsp;&nbsp;{pills}</div>',
                unsafe_allow_html=True,
            )

        # Description
        desc = str(row.get("description") or "")
        if desc:
            desc_html = md.markdown(desc)
            if len(desc) > 300:
                preview = desc[:300]
                preview_html = md.markdown(preview)
                st.markdown(
                    f'<details style="margin:4px 0 2px">'
                    f'<summary style="list-style:none;-webkit-appearance:none;'
                    f'cursor:pointer;display:block">'
                    f'<span class="desc-short">{preview_html}… '
                    f'<small style="color:#888;font-size:0.8em">(more)</small></span>'
                    f'<span class="desc-full" style="display:none">{desc_html} '
                    f'<small style="color:#888;font-size:0.8em">(less)</small></span>'
                    f'</summary>'
                    f'</details>'
                    f'<style>'
                    f'details[open] .desc-short{{display:none}}'
                    f'details[open] .desc-full{{display:inline!important}}'
                    f'</style>',
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(desc_html, unsafe_allow_html=True)

        # Amazon link
        amazon = str(row.get("amazon_link") or "")
        if amazon.strip():
            st.markdown('<div style="margin-top:10px"></div>', unsafe_allow_html=True)
            st.link_button("Buy on Amazon →", amazon, type="tertiary")


# ── App ───────────────────────────────────────────────────────────────────────

def run() -> None:
    st.set_page_config(
        page_title="New Yorker Best Books",
        page_icon="📚",
        layout="wide",
    )

    st.markdown(
        """
        <style>
        /* Tighten card padding */
        div[data-testid="stVerticalBlockBorderWrapper"] > div {
            padding: 12px 14px 10px;
        }
        /* Remove extra margin under images inside cards */
        div[data-testid="stVerticalBlockBorderWrapper"] img {
            border-radius: 4px;
            margin-bottom: 6px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.title("New Yorker Best Books")
    st.caption("Semantic search across 1,446 curated book recommendations from The New Yorker's Best Books lists, 2022–2026.")

    model = load_model()
    df, embeddings, all_tags = load_data()

    # ── Search bar ─────────────────────────────────────────────────────────
    query = st.text_input(
        "search",
        placeholder="e.g.  dark family saga · funny memoir · nature writing",
        label_visibility="collapsed",
        help=(
            "**Semantic search** — matches books by meaning, not keywords.\n\n"
            "Queries like *\"grief and memory\"* or *\"funny essay collection\"* work well "
            "because results are ranked by how closely a book's description aligns with your idea, "
            "not whether those exact words appear.\n\n"
            "**Limitations:** it only searches the short editorial descriptions from The New Yorker, "
            "so niche details (minor characters, specific settings) may not surface. "
            "Results can also reflect the descriptions' editorial framing rather than the book itself."
        ),
    )

    # ── Tag filter pills ───────────────────────────────────────────────────
    available_genres = [g for g in GENRE_OPTIONS if "genre" in df.columns and g in df["genre"].values]
    # st.caption("Filter by tag — select multiple to narrow results:")
    selected_tags: list[str] = st.pills(
        "tags",
        options=available_genres + all_tags,
        selection_mode="multi",
        label_visibility="collapsed",
    ) or []

    # Reset page size when the search changes
    search_key = (query, tuple(selected_tags))
    if st.session_state.get("_search_key") != search_key:
        st.session_state["_search_key"] = search_key
        st.session_state["_top_k"] = 10
    top_k: int = st.session_state["_top_k"]

    st.divider()

    # ── Results ────────────────────────────────────────────────────────────
    results = get_results(query, df, embeddings, model, top_k, selected_tags)

    filter_note = f" · {', '.join(selected_tags)}" if selected_tags else ""

    if query.strip():
        st.caption(f"{len(results)} results for **\"{query}\"**{filter_note}")
    else:
        st.caption(f"Showing {len(results)} books, newest first{filter_note}")

    if results.empty:
        st.info("No books match — try a different query or fewer tag filters.")
        return

    cols = st.columns(3, gap="medium")
    for i, (_, row) in enumerate(results.iterrows()):
        with cols[i % 3]:
            render_card(row)

    # ── Load more ──────────────────────────────────────────────────────────
    if len(results) == top_k:
        st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
        col = st.columns([1, 2, 1])[1]
        with col:
            if st.button("Show 10 more", use_container_width=True):
                st.session_state["_top_k"] += 10
                st.rerun()


def main() -> None:
    app_path = str(Path(__file__).resolve())
    sys.exit(subprocess.call(["streamlit", "run", app_path, *sys.argv[1:]]))


if __name__ == "__main__":
    run()
