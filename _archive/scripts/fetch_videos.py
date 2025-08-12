import yt_dlp
import json
from pathlib import Path

# Direct /videos tab URLs so yt_dlp fetches only actual videos
CHANNELS = [
    "https://www.youtube.com/@CoinBureau/videos",
    "https://www.youtube.com/@Bankless/videos",
    "https://www.youtube.com/@Finematics/videos",
    "https://www.youtube.com/@AltcoinDaily/videos",
    "https://www.youtube.com/@CryptoBanter/videos",
    "https://www.youtube.com/@TheDefiant/videos"
]

MAX_VIDEOS_PER_CHANNEL = 10  # how many per channel


def fetch_latest_videos(channel_url, max_videos=10):
    """
    Fetch latest *actual video* URLs from a YouTube /videos tab.
    Filters out Shorts, Live tabs, and non-playable items.
    """
    ydl_opts = {
        'quiet': True,
        'extract_flat': True,   # metadata only, no downloads
        'dump_single_json': True
    }

    videos = []
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        print(f"📡 Fetching videos from: {channel_url}")
        info = ydl.extract_info(channel_url, download=False)

        entries = info.get("entries", [])
        for entry in entries:
            # Only include actual playable videos
            if entry.get("url") and "watch?v=" in entry.get("url"):
                video_id = entry["url"].split("v=")[-1]
                title = entry.get("title", "Untitled Video")
                videos.append({
                    "title": title,
                    "url": f"https://www.youtube.com/watch?v={video_id}"
                })
                if len(videos) >= max_videos:
                    break

    return videos


if __name__ == "__main__":
    all_videos = []

    for channel in CHANNELS:
        try:
            vids = fetch_latest_videos(channel, MAX_VIDEOS_PER_CHANNEL)
            all_videos.extend(vids)
        except Exception as e:
            print(f"⚠️ Skipping {channel} due to error: {e}")

    # Save cleaned results
    output_path = Path("videos.json")
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(all_videos, f, ensure_ascii=False, indent=2)

    print(f"\n✅ Saved {len(all_videos)} playable videos to {output_path.resolve()}")
