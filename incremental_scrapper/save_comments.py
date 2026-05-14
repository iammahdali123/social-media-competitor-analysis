import os
import json
from dotenv import load_dotenv
from apify_client import ApifyClient
import gspread
from datetime import datetime

load_dotenv()
APIFY_API_TOKEN = os.getenv("APIFY_API_TOKEN")
GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID")
SERVICE_ACCOUNT_FILE = "service_account.json"

client = ApifyClient(APIFY_API_TOKEN)
auth = gspread.service_account(SERVICE_ACCOUNT_FILE)
sh = auth.open_by_key(GOOGLE_SHEET_ID)

def create_or_get_worksheet(spreadsheet, sheet_name):
    """Create worksheet if it doesn't exist, otherwise get it."""
    try:
        return spreadsheet.worksheet(sheet_name)
    except gspread.exceptions.WorksheetNotFound:
        print(f"  📋 Creating new tab: {sheet_name}")
        return spreadsheet.add_worksheet(sheet_name, 100, 20)

# Scrape that specific post
post_url = "https://www.instagram.com/p/DXen0NcCftE/"

print("🔍 Fetching post and comments...\n")

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
    post_id = post.get("id", "")
    post_url = post.get("url", "")
    
    latest_comments = post.get("latestComments", [])
    print(f"✅ Found post with {len(latest_comments)} comments\n")
    
    if latest_comments:
        # Get or create instagram_comments sheet
        ws = create_or_get_worksheet(sh, "instagram_comments")
        
        # Clear existing data (keep headers if they exist)
        ws.clear()
        
        # Add headers
        headers = [
            "Platform", "Page", "Post_ID", "Post_URL", "Comment_ID", "Comment_URL",
            "Comment_Text", "Author_Username", "Author_Full_Name", "Author_ID",
            "Author_FBID", "Author_Profile_Pic_URL", "Is_Verified", "Is_Private",
            "Comment_Likes", "Replies_Count", "Comment_Posted_At", "Scraped_At"
        ]
        ws.insert_row(headers, index=1)
        
        # Add comments
        scraped_at = datetime.utcnow().isoformat() + "Z"
        rows = []
        
        for idx, comment in enumerate(latest_comments, 1):
            owner = comment.get("owner", {})
            
            row = [
                "Instagram",                                    # Platform
                "Baroque",                                      # Page
                post_id,                                        # Post_ID
                post_url,                                       # Post_URL
                comment.get("id", ""),                          # Comment_ID
                f"https://www.instagram.com/p/{post_id}#comment_{comment.get('id', '')}",  # Comment_URL
                comment.get("text", "")[:1000],                 # Comment_Text (1000 char limit)
                comment.get("ownerUsername", ""),               # Author_Username
                owner.get("full_name", "") or owner.get("username", ""),  # Author_Full_Name
                owner.get("id", comment.get("ownerUsername", "")),  # Author_ID
                owner.get("fbid_v2", ""),                       # Author_FBID
                comment.get("ownerProfilePicUrl", ""),          # Author_Profile_Pic_URL
                owner.get("is_verified", False),                # Is_Verified
                owner.get("is_private", False),                 # Is_Private
                comment.get("likesCount", 0),                   # Comment_Likes
                comment.get("repliesCount", 0),                 # Replies_Count
                comment.get("timestamp", ""),                   # Comment_Posted_At
                scraped_at                                      # Scraped_At
            ]
            rows.append(row)
            print(f"  ✅ Comment {idx}: {comment.get('ownerUsername', 'Unknown')} - \"{comment.get('text', '')[:50]}...\"")
        
        # Insert all rows
        ws.append_rows(rows)
        print(f"\n✅ Pushed {len(rows)} comments to Google Sheet!")
        print(f"📊 Sheet: instagram_comments")
        
        # Display the data
        print("\n" + "="*80)
        print("Comment Data Saved:")
        print("="*80)
        for i, comment in enumerate(latest_comments, 1):
            owner = comment.get("owner", {})
            print(f"\nComment #{i}:")
            print(f"  ID: {comment.get('id')}")
            print(f"  Text: {comment.get('text')}")
            print(f"  Author: {comment.get('ownerUsername')}")
            print(f"  Author Full Name: {owner.get('full_name', 'N/A')}")
            print(f"  Author ID: {owner.get('id', 'N/A')}")
            print(f"  Verified: {owner.get('is_verified', False)}")
            print(f"  Private: {owner.get('is_private', False)}")
            print(f"  Likes: {comment.get('likesCount')}")
            print(f"  Replies: {comment.get('repliesCount')}")
            print(f"  Posted: {comment.get('timestamp')}")
    else:
        print("❌ No comments found")
else:
    print("❌ Post not found")
