"""Exploratory audio-source forensic measurements, not a validated classifier."""
from __future__ import annotations

import io
import numpy as np
from scipy import signal
from pydub import AudioSegment

MAX_SECONDS = 120


def decode_audio(data: bytes, filename: str):
    ext = filename.rsplit('.', 1)[-1].lower()
    if ext not in {'mp3', 'wav', 'flac'}:
        raise ValueError('Upload an MP3, WAV or FLAC recording.')
    audio = AudioSegment.from_file(io.BytesIO(data), format=ext)
    if len(audio) < 5000:
        raise ValueError('Please upload at least 5 seconds of audio.')
    if len(audio) > MAX_SECONDS * 1000:
        raise ValueError('Please trim the recording to two minutes or less.')
    channels = audio.channels
    samples = np.asarray(audio.get_array_of_samples(), dtype=np.float64)
    if channels > 1:
        samples = samples.reshape(-1, channels)
    else:
        samples = samples[:, None]
    samples /= float(2 ** (8 * audio.sample_width - 1))
    return samples, int(audio.frame_rate)


def verdict(value='Unclear', level='Unclear', detail='No sufficiently distinctive signal detected.'):
    return {'result': value, 'certainty': level, 'detail': detail}


def narrow_tone(x, fs, target, tolerance=0.7):
    """Measure a stable narrowband tone against neighboring spectral baseline."""
    if fs / 2 <= target + 8 or len(x) < fs * 5:
        return None
    nper = min(len(x), max(8192, int(fs * 4)))
    f, power = signal.welch(x, fs, nperseg=nper, noverlap=nper // 2, scaling='spectrum')
    inside = (f >= target - tolerance) & (f <= target + tolerance)
    neighborhood = ((f >= target - 9) & (f < target - 2)) | ((f > target + 2) & (f <= target + 9))
    if not inside.any() or neighborhood.sum() < 8:
        return None
    peak = float(np.max(power[inside]))
    baseline = float(np.median(power[neighborhood])) + 1e-18
    snr_db = 10 * np.log10((peak + 1e-18) / baseline)
    freq = float(f[inside][np.argmax(power[inside])])
    # Avoid reporting extremely tiny peaks of effectively silent files.
    relative = 10 * np.log10((peak + 1e-18) / (float(np.mean(x*x)) + 1e-18))
    return {'snr': float(snr_db), 'freq': freq, 'relative': float(relative)}


def electrical(x, fs):
    choices = []
    for base in (50, 60):
        measures = [narrow_tone(x, fs, base*k, tolerance=0.65) for k in (1, 2, 3)]
        valid = [m for m in measures if m and m['snr'] >= 10 and m['relative'] > -65]
        # One isolated tone can easily be musical, demand 2 harmonics.
        if len(valid) >= 2:
            choices.append((base, len(valid), sum(m['snr'] for m in valid)))
    if not choices:
        return verdict(detail='No convincing 50/60 Hz harmonic family detected; music and compression can mask hum.')
    choices.sort(key=lambda c: (c[1], c[2]), reverse=True)
    best = choices[0]
    if len(choices) > 1 and (best[1] == choices[1][1] and best[2] - choices[1][2] < 12):
        return verdict(detail='50 and 60 Hz harmonic patterns were both present or ambiguous.')
    region = '50 Hz regions (including Europe)' if best[0] == 50 else '60 Hz regions (including North America)'
    level = 'High' if best[1] == 3 and best[2] > 65 else 'Possible'
    return verdict(region, level, f'{best[1]} harmonics support a {best[0]} Hz electrical environment somewhere in the recording or transfer chain.')


def broadcast(x, fs):
    targets = [(19000, 'FM stereo pilot (19 kHz)'), (15625, '625-line TV interference (15,625 Hz)'), (15734.26, '525-line TV interference (15,734 Hz)')]
    hits = []
    for hz, name in targets:
        t = narrow_tone(x, fs, hz, tolerance=1.1)
        if t and t['snr'] >= 17 and t['relative'] > -75:
            hits.append((name, t['snr']))
    if not hits:
        return verdict(detail='No clear FM pilot or TV scanning-tone remnants found. Their absence does not rule out broadcasts.')
    hits.sort(key=lambda h: h[1], reverse=True)
    if len(hits) > 1:
        return verdict('Multiple signals', 'Possible', '; '.join(h[0] for h in hits))
    return verdict(hits[0][0], 'Possible', 'A narrowband tone is present near this frequency; other electronic interference is possible.')


def _click_candidates(x, fs):
    """Find isolated broadband impulses from a single audio channel.

    Uses a local linear-prediction residual: a one-sample click differs sharply
    from its immediate neighbors. Group adjacent flagged samples into events.
    This is a conservative *candidate* detector, not a vinyl classifier.
    """
    work_fs = min(fs, 16000)
    if work_fs != fs:
        x = signal.resample_poly(x, work_fs, fs)
    fs = work_fs
    x = signal.sosfilt(signal.butter(3, 1800, btype='highpass', fs=fs, output='sos'), x)
    # Predict center from adjacent samples. Impulsive clicks leave a sharp residual.
    residual = x[1:-1] - .5 * (x[:-2] + x[2:])
    # 10 ms envelopes and a local 1 s median baseline.
    hop = max(1, round(fs * .003))
    n = len(residual) // hop
    if n < 100:
        return np.array([])
    envelope = np.max(np.abs(residual[:n * hop].reshape(n, hop)), axis=1)
    baseline = signal.medfilt(envelope, kernel_size=301)
    residual_strength = np.maximum(envelope - baseline, 0)
    threshold = max(float(np.percentile(residual_strength, 99.7)), 1e-6)
    peaks, _ = signal.find_peaks(residual_strength, height=threshold,
                                 prominence=threshold * .65,
                                 distance=max(1, round(.065 * fs / hop)))
    return (peaks * hop + 1) / fs


def _rotation_candidate(times, period, duration):
    """Assess an actual repeating sequence rather than global phase alone.

    A defect may be absent in some revolutions. Match one click per expected
    revolution and require multiple successive matches and temporal coverage.
    """
    if len(times) < 8:
        return None
    # A small speed tolerance accommodates ordinary turntable variations.
    tol = min(.025, period * .012)
    best = None
    for anchor in times:
        phase = ((times - anchor + period / 2) % period) - period / 2
        aligned = times[np.abs(phase) <= tol]
        revolutions = np.round((aligned - anchor) / period).astype(int)
        unique = np.unique(revolutions)
        if len(unique) < 7:
            continue
        # Look for consecutive matched rotations; missing a few is allowed.
        gaps = np.diff(unique)
        immediate = int(np.sum(gaps == 1))
        span = int(unique[-1] - unique[0] + 1)
        coverage = len(unique) / max(1, span)
        elapsed = (unique[-1] - unique[0]) * period
        # Need a real sequence spanning a substantial part of the recording.
        if immediate < 5 or elapsed < 10 or coverage < .48:
            continue
        # Accidental alignment from a dense rhythm is filtered partly by
        # requiring the matched click pattern to stand out from all impulses.
        phase_fraction = len(aligned) / max(1, len(times))
        expected_random = min(1.0, 2 * tol / period)
        if phase_fraction < max(.20, expected_random * 3.5):
            continue
        score = immediate + 2 * coverage + .1 * len(unique)
        if best is None or score > best['score']:
            best = {'score': score, 'matched': len(unique), 'consecutive': immediate,
                    'coverage': coverage, 'fraction': phase_fraction}
    return best


def vinyl_rotation(samples, fs):
    """Conservatively seek recurring impulse sequences at record rotation rates.

    Checks L/R separately where possible; never infer that absence excludes vinyl.
    Ordinary music can remain periodic, so only 'Possible' is returned.
    """
    if samples.ndim == 1:
        samples = samples[:, None]
    duration = samples.shape[0] / fs
    if duration < 15:
        return verdict(detail='At least 15 seconds needed for recurring vinyl-click assessment.'), None
    candidates = [(33.333333, 1.8), (45.0, 60 / 45), (78.0, 60 / 78)]
    best_by_rpm = {}
    for channel in range(samples.shape[1]):
        times = _click_candidates(samples[:, channel], fs)
        # Numerous candidates usually indicate percussion or compression artifacts.
        if len(times) < 8 or len(times) > duration * 14:
            continue
        for rpm, period in candidates:
            match = _rotation_candidate(times, period, duration)
            if match and (rpm not in best_by_rpm or match['score'] > best_by_rpm[rpm]['score']):
                best_by_rpm[rpm] = match
    if not best_by_rpm:
        return verdict(detail='No convincing rotation-locked sequence of impulsive defects. Vinyl may still be present.'), None
    ranked = sorted(best_by_rpm.items(), key=lambda pair: pair[1]['score'], reverse=True)
    rpm, match = ranked[0]
    if len(ranked) > 1 and ranked[0][1]['score'] < ranked[1][1]['score'] * 1.2:
        return verdict(detail='Several rotation speeds fit the detected transients; cannot distinguish a scratch from musical rhythm.'), None
    detail = (f"{match['matched']} rotation-aligned events across the clip, "
              f"including {match['consecutive']} adjacent-rotation pairs. "
              'Still provisional: repeating drum sounds and transferred vinyl clicks can imitate this signature.')
    return verdict(f'{rpm:g} RPM', 'Possible', detail), rpm


def source_from_tests(rotation, broadcast_test):
    if rotation['result'] != 'Unclear':
        return verdict('Vinyl evidence', 'Possible', 'Rotation-period click pattern detected. Could also be a vinyl transfer recorded onto cassette or broadcast.')
    if broadcast_test['result'].startswith('FM stereo pilot'):
        return verdict('FM broadcast evidence', 'Possible', '19 kHz pilot tone may indicate an FM broadcast in the recording chain.')
    return verdict(detail='Vinyl, cassette and radio overlap acoustically. No source-specific signal met the threshold; cassette cannot be reliably identified from hiss alone.')


def analyze(data: bytes, filename: str):
    samples, fs = decode_audio(data, filename)
    mono = samples.mean(axis=1)
    # Short enough for cloud deployment and avoids near-silent analysis.
    if np.sqrt(np.mean(mono**2)) < 1e-5:
        raise ValueError('This recording is too quiet for analysis.')
    rotation, rpm = vinyl_rotation(samples, fs)
    power = electrical(mono, fs)
    air = broadcast(mono, fs)
    if samples.shape[1] == 1:
        stereo = verdict('Mono', 'High', 'One audio channel in the uploaded file; original may have been stereo.')
    else:
        a, b = samples[:, 0], samples[:, 1]
        corr = np.corrcoef(a[::16], b[::16])[0,1] if np.std(a) and np.std(b) else 1.0
        stereo = verdict('Dual mono / near-mono' if corr > .998 else 'Stereo', 'High', 'Describes the uploaded channels, not necessarily the original studio mix.')
    rows = [
        ('Likely source', source_from_tests(rotation, air)),
        ('Likely vinyl speed', rotation),
        ('Likely power origin', power),
        ('Likely broadcast signals', air),
        ('Likely playback speed', verdict(detail='An original-speed reference recording or verified stable reference tone is needed.')),
        ('Likely recording medium', verdict(detail='Analog versus digital provenance cannot be reliably established from a brief compressed mix alone.')),
        ('Likely audio generation', verdict(detail='Number of copies cannot be estimated reliably from this recording alone.')),
        ('Stereo format', stereo),
    ]
    return rows, {'duration': len(samples)/fs, 'sample_rate': fs, 'channels': samples.shape[1]}
