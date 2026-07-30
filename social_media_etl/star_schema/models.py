"""
star_schema/models.py
======================
SQLAlchemy ORM models that define the Star Schema for the social-media
competitive-intelligence warehouse.

Star Schema Layout
------------------
Fact Table
~~~~~~~~~~
fact_posts
  – one row per social-media post
  – contains quantitative metrics: likes, shares, reach, saves, video_views,
    comment_count
  – FK references to all dimension tables

Dimension Tables
~~~~~~~~~~~~~~~~
dim_brand          – the six Pakistani fashion brands
dim_platform       – social-media platforms (Instagram, Facebook, TikTok, Twitter/X)
dim_date           – calendar date attributes (year, month, day, quarter, weekday)
dim_campaign_type  – campaign-type labels
dim_comment_intent – comment-intent labels (shared by the comment-level fact)

Additional Fact
~~~~~~~~~~~~~~~
fact_comments
  – one row per comment
  – links to fact_posts (post_id) and dim_comment_intent
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    Text,
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


# ===========================================================================
# Dimension: Brand
# ===========================================================================

class DimBrand(Base):
    __tablename__ = "dim_brand"

    brand_id = Column(Integer, primary_key=True)
    brand_name = Column(String(100), nullable=False, unique=True)
    country = Column(String(50), default="Pakistan")
    founded_year = Column(SmallInteger)
    headquarters = Column(String(100))
    instagram_handle = Column(String(100))
    facebook_page = Column(String(100))
    category = Column(String(100))

    posts = relationship("FactPost", back_populates="brand", lazy="dynamic")

    def __repr__(self) -> str:
        return f"<DimBrand id={self.brand_id} name={self.brand_name!r}>"


# ===========================================================================
# Dimension: Platform
# ===========================================================================

class DimPlatform(Base):
    __tablename__ = "dim_platform"

    platform_id = Column(Integer, primary_key=True)
    platform_name = Column(String(50), nullable=False, unique=True)
    platform_type = Column(String(50))

    posts = relationship("FactPost", back_populates="platform", lazy="dynamic")

    def __repr__(self) -> str:
        return f"<DimPlatform id={self.platform_id} name={self.platform_name!r}>"


# ===========================================================================
# Dimension: Date
# ===========================================================================

class DimDate(Base):
    __tablename__ = "dim_date"

    date_id = Column(Integer, primary_key=True, autoincrement=True)
    full_date = Column(DateTime, nullable=False, unique=True, index=True)
    year = Column(SmallInteger, nullable=False)
    month = Column(SmallInteger, nullable=False)
    day = Column(SmallInteger, nullable=False)
    quarter = Column(SmallInteger, nullable=False)
    weekday = Column(SmallInteger, nullable=False)   # 0=Monday, 6=Sunday
    week_of_year = Column(SmallInteger, nullable=False)
    is_weekend = Column(SmallInteger, nullable=False, default=0)

    posts = relationship("FactPost", back_populates="date", lazy="dynamic")

    def __repr__(self) -> str:
        return f"<DimDate id={self.date_id} date={self.full_date!r}>"


# ===========================================================================
# Dimension: Campaign Type
# ===========================================================================

class DimCampaignType(Base):
    __tablename__ = "dim_campaign_type"

    campaign_type_id = Column(Integer, primary_key=True)
    campaign_type_name = Column(String(100), nullable=False, unique=True)

    posts = relationship("FactPost", back_populates="campaign_type", lazy="dynamic")

    def __repr__(self) -> str:
        return f"<DimCampaignType id={self.campaign_type_id} name={self.campaign_type_name!r}>"


# ===========================================================================
# Dimension: Comment Intent
# ===========================================================================

class DimCommentIntent(Base):
    __tablename__ = "dim_comment_intent"

    intent_id = Column(Integer, primary_key=True)
    intent_name = Column(String(100), nullable=False, unique=True)

    comments = relationship("FactComment", back_populates="intent", lazy="dynamic")

    def __repr__(self) -> str:
        return f"<DimCommentIntent id={self.intent_id} name={self.intent_name!r}>"


# ===========================================================================
# Fact: Post
# ===========================================================================

class FactPost(Base):
    __tablename__ = "fact_posts"

    post_id = Column(String(36), primary_key=True)   # UUID
    brand_id = Column(Integer, ForeignKey("dim_brand.brand_id"), nullable=False)
    platform_id = Column(Integer, ForeignKey("dim_platform.platform_id"), nullable=False)
    date_id = Column(Integer, ForeignKey("dim_date.date_id"), nullable=False)
    campaign_type_id = Column(Integer, ForeignKey("dim_campaign_type.campaign_type_id"), nullable=False)

    caption = Column(Text)
    post_url = Column(String(300))
    posted_at = Column(DateTime, nullable=False)

    # Metrics
    likes = Column(BigInteger, default=0)
    shares = Column(BigInteger, default=0)
    reach = Column(BigInteger, default=0)
    saves = Column(BigInteger, default=0)
    video_views = Column(BigInteger, default=0)
    comment_count = Column(Integer, default=0)

    # Relationships
    brand = relationship("DimBrand", back_populates="posts")
    platform = relationship("DimPlatform", back_populates="posts")
    date = relationship("DimDate", back_populates="posts")
    campaign_type = relationship("DimCampaignType", back_populates="posts")
    comments = relationship("FactComment", back_populates="post", lazy="dynamic")

    __table_args__ = (
        Index("ix_fact_posts_brand_date", "brand_id", "date_id"),
        Index("ix_fact_posts_platform", "platform_id"),
        Index("ix_fact_posts_campaign", "campaign_type_id"),
    )

    def __repr__(self) -> str:
        return f"<FactPost id={self.post_id!r} brand={self.brand_id} likes={self.likes}>"


# ===========================================================================
# Fact: Comment
# ===========================================================================

class FactComment(Base):
    __tablename__ = "fact_comments"

    comment_id = Column(String(36), primary_key=True)   # UUID
    post_id = Column(String(36), ForeignKey("fact_posts.post_id"), nullable=False)
    intent_id = Column(Integer, ForeignKey("dim_comment_intent.intent_id"), nullable=False)

    commenter_username = Column(String(100))
    comment_text = Column(Text)
    commented_at = Column(DateTime)
    likes = Column(Integer, default=0)

    # Relationships
    post = relationship("FactPost", back_populates="comments")
    intent = relationship("DimCommentIntent", back_populates="comments")

    __table_args__ = (
        Index("ix_fact_comments_post", "post_id"),
        Index("ix_fact_comments_intent", "intent_id"),
    )

    def __repr__(self) -> str:
        return f"<FactComment id={self.comment_id!r} intent={self.intent_id}>"
