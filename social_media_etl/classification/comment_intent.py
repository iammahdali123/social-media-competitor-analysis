"""
classification/comment_intent.py
=================================
Rule-based Comment Intent classifier.

Inspects the text of a social-media comment and assigns one of six intent labels
defined in ``config.COMMENT_INTENTS``.  Rules are applied in priority order; the
first match wins.  If no rule matches, the comment is classified as "Neutral".

Comment Intent Labels
---------------------
1. Purchase Intent – user wants to buy (price questions, order requests, delivery)
2. Inquiry         – general questions about product, stock, availability
3. Complaint       – negative feedback, dissatisfaction, bad experience
4. Compliment      – positive feedback, praise, admiration
5. Spam            – self-promotion, giveaways, follow-back requests
6. Neutral         – generic / uninformative comments
"""

from __future__ import annotations

import re
from typing import Optional

# ---------------------------------------------------------------------------
# Keyword rules (compiled once at import time)
# ---------------------------------------------------------------------------

_RULES: list[tuple[str, re.Pattern]] = [
    (
        "Spam",
        re.compile(
            r"\b(follow\s+(me|back|for|my)|check\s+(out\s+)?my\s+(page|profile|account)|"
            r"win\s+free|giveaway|grow\s+your|dm\s+me|free\s+(followers?|likes?)|"
            r"subscribe|click\s+(here|the\s+link)|visit\s+my)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "Purchase Intent",
        re.compile(
            r"\b(how\s+much|price\s+(please|ka|hai)?|kya\s+price|what('s|\s+is)\s+the\s+(price|cost|rate)|"
            r"where\s+(can\s+I|to)\s+buy|where\s+(is\s+it\s+)?available|link\s+please|"
            r"do\s+you\s+deliver|delivery\s+(to|charges?)|how\s+(do\s+I|to)\s+(order|purchase)|"
            r"can\s+I\s+order|is\s+it\s+available|in\s+stock|size\s+(available|chart)|"
            r"available\s+in\s+size)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "Inquiry",
        re.compile(
            r"\b(when\s+will|when\s+is\s+the\s+next|what\s+(fabric|material|size)|"
            r"is\s+this\s+(fabric|lawn|cotton|chiffon)|do\s+you\s+have\s+(this|it)\s+in|"
            r"store\s+timings?|what\s+are\s+(your\s+)?timings?|unstitched|"
            r"different\s+colou?r|available\s+online|any\s+new\s+collection)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "Complaint",
        re.compile(
            r"\b(quality\s+(has\s+(\w+\s+)?)?gone\s+down|bad\s+quality|poor\s+quality|"
            r"disappointing|disappointed|very\s+bad|worst|terrible|awful|horrible|"
            r"never\s+buying|never\s+again|faded\s+after|colour\s+fade|"
            r"no\s+update\s+on\s+(my\s+)?order|not\s+impressed|bad\s+experience|"
            r"customer\s+service\s+is\s+(terrible|bad|worst|horrible))\b",
            re.IGNORECASE,
        ),
    ),
    (
        "Compliment",
        re.compile(
            r"\b(love\s+(this|it|the)|absolutely\s+(love|beautiful|stunning)|"
            r"never\s+disappoints?|stunning|gorgeous|beautiful|amazing|"
            r"in\s+love\s+with|my\s+favou?rite\s+brand|so\s+pretty|"
            r"definitely\s+buying|obsessed|so\s+cute|perfect\s+(colou?r|combination|fabric))\b",
            re.IGNORECASE,
        ),
    ),
]

_DEFAULT_INTENT = "Neutral"


def classify_comment_intent(comment: str) -> str:
    """
    Classify the intent of a single *comment* string.

    Parameters
    ----------
    comment:
        Raw comment text.

    Returns
    -------
    One of the six intent-label names defined in ``config.COMMENT_INTENTS``.
    """
    if not comment or not isinstance(comment, str):
        return _DEFAULT_INTENT

    for intent, pattern in _RULES:
        if pattern.search(comment):
            return intent

    return _DEFAULT_INTENT


def classify_comment_intents_bulk(comments: list[Optional[str]]) -> list[str]:
    """
    Classify a list of comments in bulk.

    Parameters
    ----------
    comments:
        List of comment strings (``None`` treated as empty).

    Returns
    -------
    List of intent-label strings, same length as *comments*.
    """
    return [classify_comment_intent(c or "") for c in comments]
