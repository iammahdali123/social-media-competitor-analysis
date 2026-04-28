"""
social_media_etl
================
Distributed ETL pipeline for Pakistani fashion-brand competitive intelligence.

Pipeline stages
---------------
1. data_ingestion  – synthetic / raw-data generators per brand
2. etl.extract     – read raw JSON/CSV snapshots from disk
3. etl.transform   – clean, normalise, classify, and shape into star-schema format
4. etl.load        – upsert dimension and fact rows into the SQLite warehouse
5. pipeline        – concurrent.futures orchestrator that fans out across all 6 brands
"""

__version__ = "1.0.0"
