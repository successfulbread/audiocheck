"""AudioCheck v0.6: evidence-oriented audio provenance indicators.

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
MIN_SECONDS = 4.0
MAX_BYTES = 100 * 1024 * 1024
SAMPLE_RATE = 44100
EXTENSIONS = {".mp3", ".wav", ".flac", ".ogg", ".m4a", ".webm", ".opus"}


def verdict(result="Unclear", certainty="Unclear", detail="Insufficient distinctive evidence."):
    return {"result": result, "certainty": certainty, "detail": detail}


def _command(args, timeout=40):
    try:
        return subprocess.run(args, capture_output=True, check=True, timeout=timeout)
    except FileNotFoundError as exc:
        raise ValueError("FFmpeg is unavailable on the server. Check packages.txt on Streamlit Cloud.") from exc
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
        raise ValueError("Please upload at least four seconds of audio.")
    if duration > MAX_SECONDS + 0.25:
        raise ValueError("Maximum recording length is 5 minutes (300 seconds).")
    if fs < 4000 or channels not in (1, 2):
        raise ValueError("Please upload mono or stereo audio with a standard sample rate.")
    return {"duration": duration, "input_rate": fs, "channels": channels,
            "codec": stream.get("codec_name", "unknown")}


def _windows(duration):
    """Examine up to four distinct 25-second spans spread through the song.

    Do not concatenate windows before periodicity detection. A rotation signal
    must recur within one continuous physical segment, not across jump cuts.
    """
    n = 1 if duration <= 38 else 2 if duration <= 95 else 3 if duration <= 190 else 4
    width = min(25.0, duration / n)
    if n == 1:
        return [(0.0, float(width))]
    starts = np.linspace(0.0, max(0.0, duration - width), n)
    return [(float(start), float(width)) for start in starts]

def _decode_window(path, start, seconds):
    p = _command([
        "ffmpeg", "-nostdin", "-v", "error", "-ss", f"{start:.3f}",
        "-i", str(path), "-t", f"{seconds:.3f}", "-map", "0:a:0",
        "-vn", "-f", "f32le", "-acodec", "pcm_f32le", "-ac", "2",
        "-ar", str(SAMPLE_RATE), "pipe:1"
    ], timeout=60)
    raw = np.frombuffer(p.stdout, dtype="<f4")
    if raw.size < SAMPLE_RATE * 2 * 4:
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


def _mains_channel(x):
    """Track narrowband energy in 8-second frames, including weak harmonics.

    This is ENF-*presence* screening, NOT actual grid matching. Framewise
    periodograms help reject brief musical notes and find persistent weak hum.
    """
    rate = 2000
    low = signal.resample_poly(x.astype(np.float64), 20, 441)
    block = min(rate * 8, (len(low)//rate)*rate)
    hop = max(rate, block // 2)
    if block < rate * 4:
        return {base: {"count": 0, "weak": 0, "snr": 0.0, "freqs": [], "frames": 0} for base in (50,60)}
    items = {base: {harmonic: [] for harmonic in range(1, 6)} for base in (50, 60)}
    windows = 0
    eps = 1e-24
    full_power = max(float(np.mean(x.astype(float) ** 2)), eps)
    for start in range(0, len(low) - block + 1, hop):
        part = low[start:start + block]
        if float(np.sqrt(np.mean(part * part))) < 1e-7:
            continue
        f, p = signal.periodogram(part, fs=rate, window="hann", scaling="spectrum")
        windows += 1
        for base in (50,60):
            for harmonic in range(1, 6):
                target = base * harmonic
                # The shared 300 Hz multiple cannot distinguish 50 from 60 Hz.
                if target == 300:
                    continue
                tol = max(0.45, harmonic * 0.4)
                candidate = np.abs(f - target) <= tol
                near = (np.abs(f-target) >= max(2.1, tol+1.25)) & (np.abs(f-target) <= 11)
                if not np.any(candidate) or np.count_nonzero(near) < 10:
                    continue
                selected = np.where(candidate)[0]
                peakidx = selected[int(np.argmax(p[candidate]))]
                peak = float(p[peakidx])
                floor = float(np.median(p[near]))
                snr = 10 * np.log10((peak+eps)/(floor+eps))
                relative = 10 * np.log10((peak+eps)/(full_power+eps))
                items[base][harmonic].append((snr,relative,float(f[peakidx])))
    results = {}
    for base in (50,60):
        count = 0
        weak = 0
        snrs = []
        freqs = []
        for harmonic, values in items[base].items():
            if not values:
                continue
            arr = np.asarray(values)
            strong_mask = (arr[:,0] >= 10.0) & (arr[:,1] >= -96)
            weaker_mask = (arr[:,0] >= 7.0) & (arr[:,1] >= -103)
            # Persistently constant line frequency is essential: broad music
            # and randomly selected noise peaks drift across FFT frames.
            needed = min(len(arr), max(3, math.ceil(0.6 * len(arr))))
            for mask, required_snr, category in ((strong_mask, 10, 'strong'),
                                                 (weaker_mask, 7, 'weak')):
                if np.count_nonzero(mask) < needed:
                    continue
                observed = arr[mask,2]
                center = float(np.median(observed))
                consistent = np.abs(observed - center) <= 0.34
                if np.count_nonzero(consistent) < needed:
                    continue
                good = arr[mask][consistent]
                if category == 'strong':
                    count += 1
                else:
                    weak += 1
                snrs.append(float(np.median(good[:,0])))
                freqs.append((harmonic, float(np.median(good[:,2]))))
                break
        results[base] = {"count": count, "weak": weak, "snr": round(sum(snrs),1),
                         "freqs": freqs, "frames": windows}
    return results


def _spectrum_window(x, original_rate):
    """Compare mid and individual channels; mid alone can cancel antiphase hum."""
    channels = (x[:,0], x[:,1])
    channel_reports = [_mains_channel(ch) for ch in channels]
    electrical = {}
    for base in (50, 60):
        electrical[base] = max((report[base] for report in channel_reports),
                               key=lambda r: (r["count"], r["weak"], r["snr"]))

    # Use per-channel spectra to avoid antiphase cancellation.
    broadcast = {}
    for name, target, tol in (("FM stereo pilot", 19000.0, 1.7),
                              ("625-line TV", 15625.0, 2.8),
                              ("525-line TV", 15734.26, 2.8)):
        if original_rate / 2 < target + 50:
            broadcast[name] = None
            continue
        attempts = []
        for ch in channels:
            f, p = _psd(ch.astype(float), SAMPLE_RATE, 7)
            m = _tone(f, p, float(np.mean(ch.astype(float)**2)),
                      target, tol, snr_gate=14, relative_gate=-102)
            if m is None:
                continue
            halves = np.array_split(ch, 2)
            checks = []
            for half in halves:
                fh, ph = _psd(half.astype(float), SAMPLE_RATE, 7)
                h = _tone(fh, ph, float(np.mean(half.astype(float)**2)),
                          target, tol, snr_gate=10, relative_gate=-106)
                checks.append(bool(h and h["pass"]))
            m["persistent"] = all(checks)
            attempts.append(m)
        broadcast[name] = max(attempts, key=lambda m: (bool(m["pass"]),
                                    bool(m.get("persistent")), m["snr"]), default=None)

    # Supplemental bandwidth estimate, not a claim of original medium.
    mono = np.mean(x, axis=1, dtype=np.float64)
    f, p = _psd(mono, SAMPLE_RATE, 5)
    cutoff = None
    limit = min(20000, original_rate // 2)
    if len(p) and float(np.max(p)) > 1e-19:
        # Use a 5 kHz reference in addition to the absolute dynamic range to
        # avoid treating high-frequency quantization noise as source bandwidth.
        reference = float(np.max(p))
        for hz in range(1000, int(limit), 500):
            sel = (f >= hz) & (f < hz + 500)
            if np.any(sel) and float(np.max(p[sel])) > reference * 10**(-65/10):
                cutoff = hz + 500
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


def _crackle_window(audio):
    """Count non-rhythmic impulsive clicks; weaker hint than rotational defects.

    These are *not* a vinyl classifier. Clipped percussion, digital glitches,
    radio static and transfer defects can make similar impulses.
    """
    channel_counts = []
    for ch in range(2):
        ts = _click_candidates(audio[:,ch], SAMPLE_RATE)
        if len(ts) < 6:
            continue
        intervals = np.diff(ts)
        if len(intervals) < 5:
            continue
        cv = float(np.std(intervals) / (np.mean(intervals)+1e-12))
        if cv < 0.45:
            continue  # regular beats are unlikely to be random surface crackle
        if len(ts) > 120:
            continue  # highly transient music is not informative
        channel_counts.append(len(ts))
    return max(channel_counts, default=0)


def _surface_noise_window(audio):
    """Screen for irregular broadband disc surface crackle.

    Unlike RPM detection, this does NOT require one defect per revolution.
    Check high-pass impulsiveness in half-second frames, and preferentially
    count noise in quiet passages. Short, regular drums must not be treated
    as record-surface evidence on their own.

    Output is an evidence feature set, NOT a calibrated probability.
    """
    channel_reports = []
    for channel in range(audio.shape[1]):
        work = signal.resample_poly(audio[:, channel].astype(np.float64), 160, 441)
        fs = 16000
        high = signal.sosfilt(
            signal.butter(4, 3800, btype="highpass", fs=fs, output="sos"), work
        )
        frame = fs // 2
        n = len(work) // frame
        if n < 8:
            continue
        raw = work[:n * frame].reshape(n, frame)
        upper = high[:n * frame].reshape(n, frame)
        full_rms = np.sqrt(np.mean(raw * raw, axis=1) + 1e-20)
        high_rms = np.sqrt(np.mean(upper * upper, axis=1) + 1e-20)
        ratio = high_rms / (full_rms + 1e-12)
        centered = upper - upper.mean(axis=1, keepdims=True)
        variance = np.mean(centered * centered, axis=1)
        fourth = np.mean(centered ** 4, axis=1)
        kurt = fourth / (variance * variance + 1e-22)
        active = (full_rms > 0.00020) & (high_rms > 0.00015)
        typical = max(float(np.median(full_rms[active])) if np.any(active) else 0, 1e-5)
        quiet = (active & (full_rms < 0.52 * typical)
                 & (ratio >= 0.115) & (kurt >= 10))
        crackly = active & (kurt >= 11) & (ratio >= .045)
        # Existing strong impulsive-click detector is additional independent
        # evidence; use CV to reject exact click trains / drum machines.
        events = _click_candidates(audio[:, channel], SAMPLE_RATE)
        gaps = np.diff(events)
        irregular = bool(len(events) >= 10 and len(gaps) >= 7 and
                         np.std(gaps) / max(np.mean(gaps), 1e-12) > .58)
        event_frames = np.floor(events * 2).astype(int)
        quiet_clicks = int(sum(0 <= t < len(quiet) and quiet[t] for t in event_frames))
        channel_reports.append({
            "quiet_frames": int(quiet.sum()),
            "crackly_frames": int(crackly.sum()),
            "frames": int(active.sum()),
            "clicks": int(len(events)),
            "quiet_clicks": quiet_clicks,
            "irregular": irregular,
            "high_frequency_ratio": float(np.median(ratio[active])) if np.any(active) else 0.0,
        })
    if not channel_reports:
        return {"quiet_frames": 0, "crackly_frames": 0, "frames": 0,
                "clicks": 0, "quiet_clicks": 0, "irregular": False,
                "high_frequency_ratio": 0.0}
    return max(channel_reports, key=lambda r: (
        r["quiet_frames"] * 5 + min(r["crackly_frames"], 30)
        + min(r["clicks"], 30) * .2
    ))


def _consolidate_surface(windows):
    """Conservative qualitative disc-noise conclusion from independent clues."""
    reports = [w["surface"] for w in windows]
    quiet = sum(r["quiet_frames"] for r in reports)
    broad = sum(r["crackly_frames"] for r in reports)
    clicks = sum(r["clicks"] for r in reports if r["irregular"])
    broad_sections = sum(r["crackly_frames"] >= 9 for r in reports)
    irregular_sections = sum(r["irregular"] for r in reports)
    # Most convincing: irregular impulses and granular non-Gaussian HF noise
    # *during quiet passages*, which are less likely to be drums.
    if quiet >= 3 and broad >= 8 and irregular_sections >= 1:
        detail = (f"Detected irregular short clicks ({clicks} in qualifying sections) "
                  f"and a crackling high-frequency texture in {broad} half-second frames. "
                  f"Importantly, {quiet} noisy frames occurred during quieter passages, "
                  "where ordinary musical percussion is less likely to explain them. "
                  "This strongly suggests a transferred grooved disc (vinyl or shellac); "
                  "it does not reveal record RPM or prove the last playback device was a turntable.")
        return verdict("Disc surface noise likely", "Possible", detail)
    if (irregular_sections >= 2 and broad_sections >= 2 and broad >= 20) or (
        quiet >= 3 and broad >= 14):
        return verdict(
            "Disc-like surface crackle", "Tentative",
            f"Random short impulses and a granular high-frequency texture appear in "
            f"{broad} half-second frames, including {quiet} quiet frames. "
            "These are consistent with a disc transfer but could be noise from another source.",
        )
    if irregular_sections and broad >= 12:
        return verdict(
            "Some surface-crackle evidence", "Tentative",
            f"Irregular impulsive noise and high-frequency transients appear in {broad} "
            "half-second frames, but quiet-section corroboration is insufficient.",
        )
    return verdict(
        "No distinctive disc crackle found", "Not detected",
        "No sufficiently corroborated irregular high-frequency crackle appeared "
        "in the sections analyzed. Clean records may produce none.",
    )


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
    """Return strongest available family with transparent weak vs stronger clue."""
    candidates = []
    for base in (50,60):
        sections = [w["mains"][base] for w in windows]
        rich = sum(s["count"] >= 2 for s in sections)
        corroborated = sum(s["count"] >= 1 and (s["count"]+s["weak"]) >= 2 for s in sections)
        singles = sum(s["count"] >= 1 for s in sections)
        weak_only = sum((s["count"]+s["weak"]) >= 1 for s in sections)
        total = sum(2 * s["count"] + s["weak"] for s in sections)
        # Short recordings permit a tentative harmonic family, never strong.
        # A single strong tone is a clue, NOT a proven mains signature.
        # A second harmonic (even weaker) is essential for the stronger claim.
        if rich >= 2:
            level = 3
        elif rich >= 1 or corroborated >= 2:
            level = 2
        elif corroborated >= 1 or singles >= 2:
            level = 1
        elif singles >= 1 or weak_only >= 2 or any(x["weak"] >= 2 for x in sections):
            level = 0.5
        else:
            level = 0
        candidates.append((base, level, total, rich, corroborated, singles, weak_only, sections))
    candidates.sort(key=lambda c: (c[1],c[2]), reverse=True)
    top = candidates[0]
    rival = candidates[1]
    if top[1] == 0:
        return verdict("None detected", "Not detected",
                       "No persistent narrowband 50/60 Hz peaks cleared even the weak-signal threshold. "
                       "A clean recording can contain no mains hum.")
    if rival[1] > 0 and (top[1]-rival[1] < 1 and top[2] <= rival[2]+2):
        # If one family has a persistent *strong* line plus a corroborating
        # harmonic and the rival has only weak lines, prefer the former, but
        # keep the result tentative. Otherwise avoid guessing a continent.
        top_strong = sum(section["count"] for section in top[7])
        rival_strong = sum(section["count"] for section in rival[7])
        top_weak = sum(section["weak"] for section in top[7])
        if not (top_strong >= 1 and top_weak >= 1 and rival_strong == 0):
            return verdict("50 and 60 Hz candidates", "Tentative",
                           "Both frequency families have measurable lines, but not "
                           "enough independent harmonic evidence to choose one. "
                           "Musical notes may imitate electrical hum.")
    base, level, total, rich, corroborated, singles, weak_only, sections = top
    region = "50 Hz regions (e.g. Europe)" if base == 50 else "60 Hz regions (e.g. N. America)"
    freq_set = []
    for section in sections:
        freq_set.extend(f"{f:.1f}" for _,f in section["freqs"])
    unique_freqs = ', '.join(dict.fromkeys(freq_set))[:110]
    if level >= 2:
        certainty = "Strong" if level >= 3 else "Possible"
        detail = (f"Harmonic family near {base} Hz, supported by independent frequency bands; "
                  f"observed peaks include {unique_freqs} Hz. ")
    else:
        certainty = "Tentative"
        detail = (f"A weak or isolated line suggests the {base} Hz family "
                  f"(observed near {unique_freqs} Hz), but other harmonics are absent or faint. ")
    detail += ("This identifies interference in the recording/transfer chain, not "
               "the song's original country. Musical tones can imitate hum.")
    return verdict(region, certainty, detail)

def _consolidate_broadcast(windows):
    names = ("FM stereo pilot", "625-line TV", "525-line TV")
    candidates = []
    for name in names:
        good = [w["broadcast"].get(name) for w in windows]
        found = [m for m in good if m and m["pass"] and m.get("persistent")]
        tentative = [m for m in good if m and m["pass"]]
        if len(found) >= 2 or (len(windows) == 1 and len(found) == 1):
            candidates.append((name, 2, len(found)))
        elif len(found) == 1 or len(tentative) >= 2:
            candidates.append((name, 1, len(tentative)))
    if not candidates:
        sample_rate_testable = any(value is not None for w in windows for value in w["broadcast"].values())
        if not sample_rate_testable:
            return verdict("Cannot assess", "Not measurable",
                           "Sampling rate is too low to retain the TV-line and FM-pilot frequencies.")
        max_band = max((w.get("cutoff") or 0) for w in windows)
        if max_band and max_band < 15000:
            return verdict("High frequencies unavailable", "Not measurable",
                           "Audio content appears filtered below the broadcast tone ranges. "
                           "Absence of pilot/TV signals is not informative.")
        return verdict("None detected", "Not detected",
                       "No persistent 19 kHz FM-pilot or 15.625/15.734 kHz TV-line tone "
                       "cleared the threshold; filtering may have removed them.")
    candidates.sort(key=lambda c:(c[1],c[2]), reverse=True)
    names_text = ' + '.join(c[0] for c in candidates if c[1]==candidates[0][1])
    return verdict(names_text, "Possible" if candidates[0][1]==2 else "Tentative",
                   "A narrowband signal was detected near a historical broadcast-related "
                   "frequency. It can enter during copying, and unrelated electronics may mimic it.")

def _stereo_format(windows, channels):
    if channels == 1:
        return verdict("Mono", "High", "The uploaded audio has one channel; the original studio may differ.")
    values = [w["stereo_corr"] for w in windows if w.get("stereo_corr") is not None]
    if not values:
        return verdict("Cannot assess", "Not measurable", "Low channel levels prevent stereo measurement.")
    if float(np.median(values)) >= .998:
        return verdict("Dual mono / near-mono", "High", "Two channels are nearly identical.")
    return verdict("Stereo", "High", "The uploaded channels differ measurably.")

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
    clips = [w["clipped"] for w in windows]
    cutoffs = [w["cutoff"] for w in windows if w["cutoff"]]
    dropouts = sum(w["dropouts"] for w in windows)
    pilot = [w["pilot_jitter"] for w in windows if w.get("pilot_jitter") is not None]
    return {"near_full_scale_percent": round(float(np.mean(clips) * 100), 3),
            "spectral_upper_energy_khz": round(float(np.median(cutoffs)) / 1000, 1) if cutoffs else None,
            "possible_interruptions": dropouts,
            "pilot_frequency_scatter_hz": round(float(np.median(pilot)),2) if pilot else None,
            "sampled_sections": len(windows)}

def analyze_path(path, file_name=None):
    """Read selected portions of a 4--300 second file, return (rows, metadata)."""
    path = Path(path)
    if path.suffix.lower() not in EXTENSIONS:
        raise ValueError("Upload MP3, WAV, FLAC, OGG or M4A audio.")
    if path.stat().st_size > MAX_BYTES:
        raise ValueError("Maximum file size is 100 MB.")
    metadata = _probe(path)
    analyzed = []
    analyzed_seconds = 0.0
    for start, seconds in _windows(metadata["duration"]):
        audio = _decode_window(path, start, seconds)
        if np.sqrt(float(np.mean(audio * audio))) < 1e-6:
            continue
        mains, air, cutoff = _spectrum_window(audio, metadata["input_rate"])
        a, b = audio[::60].T
        stereo_corr = (float(np.corrcoef(a,b)[0,1])
                       if np.std(a) > 1e-6 and np.std(b) > 1e-6 else None)
        fm = air.get("FM stereo pilot")
        pilot_jitter = (_pilot_variation_hz(audio)
                        if fm and fm["pass"] and fm.get("persistent") else None)
        analyzed.append({"vinyl":_vinyl_window(audio), "surface":_surface_noise_window(audio), "mains":mains,
                         "broadcast":air, "cutoff":cutoff, "dropouts":_dropout_candidates(audio),
                         "clipped":float(np.mean(np.abs(audio) >= .998)),
                         "pilot_jitter":pilot_jitter, "stereo_corr":stereo_corr})
        analyzed_seconds += len(audio)/SAMPLE_RATE
        del audio # Avoid keeping 100+ MB of decoded audio in RAM.
    if not analyzed:
        raise ValueError("The audio was silent or too faint to analyze.")
    rotation = _consolidate_vinyl(analyzed)
    surface = _consolidate_surface(analyzed)
    electrical = _consolidate_electrical(analyzed)
    broadcast = _consolidate_broadcast(analyzed)
    diag = _diagnostics(analyzed)
    fm = "FM stereo pilot" in broadcast["result"] and broadcast["certainty"] in {"Possible","Tentative"}
    vinyl = rotation["certainty"] == "Possible"
    tape = diag["possible_interruptions"] >= 2
    surface_likely = surface["result"] == "Disc surface noise likely"
    surface_hint = surface["certainty"] in ("Possible", "Tentative")
    if fm and (vinyl or surface_likely):
        source = verdict("Disc transfer, possible FM chain", "Possible",
                         "Both disc-surface artifacts and a 19 kHz FM pilot are present. "
                         "A record may have been broadcast or later copied from radio. "
                         + surface["detail"])
    elif vinyl:
        source = verdict("Disc transfer likely", "Possible",
                         "Recurring physical clicks aligned to a turntable revolution. "
                         + rotation["detail"])
    elif surface_likely:
        source = verdict("Disc transfer likely", "Possible",
                         "The main clues are irregular, high-frequency surface crackle, "
                         "including noise in quieter passages. "
                         + surface["detail"])
    elif fm:
        source = verdict("FM radio transfer possible", "Possible", broadcast["detail"])
    elif surface_hint:
        source = verdict("Disc transfer possible", "Tentative", surface["detail"])
    elif tape:
        source = verdict("Tape-like transfer (weak)", "Tentative",
                         "Several abrupt interruptions resemble tape dropouts, "
                         "but digital edits and sound effects can do the same.")
    else:
        source = verdict("Source not established", "Not measurable",
                         "No distinctive disc-noise, rotation, FM pilot or tape "
                         "pattern was supported. A clean disc can sound like a clean tape.")
    stereo = _stereo_format(analyzed, metadata["channels"])
    if vinyl or surface_likely:
        medium = verdict("Disc-transfer evidence", "Possible", "Noise and/or a repeating defect are consistent with a grooved disc somewhere in the transfer chain.")
    elif tape:
        medium = verdict("Tape-like dropout evidence", "Tentative", "Brief interruptions may suggest tape, but are not a conclusive source identification.")
    elif fm:
        medium = verdict("Broadcast-chain evidence", "Possible", "A 19 kHz pilot suggests an FM chain somewhere in the recording history.")
    else:
        medium = verdict("No distinctive artifact", "Not measurable", "Neither analog nor digital origin can be established from the absence of artifacts.")
    interruptions = diag["possible_interruptions"]
    dropout = (verdict(f"{interruptions} interruptions", "Tentative", "Sudden short level losses detected. Not uniquely associated with cassette tape.")
               if interruptions else verdict("None detected", "Not detected", "No near-silent interruptions in examined sections."))
    cutoff = diag["spectral_upper_energy_khz"]
    bandwidth = (verdict(f"Energy to ~{cutoff:g} kHz", "High", "Measured upper spectral energy, not necessarily a true cutoff; MP3 encoding can remove high frequencies.")
                 if cutoff is not None else verdict("Cannot assess", "Not measurable", "No usable spectrum."))
    rows = [
        ("Likely audio source", source),
        ("Disc surface noise", surface),
        ("Vinyl rotation", rotation),
        ("Likely power system", electrical),
        ("Radio / TV signals", broadcast),
        ("Playback speed", verdict("No speed reference", "Not measurable", "Absolute playback speed requires a reliable comparison or calibrated reference.")),
        ("Recording-medium clues", medium),
        ("Possible tape dropouts", dropout),
        ("Audio bandwidth", bandwidth),
        ("Stereo format", stereo),
    ]
    metadata["analyzed_seconds"] = round(analyzed_seconds, 1)
    metadata["diagnostics"] = diag
    return rows, metadata

def analyze(data: bytes, filename: str):
    """Bytes-oriented API wrapper; temporary file is always removed."""
    ext = Path(filename).suffix.lower()
    if ext not in EXTENSIONS:
        raise ValueError("Upload an MP3, WAV, FLAC, OGG or M4A file.")
    if len(data) > MAX_BYTES:
        raise ValueError("Maximum file size is 100 MB.")
    with tempfile.TemporaryDirectory(prefix="audiocheck_") as tempdir:
        path = Path(tempdir) / ("upload" + ext)
        path.write_bytes(data)
        return analyze_path(path, filename)
