"""Safely retrieve an explicitly permitted direct audio file from archive.org.

An audio file URL, not an Archive item webpage. Hosts and redirects are limited
 to archive.org. Restricting this source avoids an arbitrary-URL SSRF endpoint.
"""
from __future__ import annotations

from pathlib import Path
import re
import time
from urllib.parse import urlsplit, unquote
from urllib.request import Request, HTTPRedirectHandler, build_opener
from urllib.error import HTTPError, URLError

MAX_BYTES = 100 * 1024 * 1024
ALLOWED_EXT = {'.mp3', '.mpeg', '.mpga', '.wav', '.flac', '.ogg', '.m4a', '.opus'}


def _archive_host(host):
    return bool(host and (host == 'archive.org' or host.endswith('.archive.org')))


def _verify_url(link: str, require_download=True):
    link = str(link).strip()
    if not link or len(link) > 2048:
        raise ValueError('Paste a direct Internet Archive MP3 or audio link.')
    try:
        u = urlsplit(link)
        port = u.port
    except ValueError as exc:
        raise ValueError('Invalid Internet Archive audio URL.') from exc
    if (u.scheme != 'https' or not _archive_host(u.hostname) or
            u.username or u.password or port not in (None, 443)):
        raise ValueError('Only HTTPS audio links from archive.org are supported.')
    if require_download:
        if not u.path.startswith('/download/'):
            raise ValueError('Use the direct MP3 download link, not the archive item page.')
        ext = Path(unquote(u.path)).suffix.lower()
        if ext not in ALLOWED_EXT:
            raise ValueError('The link must point directly to an MP3, WAV, FLAC or other audio file.')
    return u


class _SafeRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        _verify_url(newurl, require_download=False)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def fetch_archive_audio(url: str, directory: Path):
    u = _verify_url(url)
    name = Path(unquote(u.path)).name
    name = re.sub(r'[^\w.()\- ]+', '_', name, flags=re.UNICODE)[:140]
    if not name or Path(name).suffix.lower() not in ALLOWED_EXT:
        raise ValueError('No recognizable audio filename in that link.')
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    destination = directory / name
    request = Request(url, headers={'User-Agent': 'AudioCheck/1.3 (audio research app)'})
    opener = build_opener(_SafeRedirect)
    try:
        with opener.open(request, timeout=20) as response:
            _verify_url(response.url, require_download=False)
            length = response.headers.get('Content-Length')
            if length and int(length) > MAX_BYTES:
                raise ValueError('This audio file is over 100 MB. Please use a smaller file.')
            total = 0
            started = time.monotonic()
            with destination.open('wb') as out:
                while True:
                    if time.monotonic() - started > 75:
                        raise ValueError('Archive audio retrieval timed out. Try uploading the file.')
                    chunk = response.read(128 * 1024)
                    if not chunk:
                        break
                    total += len(chunk)
                    if total > MAX_BYTES:
                        raise ValueError('This audio file is over 100 MB.')
                    out.write(chunk)
            if total < 256:
                raise ValueError('The archive link returned no usable audio.')
    except (HTTPError, URLError, TimeoutError, OSError) as exc:
        raise ValueError('The Internet Archive file could not be fetched. Check the direct download link.') from exc
    return destination, name
