import json
from pathlib import Path
from urllib.parse import urlparse, parse_qs
import shutil

# === CONFIG ===
TRANSCRIPTS_DIR = Path(r"C:\Users\nicho\Documents\crypto_bot\data\transcripts")
VIDEOS_JSON = Path(r"C:\Users\nicho\Documents\crypto_bot\videos.json")
EXTRAS_DIR = TRANSCRIPTS_DIR / "_extras"

EXTRAS_DIR.mkdir(exist_ok=True)

# === HELPER ===
def get_video_id(url):
    parsed_url = urlparse(url)
    if parsed_url.hostname in ["www.youtube.com", "youtube.com"]:
        return parse_qs(parsed_url.query).get("v", [None])[0]
    elif parsed_url.hostname == "youtu.be":
        return parsed_url.path.lstrip("/")
    return None

# === LOAD VALID VIDEO IDS ===
with open(VIDEOS_JSON, "r", encoding="utf-8") as f:
    videos = json.load(f)

valid_ids = {get_video_id(v["url"]) for v in videos}

# === MOVE INVALID FILES ===
for f in TRANSCRIPTS_DIR.glob("*.txt"):
    file_id = f.stem.split("_")[-1]
    if file_id not in valid_ids:
        print(f"⚠ Moving extra file: {f.name}")
        shutil.move(str(f), str(EXTRAS_DIR / f.name))

print("✅ Cleanup complete.")
