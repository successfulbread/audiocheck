"""Conservative, optional YouTube ingestion for AudioCheck.

Only accept a single standard YouTube video ID. No arbitrary URL access,
playlists, cookies, logins or bypasses. Fails clearly when retrieval is blocked.
"""
from __future__ import annotations

import json
from pathlib import Path
import re
import subprocess
import sys
from urllib.parse import parse_qs, urlsplit

ALLOWED_HOSTS = {
    "youtube.com", "www.youtube.com", "m.youtube.com",
    "music.youtube.com", "youtu.be", "www.youtu.be",
}
VIDEO_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")
MAX_YOUTUBE_SECONDS = 300
MAX_YOUTUBE_BYTES = 100 * 1024 * 1024


def canonical_youtube_url(link: str) -> str:
    """Validate YouTube host, path and video ID before making any network call."""
    link = link.strip()
    if len(link) > 2048:
        raise ValueError("Please enter a shorter YouTube video link.")
    try:
        parts = urlsplit(link)
        port = parts.port
    except ValueError as exc:
        raise ValueError("Please enter a valid YouTube video link.") from exc
    host = (parts.hostname or "").lower()
    if parts.scheme != "https" or parts.username or parts.password or port not in (None, 443):
        raise ValueError("Please enter an HTTPS YouTube video link.")
    if host not in ALLOWED_HOSTS:
        raise ValueError("Only YouTube video links are accepted in this field.")
    if host in {"youtu.be", "www.youtu.be"}:
        video_id = parts.path.strip("/")
    elif parts.path == "/watch":
        values = parse_qs(parts.query).get("v", [])
        video_id = values[0] if len(values) == 1 else ""
    else:
        match = re.fullmatch(r"/(?:shorts|live|embed)/([A-Za-z0-9_-]{11})/?", parts.path)
        video_id = match.group(1) if match else ""
    if not VIDEO_ID_RE.fullmatch(video_id):
        raise ValueError("Use a link to one YouTube video, not a playlist or channel.")
    return f"https://www.youtube.com/watch?v={video_id}"


def _run_yt_dlp(extra_args: list[str], url: str, timeout: int) -> subprocess.CompletedProcess:
    cmd = [
        sys.executable, "-m", "yt_dlp", "--ignore-config", "--no-playlist",
        "--no-warnings", "--no-progress", "--socket-timeout", "12",
        "--retries", "1", "--fragment-retries", "1", "--no-cache-dir",
        *extra_args, url,
    ]
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=False)
    except subprocess.TimeoutExpired as exc:
        raise ValueError("YouTube did not respond in time. Upload an audio file instead.") from exc
    except OSError as exc:
        raise ValueError("The YouTube audio component is unavailable on the server.") from exc


def download_youtube_audio(url: str, directory: Path) -> tuple[Path, str]:
    """Download a permitted, public video audio stream to a temporary directory.

    Calling code owns the temporary directory and must delete it after analysis.
    """
    url = canonical_youtube_url(url)
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)

    probe = _run_yt_dlp(["--dump-single-json", "--skip-download"], url, timeout=40)
    if probe.returncode != 0:
        raise ValueError(
            "YouTube could not provide this video's audio information on this server. "
            "It may be restricted or block automated retrieval. Try uploading the file instead."
        )
    try:
        info = json.loads(probe.stdout)
        duration = float(info.get("duration"))
    except (ValueError, TypeError, json.JSONDecodeError) as exc:
        raise ValueError("YouTube did not provide a usable video duration. Please upload an audio file.") from exc
    if not 4 <= duration <= MAX_YOUTUBE_SECONDS + 0.25:
        raise ValueError("YouTube videos must be between 4 seconds and 5 minutes long.")
    if info.get("is_live") or info.get("live_status") == "is_live":
        raise ValueError("Live streams are not supported.")

    result = _run_yt_dlp([
        "--format", "bestaudio[ext=m4a]/bestaudio[ext=webm]/bestaudio",
        "--max-filesize", "100M", "--output", str(directory / "youtube.%(ext)s"),
    ], url, timeout=120)
    if result.returncode != 0:
        raise ValueError(
            "YouTube audio couldn't be retrieved from Streamlit Cloud. "
            "Try uploading the file directly."
        )
    allowed = {".m4a", ".webm", ".ogg", ".mp3", ".opus", ".wav"}
    files = [p for p in directory.iterdir() if p.is_file() and p.suffix.lower() in allowed]
    if len(files) != 1:
        raise ValueError("YouTube returned no usable audio track. Please upload the audio file instead.")
    path = files[0]
    if path.stat().st_size > MAX_YOUTUBE_BYTES:
        raise ValueError("The YouTube audio track exceeds 100 MB.")
    title = str(info.get("title") or "YouTube recording")[:150]
    return path, title
