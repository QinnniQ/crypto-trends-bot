from dotenv import load_dotenv
load_dotenv()

from langchain.tools import Tool
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import OpenAIEmbeddings
from langchain.schema import Document

CHROMA_DIR = "chroma_store"
embedding = OpenAIEmbeddings()
vectordb = Chroma(persist_directory=CHROMA_DIR, embedding_function=embedding)

def retrieve_crypto_context(query: str, k: int = 4) -> str:
    docs = vectordb.similarity_search(query, k=k)
    if not docs:
        return "No relevant information found in the knowledge base."

    response = ""
    for i, doc in enumerate(docs, 1):
        meta = doc.metadata
        source = meta.get("source", "unknown")
        title = meta.get("title", "Untitled")
        url = meta.get("url", "")
        preview = doc.page_content[:1000].strip()

        response += f"\n--- Source {i} ---\n"
        response += f"Source: {source.upper()}\n"
        response += f"Title: {title}\n"

        if source == "reddit":
            subreddit = meta.get("subreddit", "")
            response += f"Subreddit: r/{subreddit}\n"

        if url:
            response += f"URL: {url}\n"

        response += f"\n{preview}\n"

    return response.strip()

rag_tool = Tool(
    name="CryptoTranscriptRetriever",
    func=retrieve_crypto_context,
    description=(
        "Use this to answer crypto questions using expert content from Substack newsletters and Reddit posts. "
        "Input should be a full user question like: 'What did Rekt Capital say about Ethereum?' "
        "or 'What's Reddit saying about Solana?'"
    )
)
