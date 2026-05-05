import os
import datetime
import time
import json
from dotenv import load_dotenv
from apify_client import ApifyClient
import gspread

# ==========================================
# 1. CONFIGURATION
# ==========================================
load_dotenv()
APIFY_API_TOKEN = os.getenv("APIFY_API_TOKEN")
GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID")
SERVICE_ACCOUNT_FILE = "service_account.json"

POSTS_LIMIT = 50  # Change this to adjust posts per page/profile
COMMENTS_LIMIT = 50  # Change this to adjust comments per post

PROGRESS_FILE = "scraping_progress.json"  # Track progress for resumability

# ==========================================
# PROGRESS TRACKING
# ==========================================
def load_progress():
    """Load scraping progress from file."""
    if os.path.exists(PROGRESS_FILE):
        try:
            with open(PROGRESS_FILE, "r") as f:
                return json.load(f)
        except:
            pass
    return {"facebook_pages": {}, "instagram_pages": {}}

def save_progress(progress):
    """Save scraping progress to file."""
    with open(PROGRESS_FILE, "w") as f:
        json.dump(progress, f, indent=2)
    print(f"  💾 Progress saved")

def is_page_complete(progress, platform, page_name):
    """Check if a page has been completely scraped."""
    if platform == "facebook":
        return progress["facebook_pages"].get(page_name, {}).get("completed", False)
    else:
        return progress["instagram_pages"].get(page_name, {}).get("completed", False)

def init_page_progress(progress, platform, page_name):
    """Initialize progress tracking for a page."""
    if platform == "facebook":
        if page_name not in progress["facebook_pages"]:
            progress["facebook_pages"][page_name] = {
                "completed": False,
                "posts_scraped": 0,
                "comments_scraped": 0
            }
    else:
        if page_name not in progress["instagram_pages"]:
            progress["instagram_pages"][page_name] = {
                "completed": False,
                "posts_scraped": 0,
                "comments_scraped": 0
            }

def update_page_progress(progress, platform, page_name, posts_count=0, comments_count=0, completed=False):
    """Update progress for a page."""
    if platform == "facebook":
        if page_name in progress["facebook_pages"]:
            progress["facebook_pages"][page_name]["posts_scraped"] = posts_count
            progress["facebook_pages"][page_name]["comments_scraped"] += comments_count
            progress["facebook_pages"][page_name]["completed"] = completed
    else:
        if page_name in progress["instagram_pages"]:
            progress["instagram_pages"][page_name]["posts_scraped"] = posts_count
            progress["instagram_pages"][page_name]["comments_scraped"] += comments_count
            progress["instagram_pages"][page_name]["completed"] = completed

# ==========================================
# 2. FACEBOOK PAGES TO SCRAPE (Fashion Brands)
# ==========================================
FACEBOOK_PAGES = [
    {"name": "Baroque", "url": "https://www.facebook.com/baroquepk/"}
]

# ==========================================
# 3. INSTAGRAM PAGES TO SCRAPE (Fashion Brands)
# ==========================================
INSTAGRAM_PAGES = [
    {"name": "Baroque", "url": "https://www.instagram.com/baroque_official"},
    {"name": "Beech Tree", "url": "https://www.instagram.com/beechtree_pk/"},
    {"name": "Cross Stitch", "url": "https://www.instagram.com/crossstitch_official"},
    {"name": "Khaadi", "url": "https://www.instagram.com/khaadi"},
    {"name": "So Kamal", "url": "https://www.instagram.com/so.kamal.official/"},
    {"name": "Generation", "url": "https://www.instagram.com/generation_pk"}
]

