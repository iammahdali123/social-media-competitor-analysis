"""
pipeline.py
===========
Distributed ETL pipeline orchestrator.

The pipeline fans out across all six Pakistani fashion brands using
:class:`concurrent.futures.ProcessPoolExecutor` (or
:class:`~concurrent.futures.ThreadPoolExecutor` when ``use_threads=True``),
processing each brand's data in parallel, then loading the results into the
shared SQLite star-schema warehouse sequentially (SQLite does not support
concurrent writes from multiple processes to the same file safely, so we
serialise the load step).

Usage
-----
Run from the project root::

    python -m social_media_etl.pipeline          # full run
    python -m social_media_etl.pipeline --brands Khaadi Sapphire
    python -m social_media_etl.pipeline --generate   # re-generate raw data first

Or import programmatically::

    from social_media_etl.pipeline import run_pipeline
    result = run_pipeline()
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from social_media_etl.config import BRAND_NAMES, BRANDS, PIPELINE_CONFIG, RAW_DIR
from social_media_etl.data_ingestion.generators import generate_and_save
from social_media_etl.etl.extract import extract_brand
from social_media_etl.etl.load import load_comments, load_date_dimensions, load_posts
from social_media_etl.etl.transform import transform_comments, transform_posts
from social_media_etl.star_schema.database import get_engine, init_db, seed_dimensions

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s – %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("etl.pipeline")


# ---------------------------------------------------------------------------
# Per-brand ETL worker (runs inside a subprocess / thread)
# ---------------------------------------------------------------------------

def _etl_worker(brand_name: str, raw_dir: str) -> dict[str, Any]:
    """
    Extract and transform data for a single brand.  This function is designed
    to be executed in a worker process/thread; it returns plain Python objects
    (not SQLAlchemy ORM instances) so they can be safely pickled across process
    boundaries.

    Parameters
    ----------
    brand_name:
        Canonical brand name.
    raw_dir:
        Path to the raw data directory (as a string for pickling safety).

    Returns
    -------
    dict with keys ``brand_name``, ``posts_records``, ``date_rows``,
    ``comments_records``.
    """
    from social_media_etl.etl.extract import extract_brand
    from social_media_etl.etl.transform import transform_comments, transform_posts

    posts_df, comments_df = extract_brand(brand_name, raw_dir=Path(raw_dir))
    transformed_posts, date_rows = transform_posts(posts_df)
    transformed_comments = transform_comments(comments_df)

    return {
        "brand_name": brand_name,
        "posts_df": transformed_posts,
        "date_rows": date_rows,
        "comments_df": transformed_comments,
    }


# ---------------------------------------------------------------------------
# Pipeline entry point
# ---------------------------------------------------------------------------

def run_pipeline(
    brands: list[str] | None = None,
    generate: bool = False,
    use_threads: bool = False,
    max_workers: int | None = None,
    raw_dir: Path | None = None,
    db_path: str | None = None,
) -> dict[str, dict[str, int]]:
    """
    Run the full distributed ETL pipeline.

    Parameters
    ----------
    brands:
        List of brand names to process.  Defaults to all six.
    generate:
        If ``True``, regenerate raw synthetic data before running ETL.
    use_threads:
        Use :class:`ThreadPoolExecutor` instead of
        :class:`ProcessPoolExecutor`.  Useful for testing and environments
        where fork-based multiprocessing is unavailable.
    max_workers:
        Maximum number of parallel workers.  Defaults to
        ``PIPELINE_CONFIG["max_workers"]``.
    raw_dir:
        Override the raw-data directory.
    db_path:
        Override the warehouse database path.

    Returns
    -------
    dict mapping ``brand_name`` to a stats dict with keys
    ``posts_inserted`` and ``comments_inserted``.
    """
    if brands is None:
        brands = BRAND_NAMES
    if raw_dir is None:
        raw_dir = RAW_DIR
    if max_workers is None:
        max_workers = PIPELINE_CONFIG["max_workers"]

    t_start = time.time()
    logger.info("=" * 60)
    logger.info("Distributed ETL Pipeline – Social Media Competitor Analysis")
    logger.info("Brands: %s", ", ".join(brands))
    logger.info("=" * 60)

    # ------------------------------------------------------------------
    # Optional: (re-)generate synthetic raw data
    # ------------------------------------------------------------------
    if generate:
        logger.info("Generating synthetic raw data for %d brands …", len(brands))
        brand_dicts = [b for b in BRANDS if b["brand_name"] in brands]
        for brand in brand_dicts:
            posts, comments = generate_and_save(brand, output_dir=raw_dir)
            logger.info(
                "  [%s] generated %d posts, %d comments",
                brand["brand_name"],
                len(posts),
                len(comments),
            )

    # ------------------------------------------------------------------
    # Initialise warehouse
    # ------------------------------------------------------------------
    engine = get_engine(db_path=db_path)
    init_db(engine)
    seed_dimensions(engine)
    logger.info("Warehouse initialised at: %s", db_path or "default path")

    # ------------------------------------------------------------------
    # Parallel Extract + Transform
    # ------------------------------------------------------------------
    logger.info("Starting parallel Extract & Transform (workers=%d) …", max_workers)
    Executor = ThreadPoolExecutor if use_threads else ProcessPoolExecutor
    results: list[dict[str, Any]] = []

    with Executor(max_workers=max_workers) as executor:
        future_map = {
            executor.submit(_etl_worker, brand_name, str(raw_dir)): brand_name
            for brand_name in brands
        }
        for future in as_completed(future_map):
            brand_name = future_map[future]
            try:
                result = future.result()
                results.append(result)
                logger.info(
                    "  [%s] extracted %d posts, %d comments",
                    brand_name,
                    len(result["posts_df"]),
                    len(result["comments_df"]),
                )
            except Exception as exc:
                logger.error("  [%s] ETL worker failed: %s", brand_name, exc)

    # ------------------------------------------------------------------
    # Sequential Load (SQLite serialisation)
    # ------------------------------------------------------------------
    logger.info("Loading into star-schema warehouse …")
    stats: dict[str, dict[str, int]] = {}

    for result in results:
        brand_name = result["brand_name"]
        posts_df = result["posts_df"]
        date_rows = result["date_rows"]
        comments_df = result["comments_df"]

        date_id_map = load_date_dimensions(engine, date_rows)
        posts_n = load_posts(engine, posts_df, date_id_map)
        comments_n = load_comments(engine, comments_df)

        stats[brand_name] = {
            "posts_inserted": posts_n,
            "comments_inserted": comments_n,
        }
        logger.info(
            "  [%s] loaded %d posts, %d comments",
            brand_name,
            posts_n,
            comments_n,
        )

    elapsed = time.time() - t_start
    total_posts = sum(s["posts_inserted"] for s in stats.values())
    total_comments = sum(s["comments_inserted"] for s in stats.values())
    logger.info("-" * 60)
    logger.info(
        "Pipeline complete in %.2fs – %d posts, %d comments loaded",
        elapsed,
        total_posts,
        total_comments,
    )
    return stats


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m social_media_etl.pipeline",
        description=(
            "Distributed ETL pipeline for Pakistani fashion-brand "
            "social-media competitive intelligence."
        ),
    )
    parser.add_argument(
        "--brands",
        nargs="+",
        metavar="BRAND",
        choices=BRAND_NAMES,
        default=BRAND_NAMES,
        help="Brands to process (default: all six).",
    )
    parser.add_argument(
        "--generate",
        action="store_true",
        help="(Re-)generate synthetic raw data before running ETL.",
    )
    parser.add_argument(
        "--threads",
        action="store_true",
        help="Use ThreadPoolExecutor instead of ProcessPoolExecutor.",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=PIPELINE_CONFIG["max_workers"],
        help="Number of parallel workers (default: %(default)s).",
    )
    return parser


if __name__ == "__main__":
    parser = _build_parser()
    args = parser.parse_args()
    result = run_pipeline(
        brands=args.brands,
        generate=args.generate,
        use_threads=args.threads,
        max_workers=args.workers,
    )
    sys.exit(0)
