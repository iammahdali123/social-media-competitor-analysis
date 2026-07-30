# Social Media Competitor Analysis

> **Distributed ETL pipeline** that transforms raw social media data from six Pakistani fashion giants into a high-performance **Star Schema** with automated **"Campaign Type"** and **"Comment Intent"** classification for real-time competitive intelligence.

---

## Overview

| Layer | Technology | Description |
|---|---|---|
| Data Ingestion | Python + Faker | Synthetic JSON-Lines data per brand |
| Extract | pandas | Reads raw `posts.jsonl` / `comments.jsonl` |
| Transform | pandas + regex | Cleans, classifies, shapes to star schema |
| Classify | Rule-based regex | Campaign Type & Comment Intent |
| Load | SQLAlchemy + SQLite | Upserts facts & dimensions |
| Orchestration | `concurrent.futures` | Parallel brand processing |

---

## Six Pakistani Fashion Brands

| Brand | Founded | HQ | Category |
|---|---|---|---|
| Khaadi | 1998 | Karachi | Ethnic & Contemporary Wear |
| Gul Ahmed | 1953 | Karachi | Textile & Ready-to-Wear |
| Alkaram Studio | 1986 | Karachi | Textile & Fashion |
| Limelight | 2010 | Lahore | Casual & Western Wear |
| Sapphire | 2014 | Lahore | Contemporary Fashion |
| Bonanza Satrangi | 1976 | Lahore | Ethnic & Semi-Formal Wear |

---

## Star Schema

```
                    ┌──────────────┐
                    │  dim_brand   │
                    └──────┬───────┘
                           │
┌──────────────┐    ┌──────┴───────┐    ┌────────────────────┐
│  dim_date    ├────┤  fact_posts  ├────┤  dim_campaign_type │
└──────────────┘    └──────┬───────┘    └────────────────────┘
                           │
┌──────────────┐           │
│ dim_platform ├───────────┘
└──────────────┘
       │
       │            ┌──────────────────┐    ┌────────────────────┐
       └────────────┤  fact_comments   ├────┤ dim_comment_intent │
                    └──────────────────┘    └────────────────────┘
```

### Dimension Tables
- **dim_brand** – brand metadata (name, founded year, headquarters, category)
- **dim_platform** – Instagram, Facebook, TikTok, Twitter/X
- **dim_date** – year, month, day, quarter, weekday, week-of-year, is_weekend
- **dim_campaign_type** – Sale/Discount, Product Launch, Brand Awareness, Seasonal/Festival, Influencer/Collaboration, User Generated Content
- **dim_comment_intent** – Purchase Intent, Inquiry, Complaint, Compliment, Spam, Neutral

### Fact Tables
- **fact_posts** – likes, shares, reach, saves, video_views, comment_count
- **fact_comments** – comment text, likes, commenter username, classified intent

---

## Campaign Type Classifier

Keyword + regex rule engine applied to post captions:

| Campaign Type | Signal keywords |
|---|---|
| Sale/Discount | `% off`, `sale`, `clearance`, `flash sale`, `promo` |
| Product Launch | `new arrivals`, `introducing`, `now available`, `limited edition` |
| Brand Awareness | *(default / catch-all)* |
| Seasonal/Festival | `eid`, `winter collection`, `summer collection`, `khaddar` |
| Influencer/Collaboration | `collab`, `ambassador`, `partnership`, `spotted: @...` |
| User Generated Content | `customer gallery`, `ootd`, `regram`, `our insta fam` |

---

## Comment Intent Classifier

Keyword + regex rule engine applied to comment text (priority order):

| Intent | Signal keywords |
|---|---|
| Spam | `follow my page`, `check out my page`, `win free`, `giveaway` |
| Purchase Intent | `how much`, `price please`, `can I order`, `do you deliver` |
| Inquiry | `is this fabric`, `store timings`, `when will`, `unstitched` |
| Complaint | `quality gone down`, `disappointing`, `terrible`, `never buying again` |
| Compliment | `absolutely love`, `gorgeous`, `beautiful`, `my favourite brand` |
| Neutral | *(default / catch-all)* |

---

## Project Structure

```
social_media_etl/
├── config.py                    # Brand definitions, taxonomies, settings
├── pipeline.py                  # Distributed orchestrator (CLI entry point)
├── data_ingestion/
│   └── generators.py            # Synthetic data generator (posts & comments)
├── etl/
│   ├── extract.py               # Read raw JSON-Lines files
│   ├── transform.py             # Clean, classify, shape
│   └── load.py                  # Upsert into star schema
├── classification/
│   ├── campaign_type.py         # Campaign Type rule engine
│   └── comment_intent.py        # Comment Intent rule engine
└── star_schema/
    ├── models.py                # SQLAlchemy ORM models
    └── database.py              # Engine, session, DDL helpers
tests/
├── test_classification.py       # 60 classifier unit tests
├── test_etl.py                  # Extract & transform tests
└── test_star_schema.py          # Schema, load & ORM tests
data/
├── raw/<brand>/posts.jsonl      # Generated raw post data
├── raw/<brand>/comments.jsonl   # Generated raw comment data
└── warehouse.db                 # SQLite star-schema warehouse
```

---

## Quick Start

```bash
# 1. Install
pip install -e ".[dev]"

# 2. Run the full pipeline (generates data + loads warehouse)
python -m social_media_etl.pipeline --generate

# 3. Process specific brands only
python -m social_media_etl.pipeline --generate --brands Khaadi Sapphire

# 4. Run tests
pytest tests/ -v
```

### Pipeline output example

```
[INFO] Distributed ETL Pipeline – Social Media Competitor Analysis
[INFO] Brands: Khaadi, Gul Ahmed, Alkaram Studio, Limelight, Sapphire, Bonanza Satrangi
[INFO] Starting parallel Extract & Transform (workers=4) …
[INFO]   [Khaadi] extracted 50 posts, 440 comments
[INFO]   [Sapphire] extracted 50 posts, 458 comments
...
[INFO] Pipeline complete in 2.34s – 300 posts, 2783 comments loaded
```
