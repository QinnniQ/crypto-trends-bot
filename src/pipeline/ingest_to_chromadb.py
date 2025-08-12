from dotenv import load_dotenv
load_dotenv()

import os
import json
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import OpenAIEmbeddings
from langchain.schema import Document

CHROMA_DIR = "chroma_store"

def load_chunks(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        raw_chunks = json.load(f)

    return [
        Document(page_content=item["text"], metadata=item["metadata"])
        for item in raw_chunks
    ]

if __name__ == "__main__":
    print("📦 Loading Substack chunks...")
    substack_docs = load_chunks("chunked_docs.json")
    print(f"✅ Loaded {len(substack_docs)} Substack documents")

    print("📦 Loading Reddit chunks...")
    reddit_docs = load_chunks("reddit_data/chunked_reddit.json")
    print(f"✅ Loaded {len(reddit_docs)} Reddit documents")

    all_docs = substack_docs + reddit_docs
    print(f"📚 Total documents to embed: {len(all_docs)}")

    print("🧠 Initializing OpenAI embeddings...")
    embedding = OpenAIEmbeddings()

    print("💾 Ingesting into ChromaDB...")
    vectordb = Chroma.from_documents(
        documents=all_docs,
        embedding=embedding,
        persist_directory=CHROMA_DIR
    )

    vectordb.persist()
    print(f"✅ ChromaDB updated and persisted at: {CHROMA_DIR}")
