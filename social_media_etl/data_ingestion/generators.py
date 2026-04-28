"""
data_ingestion/generators.py
============================
Generates realistic synthetic social-media data for each of the six Pakistani
fashion brands.  The output is written as two JSON-Lines files per brand under
``data/raw/<brand_name>/``:

  posts.jsonl    – one post record per line
  comments.jsonl – one comment record per line

Each record mimics the fields returned by Instagram / Facebook Graph APIs so
that the downstream ETL layer needs only minimal adjustment to work with real
API data.
"""

from __future__ import annotations

import json
import random
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from faker import Faker

from social_media_etl.config import (
    BRANDS,
    PIPELINE_CONFIG,
    PLATFORMS,
    RAW_DIR,
)

fake = Faker()
random.seed(42)

# ---------------------------------------------------------------------------
# Text templates per brand – captions reflecting real campaign styles
# ---------------------------------------------------------------------------

_CAPTION_POOL: dict[str, list[str]] = {
    "Khaadi": [
        "Celebrate the art of handcrafted fabric. New arrivals are here! 🌸 #Khaadi #NewCollection",
        "Flat 30% OFF on select summer kurtas. Shop now before stock runs out! 🛍️ #KhaadiSale",
        "This Eid, drape yourself in our hand-embroidered luxury lawn. ✨ #EidCollection",
        "Meet our brand ambassador @influencer – rocking the Khaadi look! 💫 #KhaadiCollab",
        "Our customer @user123 styled our Gulbahar print beautifully 😍 #KhaadiFamily",
        "New season, new palette. Explore our Autumn-Winter 2024 lineup 🍂 #AW24",
        "Introducing the Limited Edition Heritage collection – woven stories of Pakistan 🇵🇰",
        "50% off on last season's pret! Stock is limited – grab yours today 🔥 #MegaSale",
    ],
    "Gul Ahmed": [
        "Bringing you the finest lawn since 1953. Summer'24 collection out now 🌺 #GulAhmed",
        "Up to 40% off on printed lawn suits! 🎉 Hurry – limited time only #GulAhmedSale",
        "Our Eid-ul-Adha festive range is live. Celebrate in style 🐑✨ #FestiveWear",
        "Collab alert! @fashionblogger wears our latest Master Replica. Stunning! 💖",
        "Customer gallery: beautiful styling by @loyalcustomer with our Zinnia print 🌹",
        "Introducing IDEAS by Gul Ahmed – casual wear for the modern Pakistani woman 👗",
        "Summer Formal Collection 2024 – where elegance meets everyday comfort 🌸",
        "Weekend sale is live! Extra 20% off online orders 🛒 #OnlineSale",
    ],
    "Alkaram Studio": [
        "New Alkaram Festival Collection is here – celebrate every moment in style 🎊",
        "Flat 25% off on all unstitched fabric bundles. Shop online now! 🛍️ #AlkaramSale",
        "Introducing SS'24 printed lawn – fresh florals for every mood 🌻 #SpringSummer",
        "Spotted: @influencerpk looking gorgeous in Alkaram's new formal edit ✨",
        "Thank you @customername for sharing this gorgeous outfit-of-the-day 💛 #AlkaramOOTD",
        "Our embroidered chiffon collection is now available in-store & online 🎀",
        "Monsoon Edit: soft pastel hues for the rainy season ☔ #MonsoonFashion",
        "70% off on clearance stock – last chance to grab your favourites! 💨",
    ],
    "Limelight": [
        "Your everyday wardrobe just got an upgrade. New pret drop is live 🔥 #Limelight",
        "SALE ALERT 🚨 Up to 50% off on all western wear. Shop before it's gone!",
        "Summer BBQ fits sorted. Check out our new printed co-ord sets 🌞 #SummerVibes",
        "We collab'd with @pakistanifashionista and we're obsessed 😍 #LimelightXInfluencer",
        "This week's style inspo comes from our community member @fashionlover 🌸 #OOTD",
        "Introducing our first-ever loungewear line – comfort meets cool 🛋️ #NewLaunch",
        "Flash sale this weekend only – 60% off on selected kurtis ⚡ #FlashSale",
        "Spring collection 2024 is finally here and it does NOT disappoint 🌷",
    ],
    "Sapphire": [
        "Sapphire Eid'24 – timeless silhouettes for your most special moments 🌙✨",
        "EOSY Sale is now live. Up to 50% off across all categories 🎉 #SapphireSale",
        "Launching our Luxury Pret line: redefining Pakistani contemporary fashion 👑",
        "The stunning @modelpk wears our Hana embroidered suit from the new edit 💫",
        "Our Insta fam @styleguru styled Sapphire like a pro ❤️ #SapphireStyle",
        "New Season, New Story. Explore Sapphire SS24 in stores now 🛍️",
        "Summer florals are calling – shop our printed lawn range online 🌸 #SummerLawn",
        "Midnight sale starts NOW. Extra 15% off with code MIDNIGHT 🌙 #MidnightSale",
    ],
    "Bonanza Satrangi": [
        "Satrangi Eid Collection is all about vibrant colours and timeless cuts 🌈 #Eid2024",
        "Satrangi Sale: Up to 60% off on unstitched & pret. Grab the best deals 💥",
        "Introducing our exclusive Khaddar Winter Collection – warmth in every thread 🍂",
        "Thrilled to partner with @celebrity for our festive shoot ✨ #Satrangi",
        "Love seeing our designs on you! @happycustomer you look amazing 😍 #CustomerLove",
        "New Arrivals: Hand-block printed cotton suits – traditional artistry reimagined 🎨",
        "Mega Mid-Season Sale is LIVE – don't miss out on iconic prints at half price!",
        "Summer Festive 2024 – celebrating Pakistan's rich textile heritage 🇵🇰",
    ],
}

