"""Date clues for the current DIGITAL encoding, not the underlying music.

ID3 TDEN = encoding date; TDTG = tagging date; TDRC/TDRL = music date.
Versions are earliest published software-family dates, never proof of file age.
References: https://id3.org/id3v2.4.0-frames
https://github.com/enzo1982/lame/releases
https://github.com/FFmpeg/FFmpeg/blob/master/doc/APIchanges
"""
from __future__ import annotations

import re
from pathlib import Path
from mutagen.mp3 import MP3

# Broad earliest known dates, conservatively rounded to the year. FFmpeg's
# APIchanges and LAME's upstream release history support these lower bounds.
LAME_EARLIEST_YEAR = {(3, 96): 2004, (3, 97): 2006,
                      (3, 98): 2008, (3, 99): 2011, (3, 100): 2017,
                      (3, 101): 2026}
LAME_RELEASES = {(3, 99, 3): '2011-11-26', (3, 99, 4): '2012-01-25',
                 (3, 99, 5): '2012-02-28', (3, 100, 0): '2017-10-13'}
LIBAVCODEC_EARLIEST_YEAR = {57: 2015, 58: 2017, 59: 2021,
                            60: 2023, 61: 2024, 62: 2025}


def _tag(tags, *keys):
    lower = {str(k).lower(): str(v).strip() for k, v in (tags or {}).items() if v is not None}
    for key in keys:
        value = lower.get(key.lower(), '')
        if value:
            return value[:240]
    return ''


def _year(text):
    hit = re.search(r'(?<!\d)(19\d{2}|20\d{2})(?!\d)', str(text or ''))
    return int(hit.group(1)) if hit else None


def _lame_version(encoder):
    hit = re.search(r'LAME(?:.{0,36}?\bversion\s+|\s*)(\d)\.(\d{2,3})(?:\.(\d+))?', str(encoder), re.I)
    return tuple(map(int, hit.groups(default='0'))) if hit else None


def _libav_kind_version(encoder):
    hit = re.search(r'\b(Lavc|libavcodec|Lavf|libavformat)[\s/]*(\d{2})(?:\.\d+)?', str(encoder or ''), re.I)
    return (hit.group(1).lower(), int(hit.group(2))) if hit else None


def _lavc_earliest_year(encoder):
    found = _libav_kind_version(encoder)
    if found and found[0] in ('lavc', 'libavcodec'):
        return LIBAVCODEC_EARLIEST_YEAR.get(found[1])
    return None


def _earliest_version(encoder):
    lame = _lame_version(encoder)
    if lame:
        exact = LAME_RELEASES.get(lame)
        year = int(exact[:4]) if exact else LAME_EARLIEST_YEAR.get(lame[:2])
        return year, exact, 'audio encoder'
    lav = _libav_kind_version(encoder)
    if lav:
        year = LIBAVCODEC_EARLIEST_YEAR.get(lav[1])
        return year, None, ('container writer' if lav[0] in ('lavf', 'libavformat') else 'audio encoder')
    return None, None, None


def _id3_extra_date(tags):
    """Only accept named user tags that explicitly say creation or encoding."""
    if tags is None:
        return ''
    for t in tags.getall('TXXX'):
        descriptor = str(getattr(t, 'desc', '')).lower().replace(' ', '_')
        if descriptor in ('encoding_date', 'date_encoded', 'encoded_date',
                          'creation_time', 'creation_date', 'encoded_on'):
            values = getattr(t, 'text', [])
            value = str(values[0]).strip() if values else ''
            if _year(value):
                return value[:100]
    return ''


