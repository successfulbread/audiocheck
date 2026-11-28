"""Bounded, process-wide analysis lifecycle for Streamlit sessions."""
from contextlib import contextmanager
import gc
import logging
from pathlib import Path
import shutil
import threading

ALLOWED_SUFFIXES = {".mp3", ".wav", ".flac", ".ogg", ".m4a", ".webm", ".opus", ".mpeg", ".mpga"}
DISALLOWED_MIME_PREFIXES = ("text/", "image/", "video/", "application/zip", "application/x-zip",
                            "application/x-dosexec", "application/x-msdownload")

_LOCK = threading.Lock()
LOGGER = logging.getLogger('audiocheq.runtime')

class AnalysisBusy(RuntimeError):
    pass


def log_memory(stage):
    # Linux current resident memory, not peak RSS. Optional diagnostic only.
    try:
        with open('/proc/self/status', encoding='ascii') as status:
            rss = next(line.strip() for line in status if line.startswith('VmRSS:'))
        LOGGER.warning('AudioCheQ %s | %s', stage, rss)
    except (OSError, StopIteration):
        LOGGER.warning('AudioCheQ %s', stage)


@contextmanager
def analysis_slot():
    if not _LOCK.acquire(blocking=False):
        raise AnalysisBusy('Another recording is being analyzed. Please try Analyze again shortly.')
    try:
        gc.collect()
        log_memory('analysis start')
        yield
    finally:
        try:
            gc.collect()
            log_memory('analysis end')
        finally:
            _LOCK.release()


def _looks_like_audio(path):
    suffix = path.suffix.lower()
    header = path.read_bytes()[:32]
    if suffix == '.wav':
        return header.startswith(b'RIFF') and header[8:12] == b'WAVE'
    if suffix == '.flac':
        return header.startswith(b'fLaC')
    if suffix in ('.ogg', '.opus'):
        return header.startswith(b'OggS')
    if suffix in ('.m4a',):
        return len(header) >= 12 and header[4:8] == b'ftyp'
    if suffix in ('.webm',):
        return header.startswith(bytes([0x1A, 0x45, 0xDF, 0xA3]))
    if suffix in ('.mp3', '.mpeg', '.mpga'):
        return header.startswith(b'ID3') or (len(header) >= 2 and header[0] == 0xFF and (header[1] & 0xE0) == 0xE0)
    return False


def save_upload(uploaded, directory, max_bytes):
    """Copy in bounded chunks rather than creating another full bytes object."""
    if uploaded.size > max_bytes:
        raise ValueError('File too large (100 MB max).')
    suffix = Path(uploaded.name or '').suffix.lower()
    if suffix not in ALLOWED_SUFFIXES:
        raise ValueError('Unsupported file type. Please upload MP3, WAV, FLAC, OGG, OPUS, M4A or WebM audio.')
    mime = str(getattr(uploaded, 'type', '') or '').lower()
    if mime and any(mime.startswith(prefix) for prefix in DISALLOWED_MIME_PREFIXES):
        raise ValueError('That file does not appear to be an audio upload.')
    path = Path(directory) / ('upload' + suffix)
    uploaded.seek(0)
    with path.open('wb') as output:
        shutil.copyfileobj(uploaded, output, length=1024*1024)
    if path.stat().st_size != uploaded.size:
        raise ValueError('The upload was incomplete. Please select the file again.')
    if suffix not in {'.mp3', '.mpeg', '.mpga'} and not _looks_like_audio(path):
        try:
            path.unlink(missing_ok=True)
        finally:
            raise ValueError('The uploaded file does not look like a valid audio file of the selected type.')
    return path


def release_upload(uploaded):
    if uploaded is not None:
        uploaded.close()