_COMMENT_POOL: list[str] = [
    # Purchase Intent
    "How much does this cost?",
    "Where can I buy this? Is it available in Lahore?",
    "Price please? 💖",
    "Can I order this online? What's the link?",
    "Do you deliver to Islamabad?",
    "Is this available in size L?",
    "How do I place an order?",
    # Inquiry
    "When will the next sale start?",
    "Is this fabric lawn or cotton?",
    "Do you have this in a different colour?",
    "What are your store timings?",
    "Is this available in unstitched form too?",
    # Complaint
    "The quality has really gone down lately 😞",
    "I ordered last week and still no update on my delivery, very disappointing!",
    "The colour faded after first wash, not impressed at all.",
    "Your customer service is terrible, never buying from here again.",
    "Worst experience with your outlet staff today.",
    # Compliment
    "Absolutely in love with this design! 😍❤️",
    "Khaadi never disappoints, stunning collection as always!",
    "This is gorgeous! My favourite brand forever 💕",
    "Beautiful fabric and amazing stitching quality ✨",
    "Wow this is so pretty, definitely buying this! 😍",
    "The colour combination is just perfect 🌸",
    # Spam
    "Follow me for fashion tips @fashionguru99",
    "Check out my page for daily giveaways 🎁",
    "Win free clothes – follow me now!",
    "I can help grow your Instagram, DM me",
    # Neutral
    "Ok",
    "Seen",
    "Nice",
    "👍",
    "Interesting",
    "Will check it out",
]


def _random_date(start: str, end: str) -> datetime:
    """Return a random datetime between *start* and *end* (ISO date strings)."""
    start_dt = datetime.fromisoformat(start)
    end_dt = datetime.fromisoformat(end)
    delta = end_dt - start_dt
    random_seconds = random.randint(0, int(delta.total_seconds()))
    return start_dt + timedelta(seconds=random_seconds)