# ==========================================
# 4. ACTOR CONFIGURATION
# ==========================================
ACTORS = {
    "facebook_posts": {
        "id": "apify/facebook-posts-scraper",
        "get_input": lambda page_url: {
            "captionText": True,
            "resultsLimit": POSTS_LIMIT,
            "startUrls": [{"url": page_url}]
        }
    },
    "facebook_comments": {
        "id": "apify/facebook-comments-scraper",
        "get_input": lambda post_url: {
            "includeNestedComments": True,
            "resultsLimit": COMMENTS_LIMIT,
            "startUrls": [{"url": post_url}]
        }
    },
    "instagram": {
        "id": "apify/instagram-api-scraper",
        "get_posts_input": lambda profile_url: {
            "addParentData": False,
            "directUrls": [profile_url],
            "resultsLimit": POSTS_LIMIT,
            "resultsType": "posts",
            "searchLimit": 1,
            "searchType": "hashtag"
        },
        "get_comments_input": lambda post_url: {
            "addParentData": False,
            "directUrls": [post_url],
            "resultsLimit": COMMENTS_LIMIT,
            "resultsType": "comments",
            "searchLimit": 1,
            "searchType": "hashtag"
        }
    }
}

# ==========================================
# 4. HELPER FUNCTIONS
# ==========================================
def create_or_get_worksheet(spreadsheet, sheet_name):
    """Create worksheet if it doesn't exist, otherwise get it."""
    try:
        return spreadsheet.worksheet(sheet_name)
    except gspread.exceptions.WorksheetNotFound:
        print(f"  📋 Creating new tab: {sheet_name}")
        return spreadsheet.add_worksheet(title=sheet_name, rows="1000", cols="30")

def push_posts_to_sheets(spreadsheet, page_name, posts):
    """Push post data to Google Sheets with analytics-ready structure."""
    if not posts:
        return
    
    worksheet = create_or_get_worksheet(spreadsheet, "Facebook_posts")
    
    # Set headers if empty
    if not worksheet.get_all_records():
        headers = ["Platform", "Page", "Post_URL", "Post_ID", "Posted_At", "Post_Text", "Likes", "Shares", "Comments_Count", "Scraped_At"]
        worksheet.append_row(headers)
    
    # Debug: print available fields from first post
    if posts:
        print(f"  📋 Available fields in first post: {list(posts[0].keys())}")
    
    rows_to_insert = []
    for post in posts:
        # Extract correct field names from Facebook scraper JSON
        post_text = post.get("text") or ""
        
        # Use 'time' for ISO timestamp or 'timestamp' for Unix timestamp
        post_timestamp = post.get("time") or post.get("timestamp") or ""
        
        # Use exact field names from scraper
        likes = post.get("likes") or 0
        shares = post.get("shares") or 0
        comments_count = post.get("comments") or 0
        post_id = post.get("postId") or post.get("id") or ""
        
        row = [
            "Facebook",
            page_name,
            post.get("url", ""),
            post_id,
            str(post_timestamp),
            str(post_text)[:500],  # Limit text to 500 chars
            likes,
            shares,
            comments_count,
            datetime.datetime.now(datetime.timezone.utc).isoformat()
        ]
        rows_to_insert.append(row)
    
    worksheet.append_rows(rows_to_insert)
    print(f"  ✅ Pushed {len(rows_to_insert)} posts from {page_name}")
    return posts

def push_comments_to_sheets(spreadsheet, post_url, post_id, page_name, comments):
    """Push comment data to Google Sheets with analytics-ready structure."""
    if not comments:
        return
    
    worksheet = create_or_get_worksheet(spreadsheet, "facebook_comments")
    
    # Set headers if empty
    if not worksheet.get_all_records():
        headers = ["Platform", "Page", "Post_ID", "Comment_ID", "Comment_Author", "Comment_Date", "Comment_Text", "Comment_Likes", "Scraped_At"]
        worksheet.append_row(headers)
    
    rows_to_insert = []
    for comment in comments:
        # Extract correct field names from Facebook comment scraper JSON
        comment_author = comment.get("profileName") or comment.get("author") or "Unknown"
        comment_text = comment.get("text") or ""
        comment_likes = comment.get("likesCount") or comment.get("likes") or 0
        comment_id = comment.get("commentId") or comment.get("id") or ""
        comment_date = comment.get("date") or ""
        
        row = [
            "Facebook",
            page_name,
            post_id,
            comment_id,
            comment_author,
            str(comment_date),
            str(comment_text)[:500],  # Limit text to 500 chars
            comment_likes,
            datetime.datetime.now(datetime.timezone.utc).isoformat()
        ]
        rows_to_insert.append(row)
    
    worksheet.append_rows(rows_to_insert)
    print(f"    ✅ Pushed {len(rows_to_insert)} comments")

