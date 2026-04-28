"""
classification/campaign_type.py
================================
Rule-based Campaign Type classifier.

The classifier inspects the text of a social-media post caption and assigns one
of six campaign types defined in ``config.CAMPAIGN_TYPES``.  Rules are applied
in priority order; the first match wins.  If no rule matches, the post is
classified as "Brand Awareness" (the catch-all).

Campaign Types
--------------
1. Sale/Discount           – promotional pricing language
2. Product Launch          – new product / collection announcements
3. Brand Awareness         – heritage, storytelling, lifestyle content
4. Seasonal/Festival       – season- or festival-specific campaigns
5. Influencer/Collaboration – partnerships and ambassador mentions
6. User Generated Content  – customer re-posts and community spotlights
"""

from __future__ import annotations

import re
from typing import Optional

# ---------------------------------------------------------------------------
# Keyword rules (compiled once at import time for performance)
# ---------------------------------------------------------------------------

_RULES: list[tuple[str, re.Pattern]] = [
    (
        "User Generated Content",
        re.compile(
            r"\b(ugc|regram|repost|customer\s+(photo|style|gallery)|styled\s+by|"
            r"community\s+member|outfit\s+of\s+the\s+day|ootd|our\s+(insta\s+)?fam|"
            r"fan\s+photo|@\w+\s+(looks?|style))\b",
            re.IGNORECASE,
        ),
    ),
    (
        "Influencer/Collaboration",
        re.compile(
            r"\b(collab|collaboration|ambassador|brand\s+ambassador|partner(ed|ship)?|"
            r"featuring|ft\.?|sponsored|meet\s+our|we\s+collab|thrilled\s+to\s+partner|"
            r"spotted[:\s]+@\w+|collab\s+alert)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "Seasonal/Festival",
        re.compile(
            r"\b(eid[\s\-]?ul?[\s\-]?(adha|fitr)?|eid|festive|winter\s+collection|"
            r"summer\s+collection|spring\s+collection|monsoon|khaddar|autumn|"
            r"fall\s+collection|aw\d{2}|ss\d{2}|holiday\s+collection|ramzan|"
            r"ramadan|christmas|new\s+year)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "Sale/Discount",
        re.compile(
            r"\b(\d+\s*%\s*off|flat\s+\d+\s*%|sale|discount|clearance|flash\s+sale|"
            r"mega\s+sale|end\s+of\s+season|eosy|promo|deal|offer|limited\s+time|"
            r"shop\s+now|last\s+chance|midnight\s+sale|extra\s+\d+\s*%|code\s+\w+|"
            r"half\s+price|weekend\s+sale|online\s+sale)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "Product Launch",
        re.compile(
            r"\b(new\s+arrivals?|new\s+collection|new\s+(pret|lawn|kurta)|launch(ing|ed)?|"
            r"introducing|now\s+(available|live|in\s+store)|new\s+drop|drop\s+is\s+(live|here)|"
            r"collection\s+is\s+(live|here|out|now)|debut|first[\s\-]ever|limited\s+edition)\b",
            re.IGNORECASE,
        ),
    ),
]

_DEFAULT_CAMPAIGN_TYPE = "Brand Awareness"


def classify_campaign_type(caption: str) -> str:
    """
    Classify the campaign type of a post from its *caption*.

    Parameters
    ----------
    caption:
        Raw post caption string.

    Returns
    -------
    One of the six campaign-type names defined in ``config.CAMPAIGN_TYPES``.
    """
    if not caption or not isinstance(caption, str):
        return _DEFAULT_CAMPAIGN_TYPE

    for campaign_type, pattern in _RULES:
        if pattern.search(caption):
            return campaign_type

    return _DEFAULT_CAMPAIGN_TYPE


def classify_campaign_types_bulk(captions: list[Optional[str]]) -> list[str]:
    """
    Classify a list of captions in bulk.

    Parameters
    ----------
    captions:
        List of caption strings (``None`` values are treated as empty).

    Returns
    -------
    List of campaign-type name strings, same length as *captions*.
    """
    return [classify_campaign_type(c or "") for c in captions]
