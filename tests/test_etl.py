"""
tests/test_etl.py
=================
Unit tests for the ETL Extract and Transform layers.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pandas as pd
import pytest

from social_media_etl.config import BRANDS
from social_media_etl.data_ingestion.generators import generate_posts, generate_comments, generate_and_save
from social_media_etl.etl.extract import extract_brand_posts, extract_brand_comments, extract_brand
from social_media_etl.etl.transform import transform_posts, transform_comments


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def tmp_raw_dir(tmp_path: Path) -> Path:
    """Return a temporary raw-data directory populated with synthetic data."""
    brand = BRANDS[0]  # Khaadi
    generate_and_save(
        brand,
        output_dir=tmp_path,
        n_posts=5,
        avg_comments=3,
    )
    return tmp_path


@pytest.fixture()
def sample_posts_df(tmp_raw_dir: Path) -> pd.DataFrame:
    return extract_brand_posts("Khaadi", raw_dir=tmp_raw_dir)


@pytest.fixture()
def sample_comments_df(tmp_raw_dir: Path) -> pd.DataFrame:
    return extract_brand_comments("Khaadi", raw_dir=tmp_raw_dir)


# ===========================================================================
# Generator tests
# ===========================================================================

class TestGenerators:

    def test_generate_posts_count(self) -> None:
        brand = BRANDS[0]
        posts = generate_posts(brand, n_posts=10, start_date="2023-01-01", end_date="2023-12-31")
        assert len(posts) == 10

    def test_generate_posts_fields(self) -> None:
        brand = BRANDS[0]
        post = generate_posts(brand, n_posts=1, start_date="2023-01-01", end_date="2023-12-31")[0]
        required = {"post_id", "brand_name", "platform", "caption", "posted_at", "likes", "shares", "reach"}
        assert required.issubset(post.keys())

    def test_generate_posts_brand_name(self) -> None:
        brand = BRANDS[1]  # Gul Ahmed
        posts = generate_posts(brand, n_posts=5, start_date="2023-01-01", end_date="2023-12-31")
        assert all(p["brand_name"] == "Gul Ahmed" for p in posts)

    def test_generate_comments_linked_to_post(self) -> None:
        post_id = "test-post-id-123"
        comments = generate_comments(post_id, "Khaadi", avg_count=5)
        assert len(comments) >= 1
        assert all(c["post_id"] == post_id for c in comments)

    def test_generate_and_save_creates_files(self, tmp_path: Path) -> None:
        brand = BRANDS[0]
        generate_and_save(brand, output_dir=tmp_path, n_posts=3, avg_comments=2)
        assert (tmp_path / "Khaadi" / "posts.jsonl").exists()
        assert (tmp_path / "Khaadi" / "comments.jsonl").exists()

    def test_generate_all_brands(self, tmp_path: Path) -> None:
        from social_media_etl.data_ingestion.generators import generate_all_brands
        results = generate_all_brands(output_dir=tmp_path, n_posts=3, avg_comments=2)
        assert len(results) == 6
        for brand_name in results:
            posts, comments = results[brand_name]
            assert len(posts) == 3
            assert len(comments) >= 1


# ===========================================================================
# Extract tests
# ===========================================================================

class TestExtract:

    def test_extract_posts_returns_dataframe(self, tmp_raw_dir: Path) -> None:
        df = extract_brand_posts("Khaadi", raw_dir=tmp_raw_dir)
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 5

    def test_extract_posts_has_required_columns(self, tmp_raw_dir: Path) -> None:
        df = extract_brand_posts("Khaadi", raw_dir=tmp_raw_dir)
        for col in ("post_id", "brand_name", "platform", "caption", "posted_at"):
            assert col in df.columns, f"Missing column: {col}"

    def test_extract_comments_returns_dataframe(self, tmp_raw_dir: Path) -> None:
        df = extract_brand_comments("Khaadi", raw_dir=tmp_raw_dir)
        assert isinstance(df, pd.DataFrame)
        assert len(df) >= 1

    def test_extract_comments_has_required_columns(self, tmp_raw_dir: Path) -> None:
        df = extract_brand_comments("Khaadi", raw_dir=tmp_raw_dir)
        for col in ("comment_id", "post_id", "comment_text"):
            assert col in df.columns, f"Missing column: {col}"

    def test_extract_brand_returns_tuple(self, tmp_raw_dir: Path) -> None:
        posts_df, comments_df = extract_brand("Khaadi", raw_dir=tmp_raw_dir)
        assert isinstance(posts_df, pd.DataFrame)
        assert isinstance(comments_df, pd.DataFrame)

    def test_extract_missing_brand_raises(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            extract_brand_posts("NonExistentBrand", raw_dir=tmp_path)


# ===========================================================================
# Transform tests
# ===========================================================================

class TestTransformPosts:

    def test_transform_adds_campaign_type(self, sample_posts_df: pd.DataFrame) -> None:
        transformed, _ = transform_posts(sample_posts_df)
        assert "campaign_type_name" in transformed.columns
        assert "campaign_type_id" in transformed.columns

    def test_transform_adds_brand_id(self, sample_posts_df: pd.DataFrame) -> None:
        transformed, _ = transform_posts(sample_posts_df)
        assert "brand_id" in transformed.columns
        assert (transformed["brand_id"] == 1).all()  # Khaadi = 1

    def test_transform_adds_platform_id(self, sample_posts_df: pd.DataFrame) -> None:
        transformed, _ = transform_posts(sample_posts_df)
        assert "platform_id" in transformed.columns
        assert transformed["platform_id"].notna().all()

    def test_transform_parses_posted_at(self, sample_posts_df: pd.DataFrame) -> None:
        transformed, _ = transform_posts(sample_posts_df)
        assert pd.api.types.is_datetime64_any_dtype(transformed["posted_at"])

    def test_transform_returns_date_rows(self, sample_posts_df: pd.DataFrame) -> None:
        _, date_rows = transform_posts(sample_posts_df)
        assert isinstance(date_rows, list)
        assert len(date_rows) >= 1
        for row in date_rows:
            assert "full_date" in row
            assert "year" in row
            assert "quarter" in row

    def test_transform_metrics_are_integers(self, sample_posts_df: pd.DataFrame) -> None:
        transformed, _ = transform_posts(sample_posts_df)
        for col in ("likes", "shares", "reach"):
            assert transformed[col].dtype in (int, "int64", "int32")


class TestTransformComments:

    def test_transform_adds_intent(self, sample_comments_df: pd.DataFrame) -> None:
        transformed = transform_comments(sample_comments_df)
        assert "intent_name" in transformed.columns
        assert "intent_id" in transformed.columns

    def test_transform_intent_values_valid(self, sample_comments_df: pd.DataFrame) -> None:
        from social_media_etl.config import COMMENT_INTENT_ID_BY_NAME
        transformed = transform_comments(sample_comments_df)
        valid_intents = set(COMMENT_INTENT_ID_BY_NAME.keys())
        assert set(transformed["intent_name"].unique()).issubset(valid_intents)

    def test_transform_parses_commented_at(self, sample_comments_df: pd.DataFrame) -> None:
        transformed = transform_comments(sample_comments_df)
        assert pd.api.types.is_datetime64_any_dtype(transformed["commented_at"])

    def test_transform_likes_is_integer(self, sample_comments_df: pd.DataFrame) -> None:
        transformed = transform_comments(sample_comments_df)
        assert transformed["likes"].dtype in (int, "int64", "int32")
