import os
import json
from pathlib import Path
from langchain.text_splitter import RecursiveCharacterTextSplitter

INPUT_DIR = "articles"
CHUNKED_FILE = "chunked_docs.json"

def load_articles():
    docs = []
    for file in os.listdir(INPUT_DIR):
        if file.endswith(".json"):
            with open(os.path.join(INPUT_DIR, file), "r", encoding="utf-8") as f:
                data = json.load(f)
                docs.append(data)
    return docs

def chunk_documents(articles, chunk_size=500, chunk_overlap=100):
    splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    all_chunks = []

    for article in articles:
        text = article["content"]
        metadata = {
            "source": article.get("source", ""),
            "title": article.get("title", ""),
            "url": article.get("url", ""),
            "date": article.get("date", "")
        }

        chunks = splitter.split_text(text)
        for i, chunk in enumerate(chunks):
            all_chunks.append({
                "text": chunk,
                "metadata": {**metadata, "chunk_id": i}
            })

    return all_chunks

if __name__ == "__main__":
    print("📄 Loading articles...")
    articles = load_articles()
    print(f"✅ Loaded {len(articles)} articles")

    print("🔪 Chunking...")
    chunked_docs = chunk_documents(articles)

    with open(CHUNKED_FILE, "w", encoding="utf-8") as f:
        json.dump(chunked_docs, f, ensure_ascii=False, indent=2)

    print(f"💾 Saved {len(chunked_docs)} chunks to {CHUNKED_FILE}")
