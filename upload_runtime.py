"""Bounded, process-wide analysis lifecycle for Streamlit sessions."""
from contextlib import contextmanager
import gc
import logging
from pathlib import Path
import shutil
import threading

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


def save_upload(uploaded, directory, max_bytes):
    """Copy in bounded chunks rather than creating another full bytes object."""
    if uploaded.size > max_bytes:
        raise ValueError('File too large (100 MB max).')
    path = Path(directory) / ('upload' + Path(uploaded.name).suffix.lower())
    uploaded.seek(0)
    with path.open('wb') as output:
        shutil.copyfileobj(uploaded, output, length=1024*1024)
    if path.stat().st_size != uploaded.size:
        raise ValueError('The upload was incomplete. Please select the file again.')
    return path


def release_upload(uploaded):
    if uploaded is not None:
        uploaded.close()
