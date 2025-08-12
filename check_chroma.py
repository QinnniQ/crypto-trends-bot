from langchain_community.vectorstores import Chroma

CHROMA_DB_DIR = r"C:\Users\nicho\Documents\crypto_bot\chroma_db"

db = Chroma(persist_directory=CHROMA_DB_DIR)
print("Number of documents:", db._collection.count())