def push_instagram_posts_to_sheets(spreadsheet, page_name, posts):
    """Push comprehensive Instagram post data to Google Sheets."""
    if not posts:
        return
    
    worksheet = create_or_get_worksheet(spreadsheet, "instagram_posts")
    
    # Set headers if empty - comprehensive schema
    if not worksheet.get_all_records():
        headers = [
            "Platform", "Page", "Post_ID", "Post_URL", "Short_Code", "Type",
            "Caption", "Hashtags", "Mentions", "Posted_At", "Likes", "Comments_Count",
            "Owner_Name", "Owner_Username", "Owner_ID",
            "Image_Count", "First_Image_URL", "Comments_Disabled",
            "Child_Posts_Count", "First_Comment", "Scraped_At"
        ]
        worksheet.append_row(headers)
    
    rows_to_insert = []
    for post in posts:
        post_timestamp = post.get("timestamp") or ""
        hashtags = ", ".join(post.get("hashtags", [])) if post.get("hashtags") else ""
        mentions = ", ".join(post.get("mentions", [])) if post.get("mentions") else ""
        images = post.get("images", [])
        first_image = images[0] if images else ""
        child_posts = post.get("childPosts", [])
        
        row = [
            "Instagram",
            page_name,
            post.get("id", ""),
            post.get("url", ""),
            post.get("shortCode", ""),
            post.get("type", ""),
            str(post.get("caption", ""))[:1000],  # Limit text to 1000 chars
            hashtags,
            mentions,
            str(post_timestamp),
            post.get("likesCount", 0),
            post.get("commentsCount", 0),
            post.get("ownerFullName", ""),
            post.get("ownerUsername", ""),
            post.get("ownerId", ""),
            len(images),
            first_image,
            post.get("isCommentsDisabled", False),
            len(child_posts),
            post.get("firstComment", ""),
            datetime.datetime.now(datetime.timezone.utc).isoformat()
        ]
        rows_to_insert.append(row)
    
    worksheet.append_rows(rows_to_insert)
    print(f"  ✅ Pushed {len(rows_to_insert)} posts from {page_name}")
    return posts

