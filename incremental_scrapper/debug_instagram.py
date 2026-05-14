import os
import json
from dotenv import load_dotenv
from apify_client import ApifyClient

load_dotenv()
APIFY_API_TOKEN = os.getenv("APIFY_API_TOKEN")

client = ApifyClient(APIFY_API_TOKEN)

# Scrape that specific post to see what comment data is available
post_url = "https://www.instagram.com/p/DXen0NcCftE/"

print("🔍 Fetching post details and checking for comments...\n")

posts_input = {
    "addParentData": False,
    "directUrls": [post_url],
    "resultsLimit": 1,
    "resultsType": "posts",
    "searchLimit": 1,
    "searchType": "hashtag"
}

posts_run = client.actor("apify/instagram-api-scraper").call(run_input=posts_input)
posts = client.dataset(posts_run["defaultDatasetId"]).list_items().items
posts_list = list(posts)

if posts_list:
    post = posts_list[0]
    print("✅ Post found!\n")
    print(f"Post ID: {post.get('id')}")
    print(f"Post URL: {post.get('url')}")
    print(f"Caption: {post.get('caption', '')[:100]}")
    print(f"Likes: {post.get('likesCount')}")
    print(f"Comments Count: {post.get('commentsCount')}")
    print(f"\n--- Comment Fields Available ---")
    
    # Check for latestComments
    latest_comments = post.get("latestComments", [])
    print(f"latestComments count: {len(latest_comments)}")
    
    if latest_comments:
        print(f"\n✅ Found {len(latest_comments)} comments in latestComments!")
        print("\n--- First Comment Structure ---")
        print(json.dumps(latest_comments[0], indent=2, default=str)[:1000])
    else:
        print("⚠️  latestComments is empty or not available")
    
    print(f"\n--- Full Post Keys ---")
    print(list(post.keys()))
    
else:
    print("❌ Post not found")
