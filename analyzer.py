"""AudioCheck v0.5: evidence-oriented audio provenance indicators.

Measures evidence, not proof of an original recording medium or location.
Uses FFmpeg/FFprobe to decode bounded, distributed windows from a file.
"""
from __future__ import annotations

import json
import math
import os
from pathlib import Path
import subprocess
import tempfile

import numpy as np
from scipy import ndimage, signal

MAX_SECONDS = 300.0
MIN_SECONDS = 10.0
MAX_BYTES = 100 * 1024 * 1024
SAMPLE_RATE = 44100
EXTENSIONS = {".mp3", ".wav", ".flac", ".ogg", ".m4a"}


def verdict(result="Unclear", certainty="Unclear", detail="Insufficient distinctive evidence."):
    return {"result": result, "certainty": certainty, "detail": detail}


def _command(args, timeout=40):
    try:
        return subprocess.run(args, capture_output=True, check=True, timeout=timeout)
    except FileNotFoundError as exc:
        raise ValueError("FFmpeg is unavailable on the server. Check packages.txt.") from exc
    except subprocess.TimeoutExpired as exc:
        raise ValueError("The file took too long to decode; please try another file.") from exc
    except subprocess.CalledProcessError as exc:
        raise ValueError("FFmpeg could not read the uploaded recording.") from exc


def _probe(path):
    p = _command([
        "ffprobe", "-v", "error", "-select_streams", "a:0",
        "-show_entries", "stream=codec_name,sample_rate,channels,duration:format=duration",
        "-of", "json", str(path)
    ])
    try:
        data = json.loads(p.stdout)
        stream = data["streams"][0]
        duration = float(stream.get("duration") or data["format"]["duration"])
        fs = int(stream["sample_rate"])
        channels = int(stream["channels"])
    except (KeyError, IndexError, ValueError, TypeError) as exc:
        raise ValueError("Unable to determine audio duration and format.") from exc
    if not math.isfinite(duration) or duration < MIN_SECONDS:
        raise ValueError("Please upload at least 10 seconds of audio.")
    if duration > MAX_SECONDS + 0.25:
        raise ValueError("Maximum recording length is 5 minutes (300 seconds).")
    if fs < 4000 or channels not in (1, 2):
        raise ValueError("Please upload mono or stereo audio with a standard sample rate.")
    return {"duration": duration, "input_rate": fs, "channels": channels,
            "codec": stream.get("codec_name", "unknown")}


def _windows(duration):
    """Analyze independent portions from beginning, middle and end, at most 160 s."""
    n = 1 if duration <= 50 else 2 if duration <= 100 else 3 if duration <= 165 else 4
    width = min(40.0, duration / n)
    starts = np.linspace(0.0, max(0.0, duration - width), n)
    return [(float(t), float(width)) for t in starts]


