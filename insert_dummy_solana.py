import json
from pathlib import Path
from datetime import datetime

def inject_dummy(path, chunk):
    if Path(path).exists():
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = []

    # Prevent duplicates
    if any("Solana is seeing renewed interest" in d["text"] for d in data):
        print(f"⚠️ Dummy content already exists in {path}")
        return

    data.append(chunk)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"✅ Injected dummy chunk into {path}")

if __name__ == "__main__":
    timestamp = datetime.utcnow().isoformat()

    reddit_chunk = {
        "text": "Solana is seeing renewed interest with rising NFT activity and TVL. Some Redditors are comparing its recent recovery to ETH's early cycles.",
        "metadata": {
            "source": "reddit",
            "subreddit": "CryptoCurrency",
            "title": "Is Solana quietly staging a comeback?",
            "url": "https://reddit.com/r/CryptoCurrency/comments/mock_solana/",
            "score": 894,
            "date": timestamp,
            "chunk_id": 0
        }
    }

    substack_chunk = {
        "text": "Solana has seen a major uptick in developer adoption over the past month. Its transaction throughput and NFT ecosystem continue to be major differentiators in Layer 1 narratives.",
        "metadata": {
            "source": "substack",
            "title": "Solana Update - July 2025",
            "url": "https://rektcapital.substack.com/p/mock-solana-update",
            "date": timestamp,
            "chunk_id": 0
        }
    }

    inject_dummy("reddit_data/chunked_reddit.json", reddit_chunk)
    inject_dummy("chunked_docs.json", substack_chunk)