def push_instagram_comments_to_sheets(spreadsheet, post_url, post_id, page_name, comments):
    """Push comprehensive Instagram comment data to Google Sheets."""
    if not comments:
        return
    
    worksheet = create_or_get_worksheet(spreadsheet, "instagram_comments")
    
    # Set headers if empty - comprehensive schema
    if not worksheet.get_all_records():
        headers = [
            "Platform", "Page", "Post_ID", "Post_URL", 
            "Comment_ID", "Comment_URL", "Comment_Text",
            "Author_Username", "Author_Full_Name", "Author_ID", "Author_FBID",
            "Author_Profile_Pic_URL", "Is_Verified", "Is_Private",
            "Comment_Likes", "Replies_Count", "Comment_Posted_At",
            "Scraped_At"
        ]
        worksheet.append_row(headers)
    
    rows_to_insert = []
    for idx, comment in enumerate(comments):
        # Extract main comment data
        comment_id = comment.get("id", f"{post_id}_comment_{idx}")
        comment_text = comment.get("text", "")
        comment_url = comment.get("commentUrl", "")
        comment_likes = comment.get("likesCount", 0)
        replies_count = comment.get("repliesCount", 0)
        comment_timestamp = comment.get("timestamp", "")
        
        # Extract author data from owner object (prioritize owner object for complete data)
        owner = comment.get("owner", {})
        author_username = owner.get("username") or comment.get("ownerUsername", "Unknown")
        author_full_name = owner.get("full_name", "")
        author_id = owner.get("id", comment.get("ownerId", ""))
        author_fbid = owner.get("fbid_v2", "")
        author_profile_pic = owner.get("profile_pic_url") or comment.get("ownerProfilePicUrl", "")
        is_verified = owner.get("is_verified", False)
        is_private = owner.get("is_private", False)
        
        row = [
            "Instagram",
            page_name,
            post_id,
            post_url,
            comment_id,
            comment_url,
            str(comment_text)[:1000],  # Limit text to 1000 chars
            author_username,
            author_full_name,
            author_id,
            author_fbid,
            author_profile_pic,
            is_verified,
            is_private,
            comment_likes,
            replies_count,
            str(comment_timestamp),
            datetime.datetime.now(datetime.timezone.utc).isoformat()
        ]
        rows_to_insert.append(row)
    
    worksheet.append_rows(rows_to_insert)
    print(f"    ✅ Pushed {len(rows_to_insert)} comments (with post_id: {post_id})")

