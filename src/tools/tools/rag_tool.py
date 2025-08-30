from dotenv import load_dotenv
load_dotenv()

import os
import pathlib
from langchain.tools import Tool
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import OpenAIEmbeddings

# Resolve absolute Chroma dir at REPO ROOT
REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
CHROMA_DIR = str(REPO_ROOT / "chroma_store")  # make sure your ingestion wrote here

# Build embeddings + vectordb once
embedding = OpenAIEmbeddings()

# Handle missing/empty DB gracefully
def _load_vectordb():
    try:
        return Chroma(persist_directory=CHROMA_DIR, embedding_function=embedding)
    except Exception as e:
        return f"❌ Could not load Chroma at {CHROMA_DIR}: {e}"

_vectordb = _load_vectordb()

def retrieve_crypto_context(query: str, k: int = 4) -> str:
    """
    Search local Chroma knowledge base for relevant chunks and
    return a compact, readable context block with source info.
    """
    if isinstance(_vectordb, str):
        return _vectordb  # early error (string message)

    try:
        docs = _vectordb.similarity_search(query, k=k)
    except Exception as e:
        return f"❌ Retrieval error: {e}"

    if not docs:
        return (
            "No relevant information found in the knowledge base.\n"
            f"(Chroma path: {CHROMA_DIR}) — Is your DB populated? Run your ingestion."
        )

    lines = []
    for i, doc in enumerate(docs, 1):
        meta = doc.metadata or {}
        source = meta.get("source", "unknown")
        title = meta.get("title", "Untitled")
        url = meta.get("url", "")
        preview = (doc.page_content or "").strip()[:1000]

        lines.append(f"--- Source {i} ---")
        lines.append(f"Source: {source.upper()}")
        lines.append(f"Title: {title}")
        if source == "reddit" and meta.get("subreddit"):
            lines.append(f"Subreddit: r/{meta['subreddit']}")
        if url:
            lines.append(f"URL: {url}")
        lines.append("")
        lines.append(preview)
        lines.append("")

    return "\n".join(lines).strip()

rag_tool = Tool(
    name="CryptoTranscriptRetriever",
    func=retrieve_crypto_context,
    description=(
        "Use this for Reddit/Substack/ transcript-based answers from the local knowledge base. "
        "Input should be a full user question like: 'What is Reddit saying about BTC?' or "
        "'Summarize Substack takes on Solana.'"
    ),
)
