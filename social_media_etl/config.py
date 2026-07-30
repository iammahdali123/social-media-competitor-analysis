"""
config.py
=========
Central configuration for the distributed ETL pipeline.

Defines the six Pakistani fashion brands, social-media platforms, campaign-type
taxonomy, and comment-intent taxonomy used throughout the pipeline.
"""

from __future__ import annotations

from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR: Path = Path(__file__).resolve().parent.parent
DATA_DIR: Path = BASE_DIR / "data"
RAW_DIR: Path = DATA_DIR / "raw"
WAREHOUSE_PATH: str = str(DATA_DIR / "warehouse.db")

# ---------------------------------------------------------------------------
# Pakistani fashion brands (the six competitors)
# ---------------------------------------------------------------------------
BRANDS: list[dict] = [
    {
        "brand_id": 1,
        "brand_name": "Khaadi",
        "country": "Pakistan",
        "founded_year": 1998,
        "headquarters": "Karachi",
        "instagram_handle": "@khaadi",
        "facebook_page": "Khaadi",
        "category": "Ethnic & Contemporary Wear",
    },
    {
        "brand_id": 2,
        "brand_name": "Gul Ahmed",
        "country": "Pakistan",
        "founded_year": 1953,
        "headquarters": "Karachi",
        "instagram_handle": "@gulahmedofficial",
        "facebook_page": "GulAhmedOfficial",
        "category": "Textile & Ready-to-Wear",
    },
    {
        "brand_id": 3,
        "brand_name": "Alkaram Studio",
        "country": "Pakistan",
        "founded_year": 1986,
        "headquarters": "Karachi",
        "instagram_handle": "@alkaramstudio",
        "facebook_page": "AlkaramStudio",
        "category": "Textile & Fashion",
    },
    {
        "brand_id": 4,
        "brand_name": "Limelight",
        "country": "Pakistan",
        "founded_year": 2010,
        "headquarters": "Lahore",
        "instagram_handle": "@limelightpk",
        "facebook_page": "LimelightPakistan",
        "category": "Casual & Western Wear",
    },
    {
        "brand_id": 5,
        "brand_name": "Sapphire",
        "country": "Pakistan",
        "founded_year": 2014,
        "headquarters": "Lahore",
        "instagram_handle": "@sapphirepk",
        "facebook_page": "SapphirePakistan",
        "category": "Contemporary Fashion",
    },
    {
        "brand_id": 6,
        "brand_name": "Bonanza Satrangi",
        "country": "Pakistan",
        "founded_year": 1976,
        "headquarters": "Lahore",
        "instagram_handle": "@bonanzasatrangi",
        "facebook_page": "BonanzaSatrangi",
        "category": "Ethnic & Semi-Formal Wear",
    },
]

# Convenience look-ups
BRAND_ID_BY_NAME: dict[str, int] = {b["brand_name"]: b["brand_id"] for b in BRANDS}
BRAND_NAMES: list[str] = [b["brand_name"] for b in BRANDS]

# ---------------------------------------------------------------------------
# Social-media platforms
# ---------------------------------------------------------------------------
PLATFORMS: list[dict] = [
    {"platform_id": 1, "platform_name": "Instagram", "platform_type": "Image/Video"},
    {"platform_id": 2, "platform_name": "Facebook", "platform_type": "Mixed"},
    {"platform_id": 3, "platform_name": "TikTok", "platform_type": "Short Video"},
    {"platform_id": 4, "platform_name": "Twitter/X", "platform_type": "Microblog"},
]

PLATFORM_ID_BY_NAME: dict[str, int] = {
    p["platform_name"]: p["platform_id"] for p in PLATFORMS
}

# ---------------------------------------------------------------------------
# Campaign-type taxonomy
# ---------------------------------------------------------------------------
CAMPAIGN_TYPES: list[dict] = [
    {"campaign_type_id": 1, "campaign_type_name": "Sale/Discount"},
    {"campaign_type_id": 2, "campaign_type_name": "Product Launch"},
    {"campaign_type_id": 3, "campaign_type_name": "Brand Awareness"},
    {"campaign_type_id": 4, "campaign_type_name": "Seasonal/Festival"},
    {"campaign_type_id": 5, "campaign_type_name": "Influencer/Collaboration"},
    {"campaign_type_id": 6, "campaign_type_name": "User Generated Content"},
]

CAMPAIGN_TYPE_ID_BY_NAME: dict[str, int] = {
    c["campaign_type_name"]: c["campaign_type_id"] for c in CAMPAIGN_TYPES
}

# ---------------------------------------------------------------------------
# Comment-intent taxonomy
# ---------------------------------------------------------------------------
COMMENT_INTENTS: list[dict] = [
    {"intent_id": 1, "intent_name": "Purchase Intent"},
    {"intent_id": 2, "intent_name": "Inquiry"},
    {"intent_id": 3, "intent_name": "Complaint"},
    {"intent_id": 4, "intent_name": "Compliment"},
    {"intent_id": 5, "intent_name": "Spam"},
    {"intent_id": 6, "intent_name": "Neutral"},
]

COMMENT_INTENT_ID_BY_NAME: dict[str, int] = {
    i["intent_name"]: i["intent_id"] for i in COMMENT_INTENTS
}

# ---------------------------------------------------------------------------
# Pipeline settings
# ---------------------------------------------------------------------------
PIPELINE_CONFIG: dict = {
    # Number of worker processes for parallel brand processing
    "max_workers": 4,
    # Rows generated per brand per run (posts)
    "posts_per_brand": 50,
    # Average comments generated per post
    "avg_comments_per_post": 10,
    # Date range for synthetic data generation
    "data_start_date": "2023-01-01",
    "data_end_date": "2024-12-31",
    # SQLite WAL mode for concurrent writes
    "db_wal_mode": True,
}
