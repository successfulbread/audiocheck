"""Conservative, optional YouTube ingestion for AudioCheck.

Only accept a single standard YouTube video ID. No arbitrary URL access,
playlists, cookies, logins or bypasses. Fails clearly when retrieval is blocked.
"""
from __future__ import annotations

import json
from pathlib import Path
import re
import shutil
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


def _runtime_args() -> list[str]:
    """Enable a proper JS runtime for modern yt-dlp YouTube extraction.

    The PyPI `deno` wheel contains a platform-specific Deno executable. This
    avoids relying on the old distro nodejs in Streamlit Cloud.
    """
    candidate = None
    try:
        import deno
        candidate = deno.find_deno_bin()
    except (ImportError, AttributeError, OSError):
        pass
    candidate = candidate or shutil.which("deno")
    if candidate and Path(candidate).is_file():
        return ["--js-runtimes", f"deno:{candidate}"]
    # Node >=22 is supported, but apt versions may be too old.
    node = shutil.which("node")
    if node:
        try:
            version = subprocess.run([node, "--version"], capture_output=True, text=True,
                                     timeout=3, check=False).stdout.strip().lstrip("v")
            if int(version.split(".")[0]) >= 22:
                return ["--js-runtimes", f"node:{node}"]
        except (ValueError, IndexError, OSError, subprocess.TimeoutExpired):
            pass
    return []


def _failure_message(result: subprocess.CompletedProcess) -> str:
    """Explain the failure category, without exposing URLs, tokens or raw logs."""
    message = str(result.stderr or "").lower()
    if "sign in to confirm" in message or "not a bot" in message:
        return ("YouTube requires a human verification for this cloud server. "
                "AudioCheck cannot complete that request; upload the audio file instead.")
    if "403" in message or "forbidden" in message:
        return ("YouTube refused the audio request (HTTP 403) from Streamlit Cloud. "
                "This may be a server-IP restriction; upload the audio file instead.")
    if "js runtime" in message or "javascript runtime" in message or "ejs" in message:
        return ("YouTube's JavaScript verification could not run on this server. "
                "Check that the deno and yt-dlp dependencies deployed successfully.")
    if "private video" in message or "unavailable" in message:
        return "The YouTube video or its audio format is unavailable for this request."
    return ("YouTube audio retrieval was unsuccessful from Streamlit Cloud. "
            "Please upload the audio file directly if permitted.")


def _run_yt_dlp(extra_args: list[str], url: str, timeout: int) -> subprocess.CompletedProcess:
    cmd = [
        sys.executable, "-m", "yt_dlp", "--ignore-config", "--no-playlist",
        "--no-warnings", "--no-progress", "--socket-timeout", "12",
        "--retries", "1", "--fragment-retries", "1", "--no-cache-dir",
        *_runtime_args(), *extra_args, url,
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
        raise ValueError(_failure_message(probe))
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
        raise ValueError(_failure_message(result))
    allowed = {".m4a", ".webm", ".ogg", ".mp3", ".opus", ".wav"}
    files = [p for p in directory.iterdir() if p.is_file() and p.suffix.lower() in allowed]
    if len(files) != 1:
        raise ValueError("YouTube returned no usable audio track. Please upload the audio file instead.")
    path = files[0]
    if path.stat().st_size > MAX_YOUTUBE_BYTES:
        raise ValueError("The YouTube audio track exceeds 100 MB.")
    title = str(info.get("title") or "YouTube recording")[:150]
    return path, title
