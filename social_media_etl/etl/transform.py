"""
etl/transform.py
================
Transformation layer: cleans raw DataFrames, applies the Campaign Type and
Comment Intent classifiers, and reshapes the data into star-schema-ready
DataFrames that map directly onto the ORM models.

Transformation steps (posts)
-----------------------------
1. Parse ``posted_at`` to :class:`datetime`.
2. Coerce numeric metric columns to integers, filling NaN with 0.
3. Classify ``caption`` → ``campaign_type_name`` using the rule engine.
4. Build the ``dim_date`` row dict for the post's date.
5. Resolve FK IDs (brand_id, platform_id, campaign_type_id, date_id).

Transformation steps (comments)
---------------------------------
1. Parse ``commented_at`` to :class:`datetime`.
2. Coerce ``likes`` to int.
3. Classify ``comment_text`` → ``intent_name`` using the rule engine.
4. Resolve FK ID (intent_id).
"""

from __future__ import annotations

from datetime import datetime

import pandas as pd

from social_media_etl.classification.campaign_type import classify_campaign_types_bulk
from social_media_etl.classification.comment_intent import classify_comment_intents_bulk
from social_media_etl.config import (
    BRAND_ID_BY_NAME,
    CAMPAIGN_TYPE_ID_BY_NAME,
    COMMENT_INTENT_ID_BY_NAME,
    PLATFORM_ID_BY_NAME,
)

# ---------------------------------------------------------------------------
# Date dimension helper
# ---------------------------------------------------------------------------

def _build_date_row(dt: datetime) -> dict:
    """Build a dim_date attribute dict from a :class:`datetime`."""
    # Truncate to date boundary (midnight) to keep the date dimension tidy
    date_midnight = dt.replace(hour=0, minute=0, second=0, microsecond=0)
    return {
        "full_date": date_midnight,
        "year": dt.year,
        "month": dt.month,
        "day": dt.day,
        "quarter": (dt.month - 1) // 3 + 1,
        "weekday": dt.weekday(),          # 0=Monday, 6=Sunday
        "week_of_year": int(dt.strftime("%W")),
        "is_weekend": int(dt.weekday() >= 5),
    }


# ---------------------------------------------------------------------------
# Posts transformation
# ---------------------------------------------------------------------------

def transform_posts(posts_df: pd.DataFrame) -> tuple[pd.DataFrame, list[dict]]:
    """
    Clean and enrich a raw posts DataFrame.

    Parameters
    ----------
    posts_df:
        Raw posts DataFrame from :func:`etl.extract.extract_brand_posts`.

    Returns
    -------
    ``(transformed_df, date_rows)`` where:

    * ``transformed_df`` has the columns needed to build a
      :class:`~star_schema.models.FactPost` ORM object.
    * ``date_rows`` is a list of unique dim_date attribute dicts for the dates
      referenced by the posts.  The caller (load layer) is responsible for
      upserting these into ``dim_date`` and resolving ``date_id``.
    """
    df = posts_df.copy()

    # 1. Parse posted_at
    df["posted_at"] = pd.to_datetime(df["posted_at"], errors="coerce", utc=False)
    df = df.dropna(subset=["posted_at"])

    # 2. Coerce metrics
    for col in ("likes", "shares", "reach", "saves", "video_views"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)
        else:
            df[col] = 0

    # 3. Campaign-type classification
    df["campaign_type_name"] = classify_campaign_types_bulk(df["caption"].tolist())
    df["campaign_type_id"] = df["campaign_type_name"].map(CAMPAIGN_TYPE_ID_BY_NAME)

    # 4. Resolve brand FK
    df["brand_id"] = df["brand_name"].map(BRAND_ID_BY_NAME)

    # 5. Resolve platform FK
    df["platform_id"] = df["platform"].map(PLATFORM_ID_BY_NAME)

    # 6. Build date rows (unique dates)
    date_rows: list[dict] = []
    seen_dates: set = set()
    for dt in df["posted_at"]:
        date_key = dt.date()
        if date_key not in seen_dates:
            seen_dates.add(date_key)
            date_rows.append(_build_date_row(dt))

    return df, date_rows


# ---------------------------------------------------------------------------
# Comments transformation
# ---------------------------------------------------------------------------

def transform_comments(comments_df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean and enrich a raw comments DataFrame.

    Parameters
    ----------
    comments_df:
        Raw comments DataFrame from :func:`etl.extract.extract_brand_comments`.

    Returns
    -------
    Transformed DataFrame with ``intent_name`` and ``intent_id`` columns added.
    """
    df = comments_df.copy()

    # 1. Parse commented_at
    df["commented_at"] = pd.to_datetime(df["commented_at"], errors="coerce", utc=False)

    # 2. Coerce likes
    if "likes" in df.columns:
        df["likes"] = pd.to_numeric(df["likes"], errors="coerce").fillna(0).astype(int)
    else:
        df["likes"] = 0

    # 3. Comment intent classification
    df["intent_name"] = classify_comment_intents_bulk(df["comment_text"].tolist())
    df["intent_id"] = df["intent_name"].map(COMMENT_INTENT_ID_BY_NAME)

    return df
