import praw
import json
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
import os

# 📦 Load from .env
load_dotenv()
REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID")
REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET")
REDDIT_USER_AGENT = os.getenv("REDDIT_USER_AGENT")

# 🛠 Settings
SUBREDDITS = ["CryptoCurrency", "Bitcoin", "ethfinance"]
LIMIT = 25
SORT = "hot"  # hot | new | top

def init_reddit():
    return praw.Reddit(
        client_id=REDDIT_CLIENT_ID,
        client_secret=REDDIT_CLIENT_SECRET,
        user_agent=REDDIT_USER_AGENT
    )

def fetch_posts(reddit, subreddit_name):
    subreddit = reddit.subreddit(subreddit_name)
    fetch_method = {
        "hot": subreddit.hot,
        "top": subreddit.top,
        "new": subreddit.new
    }.get(SORT, subreddit.hot)

    results = []
    for post in fetch_method(limit=LIMIT):
        if post.stickied:
            continue
        results.append({
            "subreddit": subreddit_name,
            "title": post.title,
            "text": post.selftext,
            "score": post.score,
            "url": post.url,
            "permalink": f"https://reddit.com{post.permalink}",
            "created_utc": datetime.utcfromtimestamp(post.created_utc).isoformat()
        })
    return results

if __name__ == "__main__":
    reddit = init_reddit()
    all_posts = []

    for sub in SUBREDDITS:
        print(f"📡 Scraping r/{sub}...")
        posts = fetch_posts(reddit, sub)
        print(f"✅ {len(posts)} posts from r/{sub}")
        all_posts.extend(posts)

    Path("reddit_data").mkdir(exist_ok=True)
    output_path = "reddit_data/reddit_posts.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(all_posts, f, ensure_ascii=False, indent=2)

    print(f"\n💾 Saved {len(all_posts)} posts → {output_path}")
