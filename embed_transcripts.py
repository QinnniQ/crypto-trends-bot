import os
import json
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma

# === LOAD ENV VARIABLES ===
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("❌ OPENAI_API_KEY not found in .env file or environment variables.")

# === CONFIG ===
TRANSCRIPTS_DIR = Path(r"C:\Users\nicho\Documents\crypto_bot\data\transcripts")
VIDEOS_JSON = Path(r"C:\Users\nicho\Documents\crypto_bot\videos.json")
CHROMA_DB_DIR = Path(r"C:\Users\nicho\Documents\crypto_bot\chroma_db")

# === LOAD VIDEO METADATA ===
with open(VIDEOS_JSON, "r", encoding="utf-8") as f:
    videos = json.load(f)

def get_video_id(url):
    if "v=" in url:
        return url.split("v=")[-1]
    elif "youtu.be" in url:
        return url.split("/")[-1]
    return None

video_map = {}
for v in videos:
    vid_id = get_video_id(v["url"])
    if vid_id:
        video_map[vid_id] = v

# === INIT COMPONENTS ===
embeddings = OpenAIEmbeddings(model="text-embedding-ada-002", api_key=OPENAI_API_KEY)
text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)

all_docs = []

# === LOAD, CHUNK, ADD METADATA ===
for transcript_file in TRANSCRIPTS_DIR.glob("*.txt"):
    video_id = transcript_file.stem.split("_")[-1]
    video_info = video_map.get(video_id, {})

    loader = TextLoader(str(transcript_file), encoding="utf-8")
    docs = loader.load()

    for doc in docs:
        doc.metadata = {
            "source": "youtube",
            "video_id": video_id,
            "title": video_info.get("title", transcript_file.stem),
            "url": video_info.get("url", ""),
            "ingest_date": datetime.utcnow().strftime("%Y-%m-%d")
        }

    split_docs = text_splitter.split_documents(docs)
    all_docs.extend(split_docs)

print(f"✅ Loaded and split {len(all_docs)} chunks from {len(list(TRANSCRIPTS_DIR.glob('*.txt')))} transcripts.")

# === STORE IN CHROMA ===
db = Chroma.from_documents(all_docs, embeddings, persist_directory=str(CHROMA_DB_DIR))
db.persist()
print(f"📦 Stored {len(all_docs)} chunks in ChromaDB at {CHROMA_DB_DIR}")
