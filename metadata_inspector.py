"""Read metadata actually embedded in an audio file, without modifying it.

Separates file/container tags from on-air RDS data. Never infer tags from a
filename, acoustic fingerprint or radio-pilot detection.
"""
from __future__ import annotations

from pathlib import Path
import re

import mutagen

_MAX_TAGS = 90
_MAX_VALUE = 340
_MAX_KEY = 105
_NAME_MAP = {
    'tit2': 'Title', 'tpe1': 'Artist', 'tpe2': 'Album artist', 'talb': 'Album',
    'trck': 'Track number', 'tpos': 'Disc number', 'tdrc': 'Recording date',
    'tdor': 'Original release date', 'tyer': 'Year', 'tcon': 'Genre',
    'tcom': 'Composer', 'tsse': 'Encoder settings', 'tenc': 'Encoded by',
    'tden': 'Encoding date', 'tdtg': 'Tagging date', 'wxxx': 'Website',
    '\xa9nam': 'Title', '\xa9art': 'Artist', '\xa9alb': 'Album',
    'aart': 'Album artist', '\xa9day': 'Date', '\xa9gen': 'Genre',
    '\xa9too': 'Encoder/software', 'trkn': 'Track number', 'disk': 'Disc number',
    'description': 'Description', 'comment': 'Comment',
}
_RDS_KEY = re.compile(r'(?:rds|radio.?text|rt\+|rt_plus|radio_text|ps_name|pi_code|program(?:me)?_service)', re.I)
_SKIP = re.compile(r'(?:artwork|coverart|picture|metadata_block_picture|covr|^apic|^geob|^priv)', re.I)


def _clean(value, maximum=_MAX_VALUE):
    text = str(value).replace('\x00', ' ').replace('\r', ' ').replace('\n', ' ').strip()
    text = ''.join(ch if ch.isprintable() else ' ' for ch in text)
    text = re.sub(r'\s+', ' ', text)
    if len(text) > maximum:
        return text[:maximum] + '… [truncated]'
    return text


def _values(data):
    """Small human-readable tag values only. Never dump binary artwork."""
    if data is None:
        return []
    if isinstance(data, bytes):
        # Most bytes tags are opaque atoms/artwork, not trustworthy text.
        return []
    if hasattr(data, 'text'):
        return _values(getattr(data, 'text'))
    if isinstance(data, (tuple, list)):
        values = []
        for item in data[:12]:
            values.extend(_values(item))
        return values
    if isinstance(data, (int, float, str)):
        value = _clean(data)
        return [value] if value else []
    if hasattr(data, 'url') and isinstance(data.url, str):
        return [_clean(data.url)]
    return []


def _normalized_key(key):
    original = _clean(key, _MAX_KEY)
    short = original.split(':', 1)[0].lower()
    if original.lower().startswith('----:com.apple.itunes:'):
        return original.split(':', 2)[-1].replace('_', ' ')
    if short == 'txxx':
        return original.split(':', 1)[-1]
    if short == 'comm':
        return 'Comment' if ':' not in original else 'Comment: ' + original.split(':', 1)[-1]
    return _NAME_MAP.get(short, original.replace('_', ' '))


