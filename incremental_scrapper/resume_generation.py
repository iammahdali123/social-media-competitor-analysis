#!/usr/bin/env python3
"""
Resume script to complete remaining comments for Generation page (posts 34-50)
"""

import json
import os
import time
from dotenv import load_dotenv
import gspread
from apify_client import ApifyClient

# Load environment variables
load_dotenv()
APIFY_API_TOKEN = os.getenv("APIFY_API_TOKEN")
GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID")

# Initialize clients
apify_client = ApifyClient(APIFY_API_TOKEN)
gs = gspread.service_account(filename="service_account.json")
sheet = gs.open_by_key(GOOGLE_SHEET_ID)

# Configuration
GENERATION_POSTS = [
    "https://www.facebook.com/generationpk/posts/pfbid02Rx2Ni6RkD...",
    "https://www.facebook.com/generationpk/posts/pfbid0kgZEGRYaA8...",
    "https://www.facebook.com/reel/976411718256561/...",
    "https://www.facebook.com/generationpk/posts/pfbid022W94bEpzK...",
    "https://www.facebook.com/generationpk/posts/pfbid02rHg3QYVUv...",
    "https://www.facebook.com/reel/2124603985058827/...",
    "https://www.facebook.com/generationpk/posts/pfbid09MZFXCr7vs...",
    "https://www.facebook.com/generationpk/posts/pfbid02cowxj5jo4...",
    "https://www.facebook.com/generationpk/posts/pfbid0Vz4bXdiw9p...",
    "https://www.facebook.com/generationpk/posts/pfbid02MaYjDhgqu...",
    "https://www.facebook.com/generationpk/posts/pfbid0UC6RfTaPvz...",
    "https://www.facebook.com/reel/3634318200041662/...",
    "https://www.facebook.com/generationpk/posts/pfbid02BxNhhsEia...",
    "https://www.facebook.com/generationpk/posts/pfbid0xBHSHiCfrw...",
    "https://www.facebook.com/generationpk/posts/pfbid02XrciZs2kw...",
    "https://www.facebook.com/generationpk/posts/pfbid0xcwyFLZi2j...",
    "https://www.facebook.com/generationpk/posts/pfbid02Y9mAESt gr...",
]

COMMENTS_LIMIT = 50
PLATFORM = "Facebook"
PAGE_NAME = "Generation"

def push_comments_to_sheets(comments, post_id):
    """Push comments to Google Sheets with Post_ID as primary identifier"""
    try:
        tab_name = "facebook_comments"
        
        # Try to get existing sheet or create new one
        try:
            ws = sheet.worksheet(tab_name)
        except gspread.exceptions.WorksheetNotFound:
            ws = sheet.add_worksheet(title=tab_name, rows=1, cols=9)
            # Add headers - aligned with main.py structure, Post_ID is primary identifier
            headers = ["Platform", "Page", "Post_ID", "Comment_ID", 
                      "Comment_Author", "Comment_Date", "Comment_Text", "Comment_Likes", "Scraped_At"]
            ws.append_row(headers)
        
        # Prepare rows
        rows = []
        for idx, comment in enumerate(comments):
            # Extract fields that are actually in the Apify response
            comment_text = comment.get("text") or ""
            comment_likes = comment.get("likesCount") or 0
            facebook_url = comment.get("facebookUrl") or ""
            
            # Generate commentId from URL hash if not present
            comment_id = comment.get("commentId") or comment.get("id")
            if not comment_id:
                # Generate a pseudo-ID from facebookUrl or use index
                comment_id = f"{post_id}_comment_{idx}" if post_id else f"comment_{idx}"
            
            # Extract author name if available in postTitle or use Unknown
            author = comment.get("profileName") or comment.get("author") or "Unknown"
            
            # Use current timestamp if date not available
            comment_date = comment.get("date") or comment.get("timestamp") or time.strftime("%Y-%m-%d %H:%M:%S")
            
            row = [
                PLATFORM,
                PAGE_NAME,
                post_id,  # Use the post_id passed as parameter (from parent post)
                comment_id,
                author,
                comment_date,
                comment_text,
                comment_likes,
                time.strftime("%Y-%m-%d %H:%M:%S")
            ]
            rows.append(row)
        
        if rows:
            ws.append_rows(rows)
            print(f"  ✅ Pushed {len(rows)} comments (stored with Post_ID: {post_id})")
            return len(rows)
        return 0
    
    except Exception as e:
        print(f"  ❌ Error pushing comments: {e}")
        return 0

def scrape_comments_for_post(post_url, post_id):
    """Scrape comments for a single post"""
    try:
        print(f"  Scraping comments for: {post_url[:60]}...")
        print(f"    Using Post_ID: {post_id}")
        
        actor_input = {
            "includeNestedComments": True,
            "resultsLimit": COMMENTS_LIMIT,
            "startUrls": [{"url": post_url}]
        }
        
        run = apify_client.actor("apify/facebook-comments-scraper").call(run_input=actor_input)
        
        comments = []
        for item in apify_client.dataset(run["defaultDatasetId"]).iterate_items():
            comments.append(item)
        
        if comments:
            count = push_comments_to_sheets(comments, post_id)
            print(f"    ⏳ Waiting 3 seconds...")
            time.sleep(3)
            return count
        else:
            print(f"    ℹ️  No comments found")
            return 0
    
    except Exception as e:
        if "Monthly usage hard limit exceeded" in str(e):
            print(f"    ❌ Error: {str(e)[:60]}...")
            return -1
        else:
            print(f"    ❌ Error: {e}")
            return 0

def main():
    """Main resume function"""
    print("\n" + "="*70)
    print("🔄 RESUMING: Generation Page Comments (Posts 34-50)")
    print("="*70 + "\n")
    
    # Get the actual posts from Google Sheets to get correct URLs and post IDs
    try:
        ws = sheet.worksheet("Facebook_posts")
        rows = ws.get_all_values()
        
        # Find Generation posts starting from row with post 34
        # First, skip header and count Generation rows
        generation_posts = []
        for i, row in enumerate(rows[1:], 1):  # Skip header
            if len(row) > 1 and row[1] == "Generation":  # row[1] is Page name
                generation_posts.append({
                    "url": row[2],  # Post_URL
                    "post_id": row[3],  # Post_ID
                    "row_num": i + 1
                })
        
        print(f"📊 Found {len(generation_posts)} Generation posts in sheet")
        
        # Start from post 34 (index 33)
        start_index = 33
        if start_index >= len(generation_posts):
            print("✅ All posts already processed!")
            return
        
        total_comments = 0
        for idx in range(start_index, len(generation_posts)):
            post = generation_posts[idx]
            post_num = idx + 1
            post_id = post['post_id']
            post_url = post['url']
            print(f"\n  Post {post_num}/{len(generation_posts)}: {post_url[:50]}...")
            print(f"    Post_ID: {post_id}")
            
            count = scrape_comments_for_post(post_url, post_id)
            
            if count == -1:
                print(f"\n⚠️  Hit API limit again. Stopping.\nResumed {total_comments} comments so far.")
                break
            
            total_comments += count
        
        print(f"\n✅ Completed! Total comments scraped: {total_comments}")
        
        # Update progress
        with open("scraping_progress.json", "r") as f:
            progress = json.load(f)
        progress["facebook_pages"]["Generation"]["comments_scraped"] = \
            progress["facebook_pages"]["Generation"]["comments_scraped"] + total_comments
        with open("scraping_progress.json", "w") as f:
            json.dump(progress, f, indent=2)
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()
