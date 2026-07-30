"""
etl/load.py
===========
Load layer: upserts transformed DataFrames into the SQLite star-schema
warehouse using SQLAlchemy ORM sessions.

Strategy
--------
* Dimension rows (dim_date) are upserted by their natural key
  (``full_date``) so that the same calendar date is never inserted twice.
* Fact rows (fact_posts, fact_comments) are upserted by their UUID primary
  key so that re-running the pipeline is idempotent.
"""

from __future__ import annotations

from datetime import datetime

import pandas as pd
from sqlalchemy.engine import Engine

from social_media_etl.star_schema.database import get_session
from social_media_etl.star_schema.models import DimDate, FactComment, FactPost


# ---------------------------------------------------------------------------
# Date dimension loader
# ---------------------------------------------------------------------------

def load_date_dimensions(engine: Engine, date_rows: list[dict]) -> dict[datetime, int]:
    """
    Upsert date rows into ``dim_date`` and return a mapping
    ``full_date (midnight) -> date_id``.

    Parameters
    ----------
    engine:
        SQLAlchemy engine.
    date_rows:
        List of date attribute dicts from :func:`etl.transform.transform_posts`.

    Returns
    -------
    dict mapping ``datetime`` → ``date_id`` integer.
    """
    date_id_map: dict[datetime, int] = {}
    with get_session(engine) as session:
        for row in date_rows:
            full_date: datetime = row["full_date"]
            existing = (
                session.query(DimDate)
                .filter(DimDate.full_date == full_date)
                .first()
            )
            if existing:
                date_id_map[full_date] = existing.date_id
            else:
                new_date = DimDate(**row)
                session.add(new_date)
                session.flush()  # obtain auto-generated PK before commit
                date_id_map[full_date] = new_date.date_id
    return date_id_map


# ---------------------------------------------------------------------------
# Post fact loader
# ---------------------------------------------------------------------------

def load_posts(
    engine: Engine,
    posts_df: pd.DataFrame,
    date_id_map: dict[datetime, int],
) -> int:
    """
    Upsert transformed post rows into ``fact_posts``.

    Parameters
    ----------
    engine:
        SQLAlchemy engine.
    posts_df:
        Transformed posts DataFrame from :func:`etl.transform.transform_posts`.
    date_id_map:
        Mapping from midnight-truncated datetime to ``date_id`` obtained from
        :func:`load_date_dimensions`.

    Returns
    -------
    Number of rows inserted (new) or skipped (already present).
    """
    inserted = 0
    with get_session(engine) as session:
        for _, row in posts_df.iterrows():
            post_id: str = row["post_id"]
            if session.get(FactPost, post_id):
                continue  # already loaded – skip (idempotent)

            # Resolve date_id from the midnight-truncated datetime
            midnight = row["posted_at"].replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            date_id = date_id_map.get(midnight)
            if date_id is None:
                continue  # should not happen in normal flow

            session.add(
                FactPost(
                    post_id=post_id,
                    brand_id=int(row["brand_id"]),
                    platform_id=int(row["platform_id"]),
                    date_id=date_id,
                    campaign_type_id=int(row["campaign_type_id"]),
                    caption=row.get("caption"),
                    post_url=row.get("post_url"),
                    posted_at=row["posted_at"].to_pydatetime(),
                    likes=int(row.get("likes", 0)),
                    shares=int(row.get("shares", 0)),
                    reach=int(row.get("reach", 0)),
                    saves=int(row.get("saves", 0)),
                    video_views=int(row.get("video_views", 0)),
                    comment_count=0,  # updated after comments are loaded
                )
            )
            inserted += 1
    return inserted


# ---------------------------------------------------------------------------
# Comment fact loader
# ---------------------------------------------------------------------------

def load_comments(engine: Engine, comments_df: pd.DataFrame) -> int:
    """
    Upsert transformed comment rows into ``fact_comments`` and update the
    ``comment_count`` on the associated ``fact_posts`` row.

    Parameters
    ----------
    engine:
        SQLAlchemy engine.
    comments_df:
        Transformed comments DataFrame from :func:`etl.transform.transform_comments`.

    Returns
    -------
    Number of comment rows inserted.
    """
    inserted = 0
    post_comment_counts: dict[str, int] = {}

    with get_session(engine) as session:
        for _, row in comments_df.iterrows():
            comment_id: str = row["comment_id"]
            if session.get(FactComment, comment_id):
                continue  # idempotent

            commented_at = row["commented_at"]
            if pd.isnull(commented_at):
                commented_at = None
            else:
                commented_at = commented_at.to_pydatetime()

            session.add(
                FactComment(
                    comment_id=comment_id,
                    post_id=row["post_id"],
                    intent_id=int(row["intent_id"]),
                    commenter_username=row.get("commenter_username"),
                    comment_text=row.get("comment_text"),
                    commented_at=commented_at,
                    likes=int(row.get("likes", 0)),
                )
            )
            inserted += 1
            post_comment_counts[row["post_id"]] = (
                post_comment_counts.get(row["post_id"], 0) + 1
            )

        # Update comment_count on fact_posts
        for post_id, count in post_comment_counts.items():
            post = session.get(FactPost, post_id)
            if post:
                post.comment_count = (post.comment_count or 0) + count

    return inserted
