from dotenv import load_dotenv
load_dotenv()

from typing import List
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import OpenAIEmbeddings
from langchain.schema import Document
import pathlib

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
CHROMA_DIR = str(REPO_ROOT / "chroma_store")

embedding = OpenAIEmbeddings()
vectordb = Chroma(persist_directory=CHROMA_DIR, embedding_function=embedding)

def retrieve_crypto_context(query: str, k: int = 4) -> List[Document]:
    return vectordb.similarity_search(query, k=k)
