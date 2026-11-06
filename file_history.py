"""Inspect *digital-file* history clues without mistaking song dates for encode dates.

A tag can be wrong, and the uploaded file's filesystem mtime is never evidence:
Streamlit writes the upload to a fresh temporary file.
"""
from __future__ import annotations

import re
from pathlib import Path

from mutagen.mp3 import MP3


# Earliest documented release years. 3.99 without patch is deliberately broad.
# https://github.com/enzo1982/lame/releases and SourceForge's LAME releases.
LAME_EARLIEST_YEAR = {
    (3, 96): 2004, (3, 97): 2006, (3, 98): 2008,
    (3, 99): 2011, (3, 100): 2017, (3, 101): 2026,
    (4, 0): 2026,
}


def _tag(tags, *keys):
    lower = {str(k).lower(): str(v).strip() for k, v in (tags or {}).items() if v is not None}
    for key in keys:
        value = lower.get(key.lower(), "")
        if value:
            return value[:240]
    return ""


def _year(text):
    hit = re.search(r"(?<!\d)(19\d{2}|20\d{2})(?!\d)", text or "")
    return int(hit.group(1)) if hit else None


def _lame_version(encoder):
    hit = re.search(r"LAME(?:.{0,36}?\bversion\s+|\s*)(\d)\.(\d{2,3})(?:\.(\d+))?", encoder, re.I)
    return tuple(map(int, hit.groups(default="0"))) if hit else None


def inspect_file(path: Path, probe_data: dict):
    """Return one beginner-friendly verdict and a few trustworthy file facts.

    Tracks when THIS digital encode could have been made, not original music age.
    """
    stream_tags = probe_data.get('stream_tags') or {}
    format_tags = probe_data.get('format_tags') or {}
    codec = str(probe_data.get('codec', 'unknown')).lower()
    bitrate = probe_data.get('bit_rate')
    details = {
        'codec': codec,
        'bitrate_kbps': round(int(bitrate) / 1000) if bitrate else None,
        'bitrate_mode': None,
        'encoder': None,
        'encoding_date': None,
        'tagged_year': None,
        'earliest_encoder_year': None,
    }
    # FFprobe knows about common container creation/encoding date tags.
    encoded_date = _tag(stream_tags, 'encoding_time', 'encoded_date', 'date_encoded', 'creation_time') or _tag(
        format_tags, 'encoding_time', 'encoded_date', 'date_encoded', 'creation_time')
    encoder = _tag(stream_tags, 'encoder', 'encoded_by', 'encoding_tool') or _tag(
        format_tags, 'encoder', 'encoded_by', 'encoding_tool')
    song_date = _tag(stream_tags, 'date', 'year', 'originaldate') or _tag(format_tags, 'date', 'year', 'originaldate')

    if codec == 'mp3':
        try:
            audio = MP3(path)
            details['bitrate_mode'] = str(audio.info.bitrate_mode).rsplit('.', 1)[-1].upper()
            tags = audio.tags
            if tags is not None:
                tenc = tags.get('TDEN')  # Encoded date is NOT TDRC (recorded) or TDRL (release).
                if tenc:
                    encoded_date = str(tenc)
                tsse = tags.get('TSSE')  # Software/hardware and settings used for encoding.
                if tsse and re.search(r'\bLAME\b', str(tsse), re.I):
                    encoder = str(tsse)
                elif tsse and not encoder:
                    encoder = str(tsse)
                if not encoder and tags.get('TENC'):
                    encoder = str(tags.get('TENC'))
                if not song_date:
                    for field in ('TDRC', 'TDRL', 'TYER'):
                        if tags.get(field):
                            song_date = str(tags.get(field))
                            break
            if audio.info.encoder_info and (not encoder or (
                    _lame_version(str(audio.info.encoder_info)) and not _lame_version(encoder))):
                encoder = str(audio.info.encoder_info)
        except Exception:
            pass  # Do not let optional forensic tags block the audio analysis.

    details['encoder'] = encoder[:120] if encoder else None
    details['encoding_date'] = encoded_date[:100] if encoded_date else None
    details['tagged_year'] = _year(song_date)
    version = _lame_version(encoder)
    earliest = LAME_EARLIEST_YEAR.get(version[:2]) if version else None
    # LAME 3.99.5 is 2012, whereas 3.99.0 is 2011.
    if version and version[:2] == (3, 99) and version[2] >= 5:
        earliest = 2012
    details['earliest_encoder_year'] = earliest

    # Allow a real explicit date, but always explain its unverified nature.
    declared_year = _year(encoded_date)
    evidence = []
    if declared_year:
        evidence.append(f'The file contains an encoding/creation date tag: {encoded_date[:40]}.')
    if encoder:
        evidence.append(f'Software/encoder tag: {encoder[:80]}.')
    if earliest:
        evidence.append(f'That encoder version appeared around {earliest}.')
    if details['bitrate_kbps']:
        mode = f" {details['bitrate_mode']}" if details['bitrate_mode'] else ''
        evidence.append(f"{codec.upper()} at about {details['bitrate_kbps']} kbps{mode}.")
    if details['tagged_year']:
        evidence.append(f"A {details['tagged_year']} music/date tag does not date the digital encoding.")
    if not evidence:
        evidence.append(f"This is a {codec.upper()} file, but it has no useful creation-date or encoder tag.")
    evidence.append('Tags can be edited; the original recording may be much older.')

    if declared_year and earliest and declared_year < earliest:
        result, certainty = 'Date tags conflict', 'Tentative'
        evidence.insert(0, 'The stated file date is earlier than the tagged encoder version.')
    elif declared_year:
        result, certainty = f'Date tag: {declared_year}', 'Possible'
    elif earliest:
        result, certainty = f'Encoded {earliest} or later', 'Possible'
    elif encoder:
        if encoder.lower().startswith('lavf'):
            result, certainty = 'Software: FFmpeg', 'Tentative'
        else:
            short = 'LAME' if 'lame' in encoder.lower() else encoder[:28]
            result, certainty = f'Encoder: {short}', 'Tentative'
    else:
        result, certainty = 'Creation date unknown', 'Not measurable'
    return {'result': result, 'certainty': certainty,
            'detail': ' '.join(evidence), 'facts': details}
