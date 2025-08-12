import json
from pathlib import Path
from urllib.parse import urlparse, parse_qs

# === CONFIG ===
TRANSCRIPTS_DIR = Path(r"C:\Users\nicho\Documents\crypto_bot\data\transcripts")
VIDEOS_JSON = Path(r"C:\Users\nicho\Documents\crypto_bot\videos.json")

# === HELPERS ===
def get_video_id(url):
    parsed_url = urlparse(url)
    if parsed_url.hostname in ["www.youtube.com", "youtube.com"]:
        return parse_qs(parsed_url.query).get("v", [None])[0]
    elif parsed_url.hostname == "youtu.be":
        return parsed_url.path.lstrip("/")
    return None

# === STEP 1: FOLDER CHECK ===
print("📂 Checking transcripts folder...")
if TRANSCRIPTS_DIR.exists() and TRANSCRIPTS_DIR.is_dir():
    print(f"✅ Folder exists: {TRANSCRIPTS_DIR}")
else:
    print(f"❌ Folder not found: {TRANSCRIPTS_DIR}")
    raise SystemExit

# === STEP 2: COUNT FILES ===
txt_files = list(TRANSCRIPTS_DIR.glob("*.txt"))
print(f"📝 Found {len(txt_files)} transcript files")

if len(txt_files) == 0:
    print("❌ No transcripts found in this folder. Stopping check.")
    raise SystemExit

# === STEP 3: LOAD VIDEO LIST ===
if not VIDEOS_JSON.exists():
    print(f"❌ Could not find videos.json at: {VIDEOS_JSON}")
    raise SystemExit

with open(VIDEOS_JSON, "r", encoding="utf-8") as f:
    videos = json.load(f)

print(f"🎥 Total videos in videos.json: {len(videos)}")

# === STEP 4: MATCH TRANSCRIPTS TO VIDEOS ===
existing_ids = {p.stem.split("_")[-1] for p in txt_files}
missing_videos = [v for v in videos if get_video_id(v["url"]) not in existing_ids]

if missing_videos:
    print(f"⚠ Missing transcripts: {len(missing_videos)}")
    for mv in missing_videos:
        print("-", mv["title"])
else:
    print("✅ All transcripts accounted for!")

# === STEP 5: FINAL SUMMARY ===
print("\n--- SUMMARY ---")
print(f"Folder: {TRANSCRIPTS_DIR}")
print(f"Total transcript files: {len(txt_files)}")
print(f"Total videos listed: {len(videos)}")
print(f"Missing transcripts: {len(missing_videos)}")
print("----------------")
if not missing_videos:
    print("🎯 You are ready to embed into ChromaDB!")
else:
    print("🚨 You still have missing transcripts. Finish those before embedding.")