def _decode_window(path, start, seconds):
    p = _command([
        "ffmpeg", "-nostdin", "-v", "error", "-ss", f"{start:.3f}",
        "-i", str(path), "-t", f"{seconds:.3f}", "-map", "0:a:0",
        "-vn", "-f", "f32le", "-acodec", "pcm_f32le", "-ac", "2",
        "-ar", str(SAMPLE_RATE), "pipe:1"
    ], timeout=60)
    raw = np.frombuffer(p.stdout, dtype="<f4")
    if raw.size < SAMPLE_RATE * 2 * 5:
        raise ValueError("Insufficient decoded audio for analysis.")
    return raw[:(raw.size // 2) * 2].reshape(-1, 2).copy()


def _psd(x, fs, seconds=6.0):
    nper = min(len(x), max(4096, int(fs * seconds)))
    return signal.welch(x, fs=fs, nperseg=nper, noverlap=nper // 2,
                        scaling="spectrum", average="median")


def _tone(f, power, rms_sq, target, tolerance, snr_gate=12, relative_gate=-76):
    if f[-1] < target + 14:
        return None
    near = np.abs(f - target) <= tolerance
    local = (np.abs(f - target) >= max(2.5, tolerance + 1.5)) & (np.abs(f - target) <= 14)
    if near.sum() < 1 or local.sum() < 12:
        return None
    idx = np.where(near)[0][int(np.argmax(power[near]))]
    peak = float(power[idx])
    floor = float(np.median(power[local]))
    if not np.isfinite(peak) or peak <= 0:
        return None
    snr = 10 * np.log10((peak + 1e-20) / (floor + 1e-20))
    relative = 10 * np.log10((peak + 1e-20) / (rms_sq + 1e-20))
    return {"freq": float(f[idx]), "snr": float(snr), "relative": float(relative),
            "pass": bool(snr >= snr_gate and relative >= relative_gate)}


def _spectrum_window(x, original_rate):
    """Use an 8 s low-frequency PSD and independent 6 s high-frequency PSDs."""
    mono = np.mean(x, axis=1, dtype=np.float64)
    low = signal.resample_poly(mono, 1, 8)
    fs_low = SAMPLE_RATE / 8
    f_low, p_low = _psd(low, fs_low, 8)
    low_rms = float(np.mean(low * low))
    electrical = {}
    for base in (50, 60):
        measures = [_tone(f_low, p_low, low_rms, base * k, .75 * k,
                          snr_gate=12, relative_gate=-73) for k in (1, 2, 3, 4)]
        passed = [m for m in measures if m and m["pass"]]
        electrical[base] = {"count": len(passed), "snr": float(sum(m["snr"] for m in passed)),
                            "harmonics": passed}
    # Spectrum analysis only works if the original recording had enough sample rate.
    f_high, p_high = _psd(mono, SAMPLE_RATE, 6)
    rms = float(np.mean(mono * mono))
    broadcast = {}
    for name, target, tol in (("FM stereo pilot", 19000, 1.7),
                              ("625-line TV", 15625, 2.8),
                              ("525-line TV", 15734.26, 2.8)):
        if original_rate / 2 < target + 50:
            broadcast[name] = None
            continue
        m = _tone(f_high, p_high, rms, target, tol, snr_gate=18,
                  relative_gate=-74)
        # A persistent signal is less likely to be a one-off synthesizer note.
        half = len(mono) // 2
        if m is not None and m["pass"] and half >= int(7 * SAMPLE_RATE):
            halves = []
            for segment in (mono[:half], mono[half:]):
                fh, ph = _psd(segment, SAMPLE_RATE, 6)
                halves.append(_tone(fh, ph, float(np.mean(segment * segment)),
                                    target, tol, snr_gate=12, relative_gate=-78))
            m["persistent"] = bool(all(h and h["pass"] for h in halves))
        elif m is not None:
            m["persistent"] = False
        broadcast[name] = m
    # Supplemental spectrum reporting, not classification of original medium.
    step = 500
    limit = min(20000, original_rate // 2)
    cutoff = None
    floor = float(np.max(p_high))
    if floor > 1e-19:
        for hz in range(1000, limit, step):
            band = (f_high >= hz) & (f_high < hz + step)
            if np.any(band) and np.max(p_high[band]) > floor * 10 ** (-65 / 10):
                cutoff = hz + step
    return electrical, broadcast, cutoff


def _click_candidates(x, fs):
    """Impulsive outliers from a short linear-prediction residual.

    Restrict duration of the impulse. Percussion remains an important ambiguity.
    """
    if len(x) < fs * 10:
        return np.empty(0, dtype=float)
    work = signal.resample_poly(x, 160, 441) if fs == SAMPLE_RATE else x
    rate = 16000 if fs == SAMPLE_RATE else fs
    hp = signal.sosfilt(signal.butter(3, 2400, "highpass", fs=rate, output="sos"), work)
    residual = hp[1:-1] - 0.5 * (hp[:-2] + hp[2:])
    hop = max(1, int(rate * .0025))
    n = len(residual) // hop
    if n < 100:
        return np.empty(0, dtype=float)
    env = np.max(np.abs(residual[:n * hop].reshape(n, hop)), axis=1)
    med = float(np.median(env)) + 1e-12
    local = ndimage.median_filter(env, size=401, mode="reflect") + med * .1
    excess = np.maximum(env - local, 0)
    global_gate = max(med * 7.0, float(np.percentile(env, 99.3)) * 1.1)
    peaks, _ = signal.find_peaks(env, height=global_gate,
                                 prominence=global_gate * .6,
                                 distance=max(1, int(.085 * rate / hop)))
    if len(peaks) == 0:
        return np.empty(0, dtype=float)
    widths = signal.peak_widths(env, peaks, rel_height=.5)[0] * hop / rate
    contrast = env[peaks] / local[peaks]
    good = (widths <= .014) & (contrast >= 6.0) & (excess[peaks] >= med * 6)
    return (peaks[good] * hop / rate).astype(float)


def _rotation_matches(times, target_period):
    if len(times) < 9 or len(times) > 230:
        return None
    # Allow up to 2.5% off nominal speed, and infer actual period from click pairs.
    periods = [target_period]
    dt = times[:, None] - times[None, :]
    positive = dt[dt > .2]
    for mult in range(1, 12):
        candidates = positive / mult
        candidates = candidates[(candidates > target_period * .975) &
                                (candidates < target_period * 1.025)]
        if candidates.size:
            hist, edges = np.histogram(candidates, bins=30,
                                       range=(target_period * .975, target_period * 1.025))
            for idx in np.argsort(hist)[-2:]:
                if hist[idx] >= 2:
                    periods.append(float((edges[idx] + edges[idx + 1]) / 2))
    best = None
    # Scan candidate periods, anchor to individual impulses, validate consecutive turns.
    for period in sorted(set(round(p, 5) for p in periods)):
        tol = min(.018, period * .012)
        for anchor in times:
            nturn = np.rint((times - anchor) / period).astype(int)
            residual = np.abs(times - (anchor + nturn * period))
            picked = residual < tol
            if picked.sum() < 9:
                continue
            indices = nturn[picked]
            samples = times[picked]
            # Only one closest event from each revolution.
            keep = {}
            for idx, t, err in zip(indices, samples, residual[picked]):
                if idx not in keep or err < keep[idx][1]:
                    keep[idx] = (float(t), float(err))
            if len(keep) < 9:
                continue
            keys = np.array(sorted(keep))
            vals = np.array([keep[k][0] for k in keys])
            span = (keys[-1] - keys[0]) * period
            coverage = len(keys) / (keys[-1] - keys[0] + 1)
            neighbors = int(np.count_nonzero(np.diff(keys) == 1))
            if span < 15 or coverage < .60 or neighbors < 7:
                continue
            slope, offset = np.polyfit(keys.astype(float), vals, 1)
            if abs(slope - target_period) > target_period * .025:
                continue
            fiterr = float(np.sqrt(np.mean((vals - (slope * keys + offset)) ** 2)))
            if fiterr > min(.010, period * .009):
                continue
            fraction = len(keys) / max(len(times), 1)
            if fraction < .17:
                continue
            score = len(keys) * coverage / (1 + fiterr * 80)
            if best is None or score > best["score"]:
                best = {"score": score, "events": len(keys), "pairs": neighbors,
                        "span": span, "period": float(slope),
                        "fit_ms": fiterr * 1000}
    return best


def _vinyl_window(audio):
    records = {}
    for ch in range(2):
        times = _click_candidates(audio[:, ch].astype(float), SAMPLE_RATE)
        duration = len(audio) / SAMPLE_RATE
        if len(times) < 9 or len(times) > duration * 5.5:
            continue
        for rpm, period in ((33.333, 1.8), (45.0, 4 / 3), (78.0, 60 / 78)):
            evidence = _rotation_matches(times, period)
            if evidence and (rpm not in records or evidence["score"] > records[rpm]["score"]):
                records[rpm] = evidence
    if not records:
        return None
    ranked = sorted(records.items(), key=lambda item: item[1]["score"], reverse=True)
    if len(ranked) > 1 and ranked[0][1]["score"] < ranked[1][1]["score"] * 1.3:
        return None
    return {"rpm": ranked[0][0], **ranked[0][1]}


def _consolidate_vinyl(windows):
    hits = [w["vinyl"] for w in windows if w["vinyl"]]
    if not hits:
        return verdict("None detected", "Not detected", "No repeatable rotation-locked click sequence cleared the detection checks. This does not exclude clean vinyl.")
    rpm_scores = {}
    for h in hits:
        rpm_scores[h["rpm"]] = rpm_scores.get(h["rpm"], 0) + h["score"]
    ranked = sorted(rpm_scores.items(), key=lambda kv: kv[1], reverse=True)
    if len(ranked) > 1 and ranked[0][1] < ranked[1][1] * 1.45:
        return verdict(detail="Different portions of the song suggested competing speeds; a musical rhythm may be responsible.")
    rpm = ranked[0][0]
    qualified = [h for h in hits if h["rpm"] == rpm]
    events = max(h["events"] for h in qualified)
    detail = (f"Detected rotation-aligned sharp impulses consistent with {rpm:g} RPM "
              f"in {len(qualified)} sampled section(s), with at least {events} aligned events in one section. "
              "Percussion, repeated samples and earlier vinyl-to-tape transfers can imitate this pattern.")
    return verdict(f"{rpm:g} RPM", "Possible", detail)


def _consolidate_electrical(windows):
    scores = {}
    for base in (50, 60):
        hits = [w["mains"][base] for w in windows if w["mains"][base]["count"] >= 2]
        # A single convincing isolated section can qualify if it has >= 3 harmonics.
        strong_single = len(hits) == 1 and hits[0]["count"] >= 3 and hits[0]["snr"] >= 52
        if len(hits) >= 2 or strong_single:
            scores[base] = (len(hits), sum(min(h["count"], 4) for h in hits),
                            sum(h["snr"] for h in hits))
    if not scores:
        return verdict("None detected", "Not detected", "No sufficiently strong, persistent 50/60 Hz harmonic pattern was detected. This does not establish the absence of electrical interference.")
    ranked = sorted(scores.items(), key=lambda kv: (kv[1][1], kv[1][2]), reverse=True)
    if len(ranked) > 1 and ranked[0][1][1] <= ranked[1][1][1] + 1:
        return verdict(detail="Both 50 Hz and 60 Hz families were plausible; the electrical environment is ambiguous.")
    base, (regions, count, score) = ranked[0]
    label = "50 Hz regions (incl. Europe)" if base == 50 else "60 Hz regions (incl. North America)"
    return verdict(label, "Possible",
                   f"A {base} Hz harmonic family was present in {regions} sampled section(s). "
                   "The interference may have entered during recording, copying, or digitization. "
                   "This is not a verified geographic identification or ENF grid matching.")


def _consolidate_broadcast(windows):
    names = ("FM stereo pilot", "625-line TV", "525-line TV")
    matches = []
    for name in names:
        good = [w["broadcast"].get(name) for w in windows]
        good = [m for m in good if m and m["pass"] and m.get("persistent")]
        if len(good) >= 2 or (len(windows) == 1 and len(good) == 1 and good[0]["snr"] >= 22):
            matches.append((name, float(np.median([g["snr"] for g in good]))))
    if not matches:
        testable = any(value is not None for w in windows for value in w["broadcast"].values())
        if not testable:
            return verdict("Not testable", "Not measurable", "The recording sample rate is too low for the FM/TV frequencies checked.")
        return verdict("None detected", "Not detected", "No qualifying 19 kHz FM pilot or TV line-frequency interference was detected in the tested audio. Lossy encoding and filtering may have removed them.")
    matches.sort(key=lambda e: e[1], reverse=True)
    if len(matches) > 1:
        names_text = ", ".join(name for name, _ in matches)
        return verdict("Multiple signals", "Possible", names_text + ". Different transfer stages may be involved.")
    name = matches[0][0]
    return verdict(name, "Possible",
                   "Persistent narrowband interference at the expected frequency; electronic equipment other than broadcasts may cause it.")


def _stereo_format(windows, channels):
    if channels == 1:
        return verdict("Mono", "High", "The uploaded audio has one channel; this does not establish the original studio format.")
    values = []
    for w in windows:
        a, b = w["audio"][::48].T
        if np.std(a) < 1e-6 or np.std(b) < 1e-6:
            continue
        values.append(float(np.corrcoef(a, b)[0, 1]))
    if not values:
        return verdict(detail="Channel levels were too low to assess stereo separation.")
    if float(np.median(values)) >= .998:
        return verdict("Dual mono / near-mono", "High", "The two uploaded channels are almost identical.")
    return verdict("Stereo", "High", "The uploaded channels differ. This does not establish the original studio format.")


def _dropout_candidates(audio):
    """Count brief near-silent interruptions, without inferring tape origin."""
    block = int(SAMPLE_RATE * .05)
    n = len(audio) // block
    if n < 100:
        return 0
    frames = audio[:n * block].reshape(n, block, 2).astype(float)
    rms = np.sqrt(np.mean(frames * frames, axis=(1, 2)))
    typical = ndimage.median_filter(rms, size=41, mode="reflect")
    quiet = (rms < typical * .10) & (typical > .003)
    labels, count = ndimage.label(quiet)
    found = 0
    for idx in range(1, count + 1):
        points = np.flatnonzero(labels == idx)
        if not 2 <= len(points) <= 12:
            continue
        first, last = int(points[0]), int(points[-1])
        if first < 2 or last + 3 >= n:
            continue
        if rms[first-2:first].mean() > typical[first] * .55 and \
           rms[last+1:last+3].mean() > typical[last] * .55:
            found += 1
    return found


def _pilot_variation_hz(audio):
    """Estimate frequency scatter of a strong 19 kHz tone, without diagnosing tape speed."""
    mono = np.mean(audio, axis=1, dtype=np.float64)
    n = int(SAMPLE_RATE * 2)
    if len(mono) < n * 5:
        return None
    freqs = np.fft.rfftfreq(n, d=1/SAMPLE_RATE)
    band = (freqs >= 18960) & (freqs <= 19040)
    positions = np.where(band)[0]
    estimates = []
    for start in range(0, len(mono) - n + 1, n):
        chunk = mono[start:start+n]
        fft = np.abs(np.fft.rfft(chunk * np.hanning(n)))
        j = positions[np.argmax(fft[band])]
        surrounding = np.concatenate((fft[max(0,j-30):max(0,j-9)], fft[j+10:j+31]))
        if len(surrounding) < 15 or fft[j] < max(float(np.median(surrounding)) * 10, 1e-8):
            continue
        # Parabolic refinement of peak location.
        if 1 <= j < len(fft)-1:
            y = np.log(np.maximum(fft[j-1:j+2], 1e-15))
            denom = y[0] - 2*y[1] + y[2]
            correction = .5 * (y[0] - y[2]) / denom if abs(denom) > 1e-12 else 0.0
            correction = float(np.clip(correction, -.5, .5))
        else:
            correction = 0.0
        estimates.append((j + correction) * SAMPLE_RATE / n)
    if len(estimates) < 6:
        return None
    values = np.asarray(estimates)
    return float(np.median(np.abs(values - np.median(values))) * 1.4826)


def _diagnostics(windows):
    # Beta measurements are descriptive only. They do not decide cassette or copy generation.
    clips = []
    cutoffs = []
    dropouts = 0
    pilot_jitter = []
    for w in windows:
        audio = w["audio"]
        clips.append(float(np.mean(np.abs(audio) >= .998)))
        if w["cutoff"]:
            cutoffs.append(w["cutoff"])
        dropouts += _dropout_candidates(audio)
        fm = w["broadcast"].get("FM stereo pilot")
        if fm and fm["pass"] and fm.get("persistent"):
            variation = _pilot_variation_hz(audio)
            if variation is not None:
                pilot_jitter.append(variation)
    return {"near_full_scale_percent": round(float(np.mean(clips) * 100), 3),
            "spectral_upper_energy_khz": round(float(np.median(cutoffs)) / 1000, 1) if cutoffs else None,
            "possible_interruptions": dropouts,
            "pilot_frequency_scatter_hz": round(float(np.median(pilot_jitter)), 2) if pilot_jitter else None,
            "sampled_sections": len(windows)}


def analyze_path(path, file_name=None):
    """Analyze a file on disk. Returns (rows, metadata)."""
    path = Path(path)
    if path.suffix.lower() not in EXTENSIONS:
        raise ValueError("Upload an MP3, WAV, FLAC, OGG or M4A file.")
    if path.stat().st_size > MAX_BYTES:
        raise ValueError("Maximum file size is 100 MB.")
    metadata = _probe(path)
    raw_sections = _windows(metadata["duration"])
    analyzed = []
    for start, seconds in raw_sections:
        audio = _decode_window(path, start, seconds)
        if np.sqrt(float(np.mean(audio * audio))) < 1e-6:
            continue
        mains, air, cutoff = _spectrum_window(audio, metadata["input_rate"])
        analyzed.append({"vinyl": _vinyl_window(audio), "mains": mains,
                         "broadcast": air, "cutoff": cutoff, "audio": audio})
    if not analyzed:
        raise ValueError("The audio was silent or too faint to analyze.")
    rotation = _consolidate_vinyl(analyzed)
    electrical = _consolidate_electrical(analyzed)
    broadcast = _consolidate_broadcast(analyzed)
    fm_hits = [w["broadcast"].get("FM stereo pilot") for w in analyzed]
    fm_hits = [x for x in fm_hits if x and x["pass"] and x.get("persistent")]
    fm_accepted = len(fm_hits) >= 2 or (len(analyzed) == 1 and
                                       len(fm_hits) == 1 and fm_hits[0]["snr"] >= 22)
    vinyl_accepted = rotation["certainty"] == "Possible"
    if vinyl_accepted and fm_accepted:
        source = verdict("Vinyl + FM evidence", "Possible",
                         "Both rotation-period defects and an FM stereo pilot were detected; "
                         "they may originate from different copying stages.")
    elif vinyl_accepted:
        source = verdict("Vinyl evidence", "Possible",
                         "Periodic groove-like defects detected; the final medium might still be cassette or a broadcast.")
    elif fm_accepted:
        source = verdict("FM radio evidence", "Possible",
                         "A 19 kHz pilot remnant suggests FM stereo broadcast somewhere in the transfer chain.")
    else:
        source = verdict("No distinctive signature", "Not detected", "Neither a rotation-locked vinyl signature nor an FM stereo pilot passed the tests. Cassette, vinyl and radio all remain possible.")
    stereo = _stereo_format(analyzed, metadata["channels"])
    diag = _diagnostics(analyzed)
    recording = (verdict("Analog disc evidence", "Possible",
                         "Rotation-locked impulses suggest a disc somewhere in the recording chain, not necessarily the original studio master.")
                 if vinyl_accepted else
                 verdict("No distinctive signature", "Not detected",
                         "The checks did not identify a medium-specific signature. This is not evidence of digital or cassette origin."))
    interruptions = diag["possible_interruptions"]
    dropout = (verdict(f"{interruptions} possible interruption(s)", "Possible",
                       "Brief level dropouts were detected. Musical rests, edits and digital faults can produce similar events; this is not a cassette identification.")
               if interruptions else
               verdict("None detected", "Not detected",
                       "No brief near-silent interruptions qualified in the analyzed portions. This does not exclude tape."))
    cutoff = diag["spectral_upper_energy_khz"]
    bandwidth = (verdict(f"Energy up to ~{cutoff:g} kHz", "Possible",
                         "Approximate highest half-kilohertz band above the analysis noise threshold. Not a verified audio bandwidth cutoff or proof of format.")
                 if cutoff is not None else
                 verdict("Not measurable", "Not measurable", "Not enough useful spectrum to estimate upper audio energy."))
    rows = [
        ("Likely source", source),
        ("Vinyl rotation", rotation),
        ("Power-system signature", electrical),
        ("Radio / TV signals", broadcast),
        ("Playback speed", verdict("No speed reference", "Not measurable",
                                   "Cannot establish absolute playback speed without a calibrated reference tone or comparison recording.")),
        ("Recording-medium evidence", recording),
        ("Possible tape dropouts", dropout),
        ("Upper audio energy", bandwidth),
        ("Stereo format", stereo),
    ]
    metadata["analyzed_seconds"] = round(sum(len(w["audio"]) / SAMPLE_RATE for w in analyzed), 1)
    metadata["diagnostics"] = diag
    return rows, metadata


def analyze(data: bytes, filename: str):
    """Streamlit-compatible bytes wrapper; temporary file is always removed."""
    ext = Path(filename).suffix.lower()
    if ext not in EXTENSIONS:
        raise ValueError("Upload an MP3, WAV, FLAC, OGG or M4A file.")
    if len(data) > MAX_BYTES:
        raise ValueError("Maximum file size is 100 MB.")
    with tempfile.TemporaryDirectory(prefix="audiocheck_") as tempdir:
        path = Path(tempdir) / ("upload" + ext)
        path.write_bytes(data)
        return analyze_path(path, filename)
