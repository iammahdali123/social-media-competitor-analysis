"""
etl/extract.py
==============
Extraction layer: reads raw JSON-Lines files produced by the data-ingestion
generators (or real API exports) and returns them as :class:`pandas.DataFrame`
objects ready for transformation.

The extractor is brand-aware – it locates the correct subdirectory under
``data/raw/`` using the brand's name and reads ``posts.jsonl`` and
``comments.jsonl``.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from social_media_etl.config import RAW_DIR


def _read_jsonl(path: Path) -> list[dict]:
    """Read a JSON-Lines file and return a list of record dicts."""
    records: list[dict] = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def extract_brand_posts(brand_name: str, raw_dir: Path | None = None) -> pd.DataFrame:
    """
    Read raw post records for *brand_name* from disk.

    Parameters
    ----------
    brand_name:
        The canonical brand name (e.g., ``"Khaadi"``).
    raw_dir:
        Root directory for raw data.  Defaults to ``config.RAW_DIR``.

    Returns
    -------
    :class:`pandas.DataFrame` with one row per post.

    Raises
    ------
    FileNotFoundError
        If the brand directory or ``posts.jsonl`` file does not exist.
    """
    if raw_dir is None:
        raw_dir = RAW_DIR

    posts_path = Path(raw_dir) / brand_name.replace(" ", "_") / "posts.jsonl"
    if not posts_path.exists():
        raise FileNotFoundError(f"Posts file not found: {posts_path}")

    records = _read_jsonl(posts_path)
    return pd.DataFrame(records)


def extract_brand_comments(brand_name: str, raw_dir: Path | None = None) -> pd.DataFrame:
    """
    Read raw comment records for *brand_name* from disk.

    Parameters
    ----------
    brand_name:
        The canonical brand name.
    raw_dir:
        Root directory for raw data.  Defaults to ``config.RAW_DIR``.

    Returns
    -------
    :class:`pandas.DataFrame` with one row per comment.

    Raises
    ------
    FileNotFoundError
        If the brand directory or ``comments.jsonl`` file does not exist.
    """
    if raw_dir is None:
        raw_dir = RAW_DIR

    comments_path = Path(raw_dir) / brand_name.replace(" ", "_") / "comments.jsonl"
    if not comments_path.exists():
        raise FileNotFoundError(f"Comments file not found: {comments_path}")

    records = _read_jsonl(comments_path)
    return pd.DataFrame(records)


def extract_brand(
    brand_name: str, raw_dir: Path | None = None
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Extract both posts and comments for a single brand.

    Parameters
    ----------
    brand_name:
        The canonical brand name.
    raw_dir:
        Root directory for raw data.  Defaults to ``config.RAW_DIR``.

    Returns
    -------
    ``(posts_df, comments_df)`` tuple.
    """
    return (
        extract_brand_posts(brand_name, raw_dir=raw_dir),
        extract_brand_comments(brand_name, raw_dir=raw_dir),
    )
