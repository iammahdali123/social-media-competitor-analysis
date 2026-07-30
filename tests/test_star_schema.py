"""
tests/test_star_schema.py
==========================
Unit tests for the star-schema models, database helpers, and load layer.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from social_media_etl.config import BRANDS
from social_media_etl.data_ingestion.generators import generate_and_save
from social_media_etl.etl.extract import extract_brand
from social_media_etl.etl.load import load_comments, load_date_dimensions, load_posts
from social_media_etl.etl.transform import transform_comments, transform_posts
from social_media_etl.star_schema.database import get_engine, get_session, init_db, seed_dimensions
from social_media_etl.star_schema.models import (
    DimBrand,
    DimCampaignType,
    DimCommentIntent,
    DimDate,
    DimPlatform,
    FactComment,
    FactPost,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def in_memory_engine():
    """SQLite in-memory engine with fully initialised schema."""
    engine = get_engine(db_path=":memory:")
    init_db(engine)
    seed_dimensions(engine)
    return engine


@pytest.fixture()
def populated_engine(tmp_path: Path):
    """Engine populated with one brand's worth of data."""
    brand = BRANDS[0]  # Khaadi
    generate_and_save(brand, output_dir=tmp_path, n_posts=5, avg_comments=3)

    engine = get_engine(db_path=str(tmp_path / "test.db"))
    init_db(engine)
    seed_dimensions(engine)

    posts_df, comments_df = extract_brand("Khaadi", raw_dir=tmp_path)
    transformed_posts, date_rows = transform_posts(posts_df)
    transformed_comments = transform_comments(comments_df)

    date_id_map = load_date_dimensions(engine, date_rows)
    load_posts(engine, transformed_posts, date_id_map)
    load_comments(engine, transformed_comments)

    return engine


# ===========================================================================
# Database / schema tests
# ===========================================================================

class TestDatabaseInit:

    def test_init_db_creates_tables(self, in_memory_engine) -> None:
        from sqlalchemy import inspect
        inspector = inspect(in_memory_engine)
        table_names = inspector.get_table_names()
        expected = {
            "dim_brand", "dim_platform", "dim_date",
            "dim_campaign_type", "dim_comment_intent",
            "fact_posts", "fact_comments",
        }
        assert expected.issubset(set(table_names))

    def test_seed_dimensions_populates_brands(self, in_memory_engine) -> None:
        with get_session(in_memory_engine) as session:
            brands = session.query(DimBrand).all()
        assert len(brands) == 6
        brand_names = {b.brand_name for b in brands}
        assert "Khaadi" in brand_names
        assert "Sapphire" in brand_names
        assert "Bonanza Satrangi" in brand_names

    def test_seed_dimensions_populates_platforms(self, in_memory_engine) -> None:
        with get_session(in_memory_engine) as session:
            platforms = session.query(DimPlatform).all()
        assert len(platforms) == 4
        names = {p.platform_name for p in platforms}
        assert "Instagram" in names
        assert "TikTok" in names

    def test_seed_dimensions_populates_campaign_types(self, in_memory_engine) -> None:
        with get_session(in_memory_engine) as session:
            types = session.query(DimCampaignType).all()
        assert len(types) == 6
        names = {t.campaign_type_name for t in types}
        assert "Sale/Discount" in names
        assert "Product Launch" in names
        assert "Brand Awareness" in names

    def test_seed_dimensions_populates_comment_intents(self, in_memory_engine) -> None:
        with get_session(in_memory_engine) as session:
            intents = session.query(DimCommentIntent).all()
        assert len(intents) == 6
        names = {i.intent_name for i in intents}
        assert "Purchase Intent" in names
        assert "Complaint" in names
        assert "Neutral" in names

    def test_seed_dimensions_idempotent(self, in_memory_engine) -> None:
        """Calling seed_dimensions twice should not create duplicate rows."""
        seed_dimensions(in_memory_engine)
        with get_session(in_memory_engine) as session:
            assert session.query(DimBrand).count() == 6
            assert session.query(DimPlatform).count() == 4


# ===========================================================================
# Load layer tests
# ===========================================================================

class TestLoadLayer:

    def test_load_posts_inserts_rows(self, populated_engine) -> None:
        with get_session(populated_engine) as session:
            count = session.query(FactPost).count()
        assert count == 5

    def test_load_posts_idempotent(self, populated_engine, tmp_path: Path) -> None:
        """Re-loading the same posts should not create duplicates."""
        posts_df, _ = extract_brand("Khaadi", raw_dir=tmp_path)
        transformed_posts, date_rows = transform_posts(posts_df)
        date_id_map = load_date_dimensions(populated_engine, date_rows)
        inserted = load_posts(populated_engine, transformed_posts, date_id_map)

        assert inserted == 0  # all already present
        with get_session(populated_engine) as session:
            count = session.query(FactPost).count()
        assert count == 5

    def test_load_comments_inserts_rows(self, populated_engine) -> None:
        with get_session(populated_engine) as session:
            count = session.query(FactComment).count()
        assert count >= 1

    def test_fact_posts_have_valid_fk(self, populated_engine) -> None:
        with get_session(populated_engine) as session:
            posts = session.query(FactPost).all()
            for post in posts:
                assert post.brand_id == 1       # Khaadi
                assert post.platform_id is not None
                assert post.date_id is not None
                assert post.campaign_type_id is not None

    def test_fact_posts_have_metrics(self, populated_engine) -> None:
        with get_session(populated_engine) as session:
            posts = session.query(FactPost).all()
            for post in posts:
                assert post.likes >= 0
                assert post.reach >= 0

    def test_fact_comments_have_valid_intent_fk(self, populated_engine) -> None:
        with get_session(populated_engine) as session:
            comments = session.query(FactComment).all()
            valid_intent_ids = {1, 2, 3, 4, 5, 6}
            for comment in comments:
                assert comment.intent_id in valid_intent_ids

    def test_dim_date_populated(self, populated_engine) -> None:
        with get_session(populated_engine) as session:
            count = session.query(DimDate).count()
        assert count >= 1

    def test_dim_date_attributes(self, populated_engine) -> None:
        with get_session(populated_engine) as session:
            date = session.query(DimDate).first()
        assert date.year in range(2020, 2030)
        assert date.month in range(1, 13)
        assert date.quarter in (1, 2, 3, 4)
        assert date.weekday in range(0, 7)
        assert date.is_weekend in (0, 1)


# ===========================================================================
# ORM model repr tests
# ===========================================================================

class TestModelReprs:

    def test_dim_brand_repr(self, in_memory_engine) -> None:
        with get_session(in_memory_engine) as session:
            brand = session.query(DimBrand).first()
        assert "DimBrand" in repr(brand)

    def test_dim_platform_repr(self, in_memory_engine) -> None:
        with get_session(in_memory_engine) as session:
            platform = session.query(DimPlatform).first()
        assert "DimPlatform" in repr(platform)

    def test_dim_campaign_type_repr(self, in_memory_engine) -> None:
        with get_session(in_memory_engine) as session:
            ct = session.query(DimCampaignType).first()
        assert "DimCampaignType" in repr(ct)

    def test_dim_comment_intent_repr(self, in_memory_engine) -> None:
        with get_session(in_memory_engine) as session:
            intent = session.query(DimCommentIntent).first()
        assert "DimCommentIntent" in repr(intent)
