"""Conservative RDS inspection of audio files.

RDS rides a 57 kHz baseband FM multiplex (MPX) subcarrier, not the 19 kHz
stereo pilot. An ordinary stereo/mono audio output lacks the multiplex.
When eligible raw MPX WAV/FLAC is supplied, optionally invoke redsea if that
separate command-line program is installed. A spectral feature is *never*
reported as decoded RDS text.
"""
from __future__ import annotations

from collections import Counter
import json
import math
from pathlib import Path
import re
import subprocess
import tempfile

import numpy as np
from scipy import signal

from redsea_bootstrap import resolve_redsea


def _decode_raw_mpx_window(path, rate, duration=12):
    # Analyze a bounded part of the raw file at original sample rate.
    p = subprocess.run([
        'ffmpeg', '-nostdin', '-v', 'error', '-i', str(path),
        '-t', str(duration), '-map', '0:a:0', '-vn', '-ac', '1',
        '-ar', str(rate), '-f', 'f32le', '-acodec', 'pcm_f32le', 'pipe:1',
    ], capture_output=True, timeout=24, check=True)
    return np.frombuffer(p.stdout, dtype='<f4')


def _spectral_check(path, fs):
    """Return measured 19k and broad 57k RDS-band evidence, not an RDS decode."""
    rate = min(int(fs), 192000)
    audio = _decode_raw_mpx_window(path, rate)
    if len(audio) < rate * 4:
        return None
    audio = audio[:min(len(audio), rate * 12)].astype(np.float64)
    if np.sqrt(float(np.mean(audio ** 2))) < 1e-7:
        return None
    f, p = signal.welch(audio, fs=rate, nperseg=min(len(audio), rate * 2), noverlap=rate,
                        scaling='density', average='median')
    eps = 1e-25
    def band_power(a, b):
        return float(np.mean(p[(f >= a) & (f <= b)]))
    # RDS is BPSK with a suppressed carrier: an energy band, not necessarily
    # a line precisely at 57000 Hz.
    rds = band_power(55500, 58500)
    neighbours = (band_power(51000, 53500) + band_power(60500, 63000)) / 2
    rds_contrast = float(10 * np.log10((rds + eps) / (neighbours + eps)))
    near = (f >= 18999.5) & (f <= 19000.5)
    local = ((f >= 18950) & (f <= 18980)) | ((f >= 19020) & (f <= 19050))
    pil = float(np.max(p[near])) if np.any(near) else 0.0
    pilot_floor = float(np.median(p[local])) if np.any(local) else 0.0
    pilot_db = float(10 * np.log10((pil + eps) / (pilot_floor + eps)))
    # Only a candidate for investigation, never decoding proof.
    # Some mono FM multiplex transmissions carry RDS without a stereo pilot.
    # A significantly isolated 57k band may still warrant *trying* a real
    # decoder; no label is trusted without valid RDS groups.
    candidate = bool((rds_contrast >= 3.0 and pilot_db >= 12.0) or rds_contrast >= 8.0)
    return {'pilot_prominence_db': round(pilot_db, 2),
            'rds_band_contrast_db': round(rds_contrast, 2),
            'sampled_seconds': round(len(audio) / rate, 1),
            'raw_mpx_candidate': candidate}


def _redsea_decode(path):
    """Decode a brief excerpt, installing the optional decoder on demand.

    Only accept repeated, consistent programme-identification (PI) groups.
    """
    command, setup_status = resolve_redsea()
    if not command:
        return {'decoder_available': False, 'groups': 0, 'data': {},
                'setup_status': setup_status}
    with tempfile.TemporaryDirectory(prefix='audiocheq_rds_') as tmp:
        clip = Path(tmp) / 'multiplex.wav'
        subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-i', str(path),
                        '-t', '25', '-map', '0:a:0', '-ac', '1', '-ar', '171000',
                        '-acodec', 'pcm_s16le', '-y', str(clip)],
                       capture_output=True, timeout=30, check=True)
        p = subprocess.run([command, '--file', str(clip)], capture_output=True,
                           timeout=35, check=False, text=True)
    groups = []
    for line in p.stdout.splitlines()[:1200]:
        try:
            entry = json.loads(line)
        except (ValueError, TypeError):
            continue
        if isinstance(entry, dict) and re.fullmatch(r'0x[0-9a-fA-F]{4}', str(entry.get('pi', ''))):
            groups.append(entry)
    repeated = Counter(x['pi'] for x in groups)
    valid_pi, n = repeated.most_common(1)[0] if repeated else (None, 0)
    if n < 2:
        return {'decoder_available': True, 'groups': len(groups), 'data': {}}
    trusted = [x for x in groups if x.get('pi') == valid_pi]
    def most_common_value(key):
        values = [str(x[key]).strip()[:250] for x in trusted if isinstance(x.get(key), str) and x[key].strip()]
        return Counter(values).most_common(1)[0][0] if values else None
    extracted = {'pi': valid_pi}
    for name in ('ps', 'radiotext', 'prog_type'):
        value = most_common_value(name)
        if value:
            extracted[name] = value
    # Some decoders include explicit artist/title in RT+ tags.
    for item in trusted:
        rtplus = item.get('radiotext_plus')
        if isinstance(rtplus, dict):
            for entry in rtplus.get('tags', [])[:15]:
                if not isinstance(entry, dict):
                    continue
                ct = str(entry.get('content-type', '')).lower()
                if ct in ('item.artist', 'item.title') and isinstance(entry.get('data'), str):
                    extracted[ct] = entry['data'][:250]
    return {'decoder_available': True, 'groups': len(trusted), 'data': extracted}