def inspect_file(path: Path, probe_data: dict):
    """Return beginner-friendly date verdict and its evidence."""
    stream_tags = probe_data.get('stream_tags') or {}
    format_tags = probe_data.get('format_tags') or {}
    codec = str(probe_data.get('codec', 'unknown')).lower()
    bitrate = probe_data.get('bit_rate')
    facts = dict(codec=codec, bitrate_kbps=round(int(bitrate) / 1000) if bitrate else None,
                 bitrate_mode=None, encoder=None, encoding_date=None,
                 tagging_date=None, tagged_year=None, earliest_encoder_year=None,
                 earliest_encoder_date=None, dating_basis=None)

    encoded_date = (_tag(stream_tags, 'encoding_time', 'encoded_date', 'date_encoded', 'creation_time', 'date_created')
                    or _tag(format_tags, 'encoding_time', 'encoded_date', 'date_encoded', 'creation_time', 'date_created'))
    tagged_date = _tag(stream_tags, 'tagging_time', 'date_tagged') or _tag(format_tags, 'tagging_time', 'date_tagged')
    stream_encoder = _tag(stream_tags, 'encoder', 'encoded_by', 'encoding_tool')
    container_encoder = _tag(format_tags, 'encoder', 'encoded_by', 'encoding_tool')
    encoder = stream_encoder or container_encoder
    song_date = (_tag(stream_tags, 'date', 'year', 'originaldate')
                 or _tag(format_tags, 'date', 'year', 'originaldate'))

    if codec == 'mp3':
        try:
            audio = MP3(path)
            if getattr(audio.info, 'bitrate_mode', None) is not None:
                facts['bitrate_mode'] = str(audio.info.bitrate_mode).rsplit('.', 1)[-1].upper()
            tags = audio.tags
            if tags is not None:
                tden = tags.get('TDEN')
                if tden:
                    encoded_date = str(tden)
                elif not encoded_date:
                    encoded_date = _id3_extra_date(tags)
                tdtg = tags.get('TDTG')
                if tdtg:
                    tagged_date = str(tdtg)
                tsse = tags.get('TSSE')
                if tsse:
                    tag_text = str(tsse)
                    tag_version = _libav_kind_version(tag_text)
                    active_version = _libav_kind_version(encoder)
                    # Prefer LAME's precise patch tag and an actual audio encoder.
                    # A Lavf tag identifies the container writer, not the encoder.
                    if _lame_version(tag_text):
                        encoder = tag_text
                    elif tag_version and tag_version[0] in ('lavc', 'libavcodec') and (
                            not active_version or active_version[0] in ('lavf', 'libavformat')):
                        encoder = tag_text
                    elif not encoder:
                        encoder = tag_text
                if not encoder and tags.get('TENC'):
                    encoder = str(tags.get('TENC'))
                if not song_date:
                    for key in ('TDRC', 'TDRL', 'TYER'):
                        if tags.get(key):
                            song_date = str(tags.get(key))
                            break
            audio_info = str(getattr(audio.info, 'encoder_info', '') or '')
            # Prefer version-specific MP3 headers over generic software tags.
            if audio_info and not (_lame_version(encoder) or _libav_kind_version(encoder)):
                if _lame_version(audio_info) or _libav_kind_version(audio_info):
                    encoder = audio_info
        except Exception:
            pass

    # Encoder version takes priority over container muxer version. The latter
    # could be from a later remux, so it cannot establish actual encoding age.
    if encoder and _libav_kind_version(encoder) is None and not _lame_version(encoder):
        if _lame_version(container_encoder) or _libav_kind_version(container_encoder):
            encoder = container_encoder
    if not encoder:
        encoder = container_encoder
    earliest, exact_release, kind = _earliest_version(encoder)
    if not earliest and stream_encoder and stream_encoder != encoder:
        alternate = _earliest_version(stream_encoder)
        if alternate[0]:
            earliest, exact_release, kind = alternate
            encoder = stream_encoder

    facts.update(encoder=encoder[:120] if encoder else None,
                 encoding_date=encoded_date[:100] if encoded_date else None,
                 tagging_date=tagged_date[:100] if tagged_date else None,
                 tagged_year=_year(song_date), earliest_encoder_year=earliest,
                 earliest_encoder_date=exact_release, dating_basis=kind)
    explicit_year = _year(encoded_date)
    tagged_year = _year(tagged_date)
    evidence = []
    if explicit_year:
        evidence.append(f'File date tag says {encoded_date[:40]}; tags can be changed.')
    if encoder:
        evidence.append(f'Encoder/software: {encoder[:85]}.')
    if earliest:
        when = exact_release if exact_release else str(earliest)
        if kind == 'container writer':
            evidence.append(f'This container software existed by {when}; it may have repackaged older audio.')
        else:
            evidence.append(f'That encoder version was available from {when}.')
    if tagged_year:
        evidence.append(f'File tag was edited in {tagged_year}; this is not the encoding date.')
    if facts['tagged_year']:
        evidence.append(f'The {facts["tagged_year"]} music/date tag describes the song, not when this digital file was made.')
    if facts['bitrate_kbps']:
        mode = f' {facts["bitrate_mode"]}' if facts['bitrate_mode'] else ''
        evidence.append(f'{codec.upper()}, about {facts["bitrate_kbps"]} kbps{mode}.')

    if explicit_year and earliest and explicit_year < earliest and kind == 'audio encoder':
        result, certainty = 'Date tags conflict', 'Tentative'
        evidence.insert(0, 'The claimed encode date is earlier than this audio-encoder version.')
    elif explicit_year and earliest and explicit_year < earliest and kind == 'container writer':
        # An old encoding can be repackaged into a newer file without
        # re-encoding. Both metadata clues can be legitimate.
        result, certainty = f'Processed {earliest} or later', 'Possible'
        evidence.insert(0, 'Older audio may have been repackaged using newer software.')
    elif explicit_year:
        result, certainty = f'Date tag: {encoded_date[:10]}', 'Possible'
    elif earliest:
        result, certainty = (f'Processed {earliest} or later' if kind == 'container writer'
                             else f'Encoded {earliest} or later'), 'Possible'
    elif tagged_year:
        result, certainty = f'Tagged in {tagged_year}', 'Tentative'
    elif encoder:
        result, certainty = ('Encoder identified', 'Tentative')
    else:
        result, certainty = 'Creation date unknown', 'Not measurable'
    if not evidence:
        evidence.append('No dated encoder or useful file-date tag was found.')
    evidence.append('This dates the digital file or processing, not the original music.')
    return {'result': result, 'certainty': certainty, 'detail': ' '.join(evidence),
            'facts': facts}
