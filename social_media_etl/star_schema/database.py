"""
star_schema/database.py
========================
Database connection management and DDL helpers for the SQLite star-schema
warehouse.

Usage
-----
    from social_media_etl.star_schema.database import get_engine, init_db, get_session

    engine = get_engine()
    init_db(engine)

    with get_session(engine) as session:
        # query / insert
        ...
"""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Generator

from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from social_media_etl.config import PIPELINE_CONFIG, WAREHOUSE_PATH
from social_media_etl.star_schema.models import Base


def get_engine(db_path: str | None = None) -> Engine:
    """
    Create and return a SQLAlchemy engine for the SQLite warehouse.

    Parameters
    ----------
    db_path:
        Path to the SQLite file.  Defaults to ``config.WAREHOUSE_PATH``.

    Returns
    -------
    Configured :class:`sqlalchemy.engine.Engine`.
    """
    if db_path is None:
        db_path = WAREHOUSE_PATH

    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(
        f"sqlite:///{db_path}",
        connect_args={"check_same_thread": False},
        echo=False,
    )

    # Enable WAL mode for better concurrent read/write performance
    if PIPELINE_CONFIG.get("db_wal_mode"):
        @event.listens_for(engine, "connect")
        def set_wal_mode(dbapi_connection, _connection_record):  # noqa: ANN001
            dbapi_connection.execute("PRAGMA journal_mode=WAL")
            dbapi_connection.execute("PRAGMA synchronous=NORMAL")

    return engine


def init_db(engine: Engine) -> None:
    """
    Create all tables defined in the ORM models (DDL is idempotent).

    Parameters
    ----------
    engine:
        SQLAlchemy engine obtained from :func:`get_engine`.
    """
    Base.metadata.create_all(engine)


@contextmanager
def get_session(engine: Engine) -> Generator[Session, None, None]:
    """
    Context manager that yields a database session and handles
    commit / rollback automatically.

    Parameters
    ----------
    engine:
        SQLAlchemy engine.

    Yields
    ------
    :class:`sqlalchemy.orm.Session`
    """
    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def seed_dimensions(engine: Engine) -> None:
    """
    Populate the four static dimension tables (brand, platform, campaign_type,
    comment_intent) with the canonical values from ``config``.  Existing rows
    are left unchanged (INSERT OR IGNORE semantics via merge).
    """
    from social_media_etl.config import (
        BRANDS,
        CAMPAIGN_TYPES,
        COMMENT_INTENTS,
        PLATFORMS,
    )
    from social_media_etl.star_schema.models import (
        DimBrand,
        DimCampaignType,
        DimCommentIntent,
        DimPlatform,
    )

    with get_session(engine) as session:
        # Brands
        for b in BRANDS:
            if not session.get(DimBrand, b["brand_id"]):
                session.add(DimBrand(**b))

        # Platforms
        for p in PLATFORMS:
            if not session.get(DimPlatform, p["platform_id"]):
                session.add(DimPlatform(**p))

        # Campaign types
        for c in CAMPAIGN_TYPES:
            if not session.get(DimCampaignType, c["campaign_type_id"]):
                session.add(DimCampaignType(**c))

        # Comment intents
        for i in COMMENT_INTENTS:
            if not session.get(DimCommentIntent, i["intent_id"]):
                session.add(DimCommentIntent(**i))
