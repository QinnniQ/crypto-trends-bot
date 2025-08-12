import json
from pathlib import Path

# Paths
videos_json_path = Path(r"C:\Users\nicho\Documents\crypto_bot\videos.json")

# Titles to remove
discard_titles = [
    "Stack Sats by Gaming: 7 Free Bitcoin Apps You Can Download Now",
    "Altcoin ETFs INCOMING: SOL, XRP, ADA & PENGU - Top or Only Start?",
    "Why I Ditched Bitcoin Mining for Ethereum | Sam Tabar",
    "10 Bullish ETH Charts",
    "DEFI 2.0 - A New Narrative? OlympusDAO, Tokemak Explained",
    "The REAL Reason Ethereum Price Is Going UP! (urgent.)",
    "Spark (SPK): The DeFi Protocol Redefining Finance with Explosive Growth and Innovation"
]

# Load
with open(videos_json_path, "r", encoding="utf-8") as f:
    videos = json.load(f)

# Filter out discarded titles
cleaned_videos = [v for v in videos if v["title"] not in discard_titles]

# Save cleaned JSON
with open(videos_json_path, "w", encoding="utf-8") as f:
    json.dump(cleaned_videos, f, indent=2, ensure_ascii=False)

print(f"✅ Cleaned videos.json: {len(videos)} → {len(cleaned_videos)} entries kept")