def inspect_metadata(path, probe):
    path = Path(path)
    collected = []
    seen = set()
    sources = set()
    artwork = 0
    overflow = False

    def add(key, value, source):
        nonlocal overflow
        field = _normalized_key(key)
        if not field or _SKIP.search(field) or _SKIP.search(str(key)):
            return
        if isinstance(value, (bytes, bytearray)) and str(key).startswith('----:'):
            # MP4 freeform atoms are normally UTF-8, but only decode text;
            # leave opaque/binary custom tags out of a human-readable report.
            try:
                decoded = bytes(value).decode('utf-8')
                vals = [_clean(decoded)] if decoded.isprintable() else []
            except UnicodeError:
                vals = []
        elif isinstance(value, list) and str(key).startswith('----:'):
            vals = []
            for part in value[:10]:
                if isinstance(part, bytes):
                    try:
                        decoded = part.decode('utf-8')
                        if decoded.isprintable():
                            vals.append(_clean(decoded))
                    except UnicodeError:
                        pass
                else:
                    vals.extend(_values(part))
        else:
            vals = _values(value)
        for item in vals:
            identity = (field.lower().strip(), item.casefold())
            if identity in seen:
                continue
            if len(collected) >= _MAX_TAGS:
                overflow = True
                continue
            seen.add(identity)
            sources.add(source)
            collected.append({'field': field, 'value': item, 'source': source})

    for stream_type, record in [('Container / FFprobe', probe.get('format_tags')),
                                ('Audio stream / FFprobe', probe.get('stream_tags'))]:
        for key, val in (record or {}).items():
            add(str(key), val, stream_type)

    parser = 'Mutagen format unknown'
    try:
        try:
            audio = mutagen.File(str(path), easy=False)
        except Exception:
            audio = None
        if audio is None and path.suffix.lower() in ('.mp3', '.mpga', '.mpeg'):
            # A recoverable ID3 block may exist even if no MP3 frames survive.
            from mutagen.id3 import ID3
            audio = ID3(str(path))
        if audio is not None:
            parser = type(audio).__name__
            tags = getattr(audio, 'tags', None)
            if tags is None and parser == 'ID3':
                tags = audio
            if tags is not None:
                for key, frame in tags.items():
                    if _SKIP.search(str(key)):
                        artwork += 1
                        continue
                    # ID3 TXXX has a separate descriptor; COMM/USLT include text.
                    kind = str(getattr(frame, 'FrameID', '')).upper()
                    if kind in ('UFID', 'POPM'):
                        owner = _clean(getattr(frame, 'owner', getattr(frame, 'email', '')), 100)
                        if kind == 'UFID':
                            identifier = getattr(frame, 'data', b'')
                            if isinstance(identifier, bytes):
                                try:
                                    identifier_text = identifier.decode('utf-8')
                                    if not identifier_text.isprintable():
                                        identifier_text = identifier[:64].hex()
                                except UnicodeError:
                                    identifier_text = identifier[:64].hex()
                                add(f'UFID: {owner}', identifier_text, 'Mutagen / ' + parser)
                        else:
                            rating = getattr(frame, 'rating', None)
                            count = getattr(frame, 'count', None)
                            add(f'POPM: {owner}', f'Rating {rating}, count {count}', 'Mutagen / ' + parser)
                        continue
                    label = str(key)
                    if kind in ('TXXX', 'COMM', 'USLT', 'WXXX'):
                        description = _clean(getattr(frame, 'desc', ''), 80)
                        if description:
                            label = f'{kind}:{description}'
                    add(label, frame, 'Mutagen / ' + parser)
            pictures = getattr(audio, 'pictures', None)
            if pictures:
                artwork += len(pictures)
    except Exception:
        parser = 'Mutagen unreadable'
    rds_tags = [entry for entry in collected if _RDS_KEY.search(entry['field'])]
    title = next((r['value'] for r in collected if r['field'].lower() in ('title', 'song title')), None)
    artist = next((r['value'] for r in collected if r['field'].lower() in ('artist', 'performer')), None)
    names = ', '.join(f"{r['field']}: {r['value'][:60]}" for r in collected[:4])
    if collected:
        conclusion = f'{len(collected)} embedded text field(s)' + (' (display limit)' if overflow else '')
        explanation = (f'Read {len(collected)} distinct tag fields from {len(sources)} parser/source group(s). '
                       f'{names}. Values are taken from the digital file; they can be edited and do not prove identity, '
                       'broadcast origin or recording date.' +
                       (' Display capped at 90 fields; additional tags were omitted.' if overflow else ''))
    else:
        conclusion = 'No embedded text tags'
        explanation = ('No readable textual tags were found in the container, audio stream or Mutagen parser. '
                       'Track and artist cannot be recovered from a blank tag field. ')
    return {
        'result': conclusion, 'certainty': 'High' if collected else 'Not detected',
        'detail': explanation, 'tags': collected, 'rds_tags': rds_tags,
        'parser': parser, 'artwork_items': artwork, 'truncated': overflow, 'title': title, 'artist': artist,
        'metrics': {'embedded_fields': len(collected), 'tag_sources': len(sources),
                    'rds_tag_fields': len(rds_tags), 'artwork_items': artwork},
    }
