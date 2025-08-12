import json
import os
import subprocess
from pathlib import Path
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound
import yt_dlp

# Paths
VIDEOS_JSON = Path("videos.json")
TRANSCRIPTS_DIR = Path("data/transcripts")
TRANSCRIPTS_DIR.mkdir(parents=True, exist_ok=True)

# Choose Whisper model ("small" is faster, "medium" better, "large-v3" best)
WHISPER_MODEL = "small"


def transcribe_with_captions(video_id, title):
    """Try getting transcript via YouTube captions."""
    try:
        transcript_data = YouTubeTranscriptApi.get_transcript(video_id)
        text = " ".join([entry['text'] for entry in transcript_data])
        print(f"✅ Captions found for: {title}")
        return text
    except (TranscriptsDisabled, NoTranscriptFound):
        print(f"⚠️ No captions for: {title}")
    except Exception as e:
        print(f"⚠️ Caption error for {title}: {e}")
    return None


def transcribe_with_whisper(video_url, title):
    """Download audio and transcribe with Whisper."""
    safe_title = "".join(c for c in title if c.isalnum() or c in " _-").strip()
    audio_path = TRANSCRIPTS_DIR / f"{safe_title}.mp3"

    # Download audio with yt-dlp
    ydl_opts = {
        "quiet": True,
        "format": "bestaudio/best",
        "outtmpl": str(audio_path),
        "postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": "mp3"}],
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([video_url])
        print(f"🎧 Downloaded audio for: {title}")
    except Exception as e:
        print(f"❌ Error downloading audio for {title}: {e}")
        return None

    # Run Whisper
    try:
        print(f"📝 Running Whisper for: {title}")
        subprocess.run(
            ["whisper", str(audio_path), "--model", WHISPER_MODEL, "--output_format", "txt", "--output_dir", str(TRANSCRIPTS_DIR)],
            check=True
        )
        txt_file = TRANSCRIPTS_DIR / f"{safe_title}.txt"
        if txt_file.exists():
            with open(txt_file, "r", encoding="utf-8") as f:
                return f.read()
    except Exception as e:
        print(f"❌ Whisper error for {title}: {e}")
    return None


if __name__ == "__main__":
    if not VIDEOS_JSON.exists():
        print("❌ videos.json not found. Run fetch_videos.py first.")
        exit(1)

    with open(VIDEOS_JSON, "r", encoding="utf-8") as f:
        videos = json.load(f)

    for vid in videos:
        title = vid["title"]
        url = vid["url"]
        video_id = url.split("v=")[-1]

        print(f"\n🎙️ Processing: {title}")

        # Try captions first
        transcript_text = transcribe_with_captions(video_id, title)

        # Fallback to Whisper if captions unavailable
        if not transcript_text:
            transcript_text = transcribe_with_whisper(url, title)

        # Save transcript if available
        if transcript_text:
            safe_title = "".join(c for c in title if c.isalnum() or c in " _-").strip()
            file_path = TRANSCRIPTS_DIR / f"{safe_title}_{video_id}.txt"
            with open(file_path, "w", encoding="utf-8") as out_f:
                out_f.write(transcript_text)
            print(f"💾 Saved transcript: {file_path}")
        else:
            print(f"⏩ Skipping {title} — no transcript generated.")

    print("\n🏁 Transcription process complete.")
