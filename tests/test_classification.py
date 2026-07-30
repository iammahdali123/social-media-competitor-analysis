"""
tests/test_classification.py
==============================
Unit tests for the Campaign Type and Comment Intent classifiers.
"""

from __future__ import annotations

import pytest

from social_media_etl.classification.campaign_type import (
    classify_campaign_type,
    classify_campaign_types_bulk,
)
from social_media_etl.classification.comment_intent import (
    classify_comment_intent,
    classify_comment_intents_bulk,
)


# ===========================================================================
# Campaign Type Classifier
# ===========================================================================

class TestCampaignTypeClassifier:

    @pytest.mark.parametrize(
        "caption, expected",
        [
            # Sale/Discount
            ("Flat 30% OFF on select summer kurtas!", "Sale/Discount"),
            ("SALE ALERT 🚨 Up to 50% off on all western wear.", "Sale/Discount"),
            ("Weekend sale is live! Extra 20% off online orders", "Sale/Discount"),
            ("70% off on clearance stock – last chance!", "Sale/Discount"),
            ("Midnight Sale starts NOW. Extra 15% off with code MIDNIGHT", "Sale/Discount"),
            # Product Launch
            ("New arrivals are here! 🌸 #NewCollection", "Product Launch"),
            ("Introducing our first-ever loungewear line", "Product Launch"),
            ("Our Luxury Pret line is now available in-store", "Product Launch"),
            ("New pret drop is live 🔥", "Product Launch"),
            ("Limited Edition Heritage collection launching today", "Product Launch"),
            # Seasonal/Festival
            ("This Eid, drape yourself in our hand-embroidered luxury", "Seasonal/Festival"),
            ("Our Eid-ul-Adha festive range is live", "Seasonal/Festival"),
            ("Introducing our exclusive Khaddar Winter Collection", "Seasonal/Festival"),
            ("Sapphire Eid'24 – timeless silhouettes", "Seasonal/Festival"),
            ("Summer Collection 2024 – where elegance meets comfort", "Seasonal/Festival"),
            # Influencer/Collaboration
            ("Collab alert! @fashionblogger wears our latest piece", "Influencer/Collaboration"),
            ("Meet our brand ambassador @influencer", "Influencer/Collaboration"),
            ("Thrilled to partner with @celebrity for our festive shoot", "Influencer/Collaboration"),
            ("Spotted: @influencerpk looking gorgeous in Alkaram", "Influencer/Collaboration"),
            # User Generated Content
            ("Thank you @customername for your OOTD post!", "User Generated Content"),
            ("Our Insta fam @styleguru styled Sapphire like a pro", "User Generated Content"),
            ("Customer gallery: beautiful styling by @loyalcustomer", "User Generated Content"),
            # Brand Awareness (default)
            ("Bringing you the finest lawn since 1953", "Brand Awareness"),
            ("Celebrating Pakistan's rich textile heritage 🇵🇰", "Brand Awareness"),
            ("", "Brand Awareness"),
        ],
    )
    def test_single_caption(self, caption: str, expected: str) -> None:
        assert classify_campaign_type(caption) == expected

    def test_bulk_classification(self) -> None:
        captions = [
            "Flat 50% OFF on all items – mega sale!",
            "New arrivals are here!",
            "Celebrating Pakistani fashion since 1976",
        ]
        results = classify_campaign_types_bulk(captions)
        assert results[0] == "Sale/Discount"
        assert results[1] == "Product Launch"
        assert results[2] == "Brand Awareness"

    def test_bulk_with_none(self) -> None:
        results = classify_campaign_types_bulk([None, "50% off sale now!"])
        assert results[0] == "Brand Awareness"
        assert results[1] == "Sale/Discount"

    def test_case_insensitive(self) -> None:
        assert classify_campaign_type("FLAT 30% OFF") == "Sale/Discount"
        assert classify_campaign_type("flat 30% off") == "Sale/Discount"

    def test_none_input(self) -> None:
        assert classify_campaign_type(None) == "Brand Awareness"  # type: ignore[arg-type]

    def test_non_string_input(self) -> None:
        assert classify_campaign_type(123) == "Brand Awareness"  # type: ignore[arg-type]


# ===========================================================================
# Comment Intent Classifier
# ===========================================================================

class TestCommentIntentClassifier:

    @pytest.mark.parametrize(
        "comment, expected",
        [
            # Purchase Intent
            ("How much does this cost?", "Purchase Intent"),
            ("Where can I buy this? Is it available in Lahore?", "Purchase Intent"),
            ("Price please? 💖", "Purchase Intent"),
            ("Can I order this online? What's the link?", "Purchase Intent"),
            ("Do you deliver to Islamabad?", "Purchase Intent"),
            ("Is this available in size L?", "Purchase Intent"),
            # Inquiry
            ("When will the next sale start?", "Inquiry"),
            ("Is this fabric lawn or cotton?", "Inquiry"),
            ("Do you have this in a different colour?", "Inquiry"),
            ("What are your store timings?", "Inquiry"),
            # Complaint
            ("The quality has really gone down lately 😞", "Complaint"),
            ("I ordered last week and still no update on my delivery, very disappointing!", "Complaint"),
            ("The colour faded after first wash, not impressed at all.", "Complaint"),
            ("Your customer service is terrible, never buying from here again.", "Complaint"),
            # Compliment
            ("Absolutely in love with this design! 😍❤️", "Compliment"),
            ("This is gorgeous! My favourite brand forever 💕", "Compliment"),
            ("Beautiful fabric and amazing stitching quality ✨", "Compliment"),
            ("Definitely buying this! 😍", "Compliment"),
            # Spam
            ("Follow me for fashion tips @fashionguru99", "Spam"),
            ("Check out my page for daily giveaways 🎁", "Spam"),
            ("Win free clothes – follow me now!", "Spam"),
            # Neutral
            ("Ok", "Neutral"),
            ("Nice", "Neutral"),
            ("👍", "Neutral"),
            ("", "Neutral"),
        ],
    )
    def test_single_comment(self, comment: str, expected: str) -> None:
        assert classify_comment_intent(comment) == expected

    def test_bulk_classification(self) -> None:
        comments = [
            "How much is this?",
            "Absolutely love it!",
            "Follow my page @spam",
            "Ok",
        ]
        results = classify_comment_intents_bulk(comments)
        assert results[0] == "Purchase Intent"
        assert results[1] == "Compliment"
        assert results[2] == "Spam"
        assert results[3] == "Neutral"

    def test_bulk_with_none(self) -> None:
        results = classify_comment_intents_bulk([None, "Never buying again, worst brand"])
        assert results[0] == "Neutral"
        assert results[1] == "Complaint"

    def test_case_insensitive(self) -> None:
        assert classify_comment_intent("HOW MUCH DOES THIS COST?") == "Purchase Intent"
        assert classify_comment_intent("ABSOLUTELY IN LOVE WITH THIS") == "Compliment"

    def test_none_input(self) -> None:
        assert classify_comment_intent(None) == "Neutral"  # type: ignore[arg-type]

    def test_spam_priority_over_compliment(self) -> None:
        # Spam rules have highest priority
        result = classify_comment_intent("Check out my page, this is gorgeous!")
        assert result == "Spam"
