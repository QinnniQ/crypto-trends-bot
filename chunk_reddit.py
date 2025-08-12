import json
from pathlib import Path
from langchain.text_splitter import RecursiveCharacterTextSplitter

INPUT_FILE = "reddit_data/reddit_posts.json"
OUTPUT_FILE = "reddit_data/chunked_reddit.json"

def load_reddit_posts():
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def chunk_posts(posts, chunk_size=500, chunk_overlap=100):
    splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    all_chunks = []

    for post in posts:
        content = f"{post['title']}\n\n{post['text']}".strip()
        if not content:
            continue

        chunks = splitter.split_text(content)
        for i, chunk in enumerate(chunks):
            chunk_data = {
                "text": chunk,
                "metadata": {
                    "source": "reddit",
                    "subreddit": post.get("subreddit", ""),
                    "title": post.get("title", ""),
                    "url": post.get("permalink", ""),
                    "score": post.get("score", 0),
                    "date": post.get("created_utc", ""),
                    "chunk_id": i
                }
            }
            all_chunks.append(chunk_data)

    return all_chunks

if __name__ == "__main__":
    print("📂 Loading reddit posts...")
    posts = load_reddit_posts()
    print(f"✅ Loaded {len(posts)} posts")

    print("🔪 Chunking...")
    chunked = chunk_posts(posts)

    Path("reddit_data").mkdir(exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(chunked, f, ensure_ascii=False, indent=2)

    print(f"💾 Saved {len(chunked)} chunks to {OUTPUT_FILE}")