def inspect_rds(path, probe, embedded=None):
    fs = int(probe.get('input_rate') or 0)
    channel_count = int(probe.get('channels') or 0)
    codec = str(probe.get('codec') or '')
    ext = Path(path).suffix.lower()
    tagged = list((embedded or {}).get('rds_tags', []))
    metrics = {'input_sample_rate_hz': fs, 'nyquist_hz': round(fs / 2, 1),
               'tagged_rds_fields': len(tagged)}
    data = {'rds_fields': tagged, 'decoded': {}, 'signal': {}}
    prefix = (f'Source sample rate {fs:,} Hz (Nyquist {fs/2:,.1f} Hz), '
              f'{channel_count} channel(s), codec {codec}. ')
    if fs < 128000:
        result = 'RDS tags only' if tagged else 'RDS not recoverable'
        details = (prefix + '57,000 Hz RDS FM-multiplex data cannot be represented at this rate; '
                   'ordinary radio audio outputs also remove the multiplex. ')
        details += (f'{len(tagged)} RDS-related file tag(s) found; these are stored text, not an RDS signal.'
                    if tagged else 'No RDS-related file tags were found.')
        return {'result': result, 'certainty': 'Possible' if tagged else 'Not measurable',
                'detail': details, 'metrics': metrics, **data}
    if channel_count != 1 or ext not in ('.wav', '.flac'):
        return {'result': 'Raw MPX not established', 'certainty': 'Not measurable',
                'detail': prefix + 'RDS decoding is attempted only for mono, lossless WAV/FLAC FM-multiplex files sampled at 128 kHz or above. ' +
                          f'{len(tagged)} RDS-related file tag(s) found.',
                'metrics': metrics, **data}
    try:
        signal_data = _spectral_check(path, fs)
    except (OSError, subprocess.SubprocessError, ValueError, FloatingPointError):
        signal_data = None
    if not signal_data:
        return {'result': 'No measurable multiplex', 'certainty': 'Not measurable',
                'detail': prefix + 'The file did not provide enough raw multiplex data for the 19 kHz / 57 kHz tests.',
                'metrics': metrics, **data}
    data['signal'] = signal_data
    metrics.update({k: v for k, v in signal_data.items() if isinstance(v, (int, float)) and not isinstance(v, bool)})
    text = (prefix + f"19 kHz peak prominence {signal_data['pilot_prominence_db']:+.1f} dB; "
            f"57 kHz RDS-band energy {signal_data['rds_band_contrast_db']:+.1f} dB "
            f"relative to 51–53.5 and 60.5–63 kHz control bands across "
            f"{signal_data['sampled_seconds']:.1f} s. ")
    if not signal_data['raw_mpx_candidate']:
        return {'result': 'No clear raw RDS signal', 'certainty': 'Not detected',
                'detail': text + 'This is not sufficient evidence of an FM multiplex or decodable RDS; no on-air text was recovered.',
                'metrics': metrics, **data}
    try:
        decoded = _redsea_decode(path)
    except (OSError, subprocess.SubprocessError, ValueError):
        decoded = {'decoder_available': False, 'groups': 0, 'data': {}}
    metrics['rds_groups'] = decoded['groups']
    data['decoded'] = decoded.get('data', {})
    if data['decoded']:
        station = data['decoded'].get('ps') or data['decoded'].get('pi') or 'station unknown'
        return {'result': f'RDS decoded: {station}', 'certainty': 'High',
                'detail': text + f"Decoded {decoded['groups']} RDS groups with consistent PI code; "
                          'station and RadioText are reported only when the decoder returned them. This is transmitted RDS, not file tags.',
                'metrics': metrics, **data}
    if not decoded['decoder_available']:
        return {'result': 'Possible FM multiplex — decoder unavailable', 'certainty': 'Tentative',
                'detail': text + 'A 19 kHz pilot and energy around 57 kHz suggest an FM multiplex candidate, '
                          'but no RDS bits or station data were decoded. ' +
                          str(decoded.get('setup_status', 'Redsea decoder unavailable.')) + ' ',
                'metrics': metrics, **data}
    return {'result': 'RDS not decoded', 'certainty': 'Not detected',
            'detail': text + 'Redsea returned no repeated, consistent RDS programme groups. '
                      'The 57 kHz energy alone cannot identify a song or station.',
            'metrics': metrics, **data}
