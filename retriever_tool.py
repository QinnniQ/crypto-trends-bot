from dotenv import load_dotenv
load_dotenv()
from langchain.vectorstores import Chroma
from langchain.embeddings import OpenAIEmbeddings
from langchain.schema import Document
from typing import List

CHROMA_DIR = "chroma_store"

# Initialize once
embedding = OpenAIEmbeddings()
vectordb = Chroma(persist_directory=CHROMA_DIR, embedding_function=embedding)

def retrieve_crypto_context(query: str, k: int = 4) -> List[Document]:
    results = vectordb.similarity_search(query, k=k)
    return results

if __name__ == "__main__":
    # Test the tool directly
    test_query = "What did Rekt Capital say about Ethereum?"
    docs = retrieve_crypto_context(test_query)

    for i, doc in enumerate(docs, 1):
        print(f"\n--- Chunk {i} ---")
        print(doc.metadata.get("source"), "|", doc.metadata.get("title"))
        print(doc.page_content[:500])