# ==========================================
# 5. MAIN ORCHESTRATOR
# ==========================================
def run_facebook_360():
    print("🚀 Starting Facebook 360° Post & Comments Analyzer...\n")
    
    # Load progress from previous runs
    progress = load_progress()
    print(f"📂 Progress tracking initialized from: {PROGRESS_FILE}\n")
    
    client = ApifyClient(APIFY_API_TOKEN)
    
    # Authenticate with Google Sheets
    try:
        gc = gspread.service_account(filename=SERVICE_ACCOUNT_FILE)
        sh = gc.open_by_key(GOOGLE_SHEET_ID)
    except Exception as e:
        print(f"❌ Google Sheets Auth Error: {e}")
        return
    
    # Initialize progress for new pages (only on first run)
    if not progress["facebook_pages"] and not progress["instagram_pages"]:
        for page in FACEBOOK_PAGES:
            init_page_progress(progress, "facebook", page["name"])
        for page in INSTAGRAM_PAGES:
            init_page_progress(progress, "instagram", page["name"])
        print("📋 Initializing progress tracking for all pages\n")
    
    # Clear existing data to start fresh (only on first run)
    if not progress["facebook_pages"] or all(not v.get("completed") for v in progress["facebook_pages"].values()):
        try:
            sh.del_worksheet(sh.worksheet("Facebook_posts"))
            sh.del_worksheet(sh.worksheet("facebook_comments"))
            sh.del_worksheet(sh.worksheet("instagram_posts"))
            sh.del_worksheet(sh.worksheet("instagram_comments"))
            print("🔄 Cleared previous data\n")
        except:
            pass  # Sheets don't exist yet
    
    total_facebook_posts = 0
    total_facebook_comments = 0
    total_instagram_posts = 0
    total_instagram_comments = 0
    
    # ==========================================
    # PHASE 1: FACEBOOK SCRAPING
    # ==========================================
    print("\n" + "="*70)
    print("PHASE 1: 📱 FACEBOOK SCRAPING")
    print("="*70 + "\n")
    
    for page_idx, page in enumerate(FACEBOOK_PAGES, 1):
        page_name = page['name']
        
        # Check if already completed
        if is_page_complete(progress, "facebook", page_name):
            print(f"✅ [{page_idx}/{len(FACEBOOK_PAGES)}] {page_name} - Already completed")
            total_facebook_posts += progress["facebook_pages"][page_name]["posts_scraped"]
            total_facebook_comments += progress["facebook_pages"][page_name]["comments_scraped"]
            continue
        
        init_page_progress(progress, "facebook", page_name)
        print(f"{'='*70}")
        print(f"📱 [{page_idx}/{len(FACEBOOK_PAGES)}] {page_name}")
        print(f"   URL: {page['url']}")
        print(f"{'='*70}\n")
        
        try:
            # Step 1: Scrape posts from the page
            print(f"[1] Fetching top {POSTS_LIMIT} posts...")
            posts_input = ACTORS["facebook_posts"]["get_input"](page['url'])
            posts_run = client.actor(ACTORS["facebook_posts"]["id"]).call(run_input=posts_input)
            posts = client.dataset(posts_run["defaultDatasetId"]).list_items().items
            
            posts_list = list(posts)
            if not posts_list:
                print(f"  ⚠️  No posts found\n")
                update_page_progress(progress, "facebook", page_name, 0, 0, True)
                save_progress(progress)
                continue
            
            print(f"  ✓ Found {len(posts_list)} posts")
            
            # Push posts to sheets
            push_posts_to_sheets(sh, page_name, posts_list)
            total_facebook_posts += len(posts_list)
            
            # Step 2: For each post, scrape comments
            print(f"\n[2] Scraping comments ({COMMENTS_LIMIT} per post)...\n")
            total_comments_this_page = 0
            for post_idx, post in enumerate(posts_list, 1):
                post_url = post.get("url")
                post_id = post.get("postId") or post.get("id") or ""
                if not post_url:
                    continue
                
                print(f"  Post {post_idx}/{len(posts_list)}: {post_url[:60]}...")
                
                try:
                    comments_input = ACTORS["facebook_comments"]["get_input"](post_url)
                    comments_run = client.actor(ACTORS["facebook_comments"]["id"]).call(run_input=comments_input)
                    comments = client.dataset(comments_run["defaultDatasetId"]).list_items().items
                    
                    comments_list = list(comments)
                    if comments_list:
                        push_comments_to_sheets(sh, post_url, post_id, page_name, comments_list)
                        total_facebook_comments += len(comments_list)
                        total_comments_this_page += len(comments_list)
                    else:
                        print(f"    ℹ️  No comments")
                    
                except Exception as e:
                    print(f"    ❌ Error: {str(e)[:100]}")
                
                # Wait between requests
                if post_idx < len(posts_list):
                    print("    ⏳ Waiting 3 seconds...")
                    time.sleep(3)
            
            # Mark as complete and save progress
            update_page_progress(progress, "facebook", page_name, len(posts_list), total_comments_this_page, True)
            save_progress(progress)
            print()
        
        except Exception as e:
            print(f"❌ Error for {page_name}: {str(e)[:100]}")
            save_progress(progress)
            print()
        
        # Wait between pages
        if page_idx < len(FACEBOOK_PAGES):
            print("⏳ Waiting 10 seconds before next brand...\n")
            time.sleep(10)
    
    # ==========================================
    # PHASE 2: INSTAGRAM SCRAPING - DISABLED
    # ==========================================
    print("\n" + "="*70)
    print("PHASE 2: 📸 INSTAGRAM SCRAPING")
    print("="*70 + "\n")
    
    for profile_idx, profile in enumerate(INSTAGRAM_PAGES, 1):
        profile_name = profile['name']
        
        # Check if already completed
        if is_page_complete(progress, "instagram", profile_name):
            print(f"✅ [{profile_idx}/{len(INSTAGRAM_PAGES)}] {profile_name} - Already completed")
            total_instagram_posts += progress["instagram_pages"][profile_name]["posts_scraped"]
            total_instagram_comments += progress["instagram_pages"][profile_name]["comments_scraped"]
            continue
        
        init_page_progress(progress, "instagram", profile_name)
        print(f"{'='*70}")
        print(f"📸 [{profile_idx}/{len(INSTAGRAM_PAGES)}] {profile_name}")
        print(f"   URL: {profile['url']}")
        print(f"{'='*70}\n")
        
        try:
            # Step 1: Scrape posts from the profile
            print(f"[1] Fetching top {POSTS_LIMIT} posts...")
            posts_input = ACTORS["instagram"]["get_posts_input"](profile['url'])
            posts_run = client.actor(ACTORS["instagram"]["id"]).call(run_input=posts_input)
            posts = client.dataset(posts_run["defaultDatasetId"]).list_items().items
            
            posts_list = list(posts)
            if not posts_list:
                print(f"  ⚠️  No posts found\n")
                update_page_progress(progress, "instagram", profile_name, 0, 0, True)
                save_progress(progress)
                continue
            
            print(f"  ✓ Found {len(posts_list)} posts")
            
            # Push posts to sheets
            push_instagram_posts_to_sheets(sh, profile_name, posts_list)
            total_instagram_posts += len(posts_list)
            
            # Step 2: For each post, extract and store comments from latestComments
            print(f"\n[2] Extracting comments from posts...\n")
            total_comments_this_profile = 0
            for post_idx, post in enumerate(posts_list, 1):
                post_url = post.get("url", "")
                post_id = post.get("id", "")
                if not post_url or not post_id:
                    continue
                
                print(f"  Post {post_idx}/{len(posts_list)}: {post_url[:60]}...")
                
                try:
                    # Extract latestComments from the post response (no additional API call needed!)
                    latest_comments = post.get("latestComments", [])
                    if latest_comments:
                        push_instagram_comments_to_sheets(sh, post_url, post_id, profile_name, latest_comments)
                        total_instagram_comments += len(latest_comments)
                        total_comments_this_profile += len(latest_comments)
                        print(f"    ✅ Extracted {len(latest_comments)} comments")
                    else:
                        print(f"    ℹ️  No comments available")
                    
                except Exception as e:
                    print(f"    ❌ Error: {str(e)[:100]}")
                
                # Small delay between posts
                if post_idx < len(posts_list):
                    time.sleep(1)
            
            # Mark as complete and save progress
            update_page_progress(progress, "instagram", profile_name, len(posts_list), total_comments_this_profile, True)
            save_progress(progress)
            print()
        
        except Exception as e:
            print(f"❌ Error for {profile_name}: {str(e)[:100]}")
            save_progress(progress)
            print()
        
        # Wait between profiles
        if profile_idx < len(INSTAGRAM_PAGES):
            print("⏳ Waiting 10 seconds before next brand...\n")
            time.sleep(10)
    
    # ==========================================
    # FINAL SUMMARY
    # ==========================================
    print("="*70)
    print("🎉 Facebook 360° + Instagram Analysis Complete!")
    print("="*70)
    print(f"\n📊 Summary:")
    print(f"  Facebook:")
    print(f"    • Posts Scraped: {total_facebook_posts}")
    print(f"    • Comments Scraped: {total_facebook_comments}")
    print(f"  Instagram:")
    print(f"    • Posts Scraped: {total_instagram_posts}")
    print(f"    • Comments Scraped: {total_instagram_comments}")
    print(f"  Total:")
    print(f"    • Posts: {total_facebook_posts + total_instagram_posts}")
    print(f"    • Comments: {total_facebook_comments + total_instagram_comments}")
    print(f"\n📁 Data Structure:")
    print(f"  • Posts Tab: Platform | Page | Post_URL | Post_ID | Post_Text | Likes | Shares/Comments_Count | Scraped_At")
    print(f"  • Comments Tab: Platform | Page | Post_URL | Comment_Author | Comment_Text | Comment_Likes | Scraped_At")
    print(f"\n⚙️  Configuration:")
    print(f"  • Posts per page/profile: {POSTS_LIMIT}")
    print(f"  • Comments per post: {COMMENTS_LIMIT}")
    print(f"\n💡 Tip: To clear progress and restart from scratch, delete the '{PROGRESS_FILE}' file")
    print(f"📂 Progress is saved in: {PROGRESS_FILE}")

if __name__ == "__main__":
    run_facebook_360()