from dotenv import load_dotenv
load_dotenv()

import os
import pathlib
from langchain.tools import Tool
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import OpenAIEmbeddings

# Resolve an absolute Chroma dir at the REPO ROOT
# This avoids "relative path" issues when you run from different folders.
# File path here is .../src/tools/rag_tool.py
REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
CHROMA_DIR = str(REPO_ROOT / "chroma_store")  # change if your DB lives elsewhere

# Build embeddings + vectordb once (module-level cache)
embedding = OpenAIEmbeddings()
vectordb = Chroma(persist_directory=CHROMA_DIR, embedding_function=embedding)

def retrieve_crypto_context(query: str, k: int = 4) -> str:
    """
    Searches your local Chroma knowledge base for relevant chunks and
    returns a compact, readable context block the agent can use directly.
    """
    try:
        docs = vectordb.similarity_search(query, k=k)
    except Exception as e:
        return f"❌ Retrieval error: {e}"

    if not docs:
        return "No relevant information found in the knowledge base."

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
        if source == "reddit":
            subreddit = meta.get("subreddit", "")
            if subreddit:
                lines.append(f"Subreddit: r/{subreddit}")
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
        "Use this to answer crypto questions using expert content from Substack newsletters and Reddit posts. "
        "Input should be a full user question like: 'What did Rekt Capital say about Ethereum?' "
        "or 'What's Reddit saying about Solana?'"
    ),
)