def generate_posts(brand: dict, n_posts: int, start_date: str, end_date: str) -> list[dict[str, Any]]:
    """Generate *n_posts* synthetic post records for *brand*."""
    captions = _CAPTION_POOL.get(brand["brand_name"], _CAPTION_POOL["Khaadi"])
    platform_names = [p["platform_name"] for p in PLATFORMS]
    posts: list[dict[str, Any]] = []
    for _ in range(n_posts):
        platform = random.choice(platform_names)
        posted_at = _random_date(start_date, end_date)
        likes = random.randint(100, 50_000)
        shares = random.randint(0, int(likes * 0.3))
        reach = random.randint(likes, likes * 10)
        posts.append(
            {
                "post_id": str(uuid.uuid4()),
                "brand_name": brand["brand_name"],
                "platform": platform,
                "caption": random.choice(captions),
                "posted_at": posted_at.isoformat(),
                "likes": likes,
                "shares": shares,
                "reach": reach,
                "saves": random.randint(0, int(likes * 0.15)),
                "video_views": random.randint(0, reach) if platform in ("Instagram", "TikTok") else 0,
                "post_url": f"https://{platform.lower().replace('/', '')}.com/p/{uuid.uuid4().hex[:11]}",
            }
        )
    return posts


def generate_comments(post_id: str, brand_name: str, avg_count: int) -> list[dict[str, Any]]:
    """Generate a variable number of synthetic comments for *post_id*."""
    n = max(1, int(random.gauss(avg_count, avg_count * 0.5)))
    return [
        {
            "comment_id": str(uuid.uuid4()),
            "post_id": post_id,
            "brand_name": brand_name,
            "comment_text": random.choice(_COMMENT_POOL),
            "commenter_username": fake.user_name(),
            "commented_at": (
                datetime.fromisoformat("2023-01-01")
                + timedelta(days=random.randint(0, 730))
            ).isoformat(),
            "likes": random.randint(0, 500),
        }
        for _ in range(n)
    ]


def generate_and_save(
    brand: dict,
    output_dir: Path | None = None,
    n_posts: int | None = None,
    avg_comments: int | None = None,
) -> tuple[list[dict], list[dict]]:
    """
    Generate synthetic posts and comments for *brand*, persist them as
    JSON-Lines files, and return the in-memory lists.

    Parameters
    ----------
    brand:
        Brand dict from ``config.BRANDS``.
    output_dir:
        Root directory for raw data.  Defaults to ``config.RAW_DIR``.
    n_posts:
        Number of posts to generate.  Defaults to ``PIPELINE_CONFIG["posts_per_brand"]``.
    avg_comments:
        Average comments per post.  Defaults to ``PIPELINE_CONFIG["avg_comments_per_post"]``.

    Returns
    -------
    (posts, comments) as lists of dicts.
    """
    if output_dir is None:
        output_dir = RAW_DIR
    if n_posts is None:
        n_posts = PIPELINE_CONFIG["posts_per_brand"]
    if avg_comments is None:
        avg_comments = PIPELINE_CONFIG["avg_comments_per_post"]

    brand_dir = Path(output_dir) / brand["brand_name"].replace(" ", "_")
    brand_dir.mkdir(parents=True, exist_ok=True)

    start_date = PIPELINE_CONFIG["data_start_date"]
    end_date = PIPELINE_CONFIG["data_end_date"]

    posts = generate_posts(brand, n_posts, start_date, end_date)
    all_comments: list[dict] = []
    for post in posts:
        all_comments.extend(
            generate_comments(post["post_id"], brand["brand_name"], avg_comments)
        )

    # Write JSON-Lines
    with open(brand_dir / "posts.jsonl", "w", encoding="utf-8") as fh:
        for record in posts:
            fh.write(json.dumps(record) + "\n")

    with open(brand_dir / "comments.jsonl", "w", encoding="utf-8") as fh:
        for record in all_comments:
            fh.write(json.dumps(record) + "\n")

    return posts, all_comments


def generate_all_brands(
    output_dir: Path | None = None,
    n_posts: int | None = None,
    avg_comments: int | None = None,
) -> dict[str, tuple[list[dict], list[dict]]]:
    """
    Generate and save data for all six brands.

    Returns a mapping of ``brand_name -> (posts, comments)``.
    """
    return {
        brand["brand_name"]: generate_and_save(
            brand, output_dir=output_dir, n_posts=n_posts, avg_comments=avg_comments
        )
        for brand in BRANDS
    }
