"""AudioCheck v0.9: best-supported, calibrated evidence indicators.

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
EXTENSIONS = {".mp3", ".wav", ".flac", ".ogg", ".m4a", ".webm", ".opus", ".mpeg", ".mpga"}


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


def _scan_broadcast_tone(ch, target, margin, original_rate):
    """Find a persistent *narrow* line near a broadcast standard.

    Offset permits moderately mis-speeded analog copies; persistence and
    spectral prominence reduce matches to ordinary music.
    """
    if original_rate / 2 < target + margin + 55:
        return None
    x=ch.astype(float)
    f,p=_psd(x,SAMPLE_RATE,7)
    candidates=np.where(np.abs(f-target)<=margin)[0]
    if not len(candidates): return None
    # Several adjacent FFT bins may contain the same physical line.
    selected=candidates[np.argsort(p[candidates])[-10:]]
    options=[]
    rms=max(float(np.mean(x*x)),1e-20)
    for idx in selected:
        hz=float(f[idx]); peak=float(p[idx]);
        floorband=(np.abs(f-hz)>=7)&(np.abs(f-hz)<=55)
        if np.count_nonzero(floorband)<20: continue
        floor=float(np.median(p[floorband]))
        snr=10*np.log10((peak+1e-22)/(floor+1e-22))
        relative=10*np.log10((peak+1e-22)/(rms+1e-22))
        if snr<8 or relative < -106:
            continue
        half_results=[]
        for half in np.array_split(x,2):
            fh,ph=_psd(half,SAMPLE_RATE,5)
            near=np.where(np.abs(fh-hz)<2.7)[0]
            if not len(near): half_results.append(False);continue
            j=near[np.argmax(ph[near])]
            away=(np.abs(fh-fh[j])>=7)&(np.abs(fh-fh[j])<=55)
            if np.count_nonzero(away)<20: half_results.append(False);continue
            hsnr=10*np.log10((float(ph[j])+1e-22)/(float(np.median(ph[away]))+1e-22))
            hrelative=10*np.log10((float(ph[j])+1e-22)/(max(float(np.mean(half*half)),1e-20)+1e-22))
            half_results.append(bool(hsnr>=7.5 and hrelative>=-111))
        persistent=all(half_results)
        passed=bool(snr>=12 and relative>=-102 and persistent)
        tentative=bool(snr>=9 and relative>=-106 and sum(half_results)>=1)
        options.append({'freq':hz,'snr':float(snr),'relative':float(relative),
                        'persistent':persistent,'pass':passed,'tentative':tentative,
                        'offset':float(hz-target)})
    return max(options,key=lambda v:(v['pass'],v['tentative'],v['snr']),default=None)


def _spectrum_window(x, original_rate):
    channels=(x[:,0],x[:,1]); reports=[_mains_channel(ch) for ch in channels]
    electrical={}
    for base in (50,60):
        electrical[base]=max((r[base] for r in reports),
            key=lambda r:(r['count'],r['weak'],r['snr']))
    broadcast={}
    specs=(('FM stereo pilot',19000.0,25.0),
           ('625-line TV',15625.0,30.0),
           ('525-line TV',15734.26,30.0))
    for name,target,tol in specs:
        attempts=[_scan_broadcast_tone(ch,target,tol,original_rate) for ch in channels]
        broadcast[name]=max((m for m in attempts if m),
            key=lambda m:(m['pass'],m['tentative'],m['snr']),default=None)
    mono=np.mean(x,axis=1,dtype=np.float64)
    f,p=_psd(mono,SAMPLE_RATE,5)
    cutoff=None
    limit=min(20000, original_rate//2)
    if len(p) and float(np.max(p))>1e-19:
        reference=float(np.max(p))
        for hz in range(1000,int(limit),500):
            sel=(f>=hz)&(f<hz+500)
            if np.any(sel) and float(np.max(p[sel]))>reference*10**(-65/10):
                cutoff=hz+500
    return electrical,broadcast,cutoff


def _ndr_notch_window(audio, input_rate):
    """Search for a persistent narrow spectral *dip* around 10 kHz.

    A radio/transcription notch can shift by a few percent after cassette
    copying. This detector never treats a 10 kHz spectral *peak* as NDR.
    """
    if input_rate < 22500:
        return None
    mono=np.mean(audio.astype(np.float64),axis=1)
    fs=SAMPLE_RATE
    length=4*fs; frames=[]; freq=None
    for begin in range(0,len(mono)-length+1,length//2):
        chunk=mono[begin:begin+length]
        if np.sqrt(float(np.mean(chunk*chunk)))<.0005:continue
        f=np.fft.rfftfreq(length,1/fs)
        p=np.abs(np.fft.rfft(chunk*np.hanning(length)))**2
        band=(f>=9300)&(f<=10700)
        hz=f[band]
        logarithmic=10*np.log10(np.maximum(p[band],1e-20))
        baseline=ndimage.median_filter(logarithmic,size=321,mode='reflect')
        contrast=ndimage.uniform_filter1d(baseline-logarithmic,size=41)
        # Avoid interpreting a global high-frequency cutoff as a narrow notch.
        region=(hz>=9400)&(hz<=10600)
        baselevel=float(np.median(logarithmic[region]))
        if baselevel < -65:continue
        frames.append(contrast)
        freq=hz
    if len(frames)<3 or freq is None:return None
    values=np.asarray(frames)
    average=np.median(values,axis=0)
    search=(freq>=9650)&(freq<=10380)
    selections=np.where(search)[0]
    idx=selections[np.argmax(average[search])]
    hz=float(freq[idx]); depth=float(average[idx])
    occurrence=float(np.mean(values[:,idx]>=3))
    controls=average[((freq>=9350)&(freq<=9620)) | ((freq>=10420)&(freq<=10650))]
    control95=float(np.percentile(controls,95))
    # Require a localized, repeatable notch stronger than competing nearby dips.
    supported=(depth>=4.6 and depth-control95>=2.3 and occurrence>=.66)
    possible=(depth>=3.4 and depth-control95>=1.5 and occurrence>=.60)
    return {'freq':hz,'depth_db':depth,'occurrence':occurrence,
            'control95':control95,'frames':len(frames),
            'supported':supported,'possible':possible}

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


def _rotation_matches(times, target_period, relaxed=False):
    """Look for aligned *impulsive* clicks; relaxed matches stay tentative.

    A musical beat alone is not admissible: input times must already have passed
    the short-duration high-pass click filter. Require consecutive turns, a
    stable fitted period and reasonable coverage to reject accidental grids.
    """
    min_events = 6 if relaxed else 9
    if len(times) < min_events or len(times) > 230:
        return None
    speed_dev = .045 if relaxed else .025
    periods = [target_period]
    dt = times[:, None] - times[None, :]
    positive = dt[dt > .2]
    for mult in range(1, 14):
        candidates = positive / mult
        candidates = candidates[(candidates > target_period * (1-speed_dev)) &
                                (candidates < target_period * (1+speed_dev))]
        if candidates.size:
            hist, edges = np.histogram(candidates, bins=30,
                range=(target_period * (1-speed_dev), target_period * (1+speed_dev)))
            for idx in np.argsort(hist)[-3:]:
                if hist[idx] >= 2:
                    periods.append(float((edges[idx] + edges[idx+1])/2))
    best = None
    for period in sorted(set(round(p, 5) for p in periods)):
        tol = min(.031 if relaxed else .018, period * (.021 if relaxed else .012))
        for anchor in times:
            nturn = np.rint((times-anchor)/period).astype(int)
            residual = np.abs(times-(anchor+nturn*period))
            picked = residual < tol
            if picked.sum() < min_events:
                continue
            keep = {}
            for idx, t, err in zip(nturn[picked],times[picked],residual[picked]):
                if idx not in keep or err < keep[idx][1]:
                    keep[idx] = (float(t), float(err))
            if len(keep) < min_events:
                continue
            keys = np.array(sorted(keep))
            vals = np.array([keep[k][0] for k in keys])
            span = (keys[-1]-keys[0])*period
            coverage = len(keys)/(keys[-1]-keys[0]+1)
            neighbors = int(np.count_nonzero(np.diff(keys)==1))
            if span < (8 if relaxed else 15) or coverage < (.49 if relaxed else .60) or neighbors < (4 if relaxed else 7):
                continue
            slope, offset = np.polyfit(keys.astype(float),vals,1)
            if abs(slope-target_period) > target_period*speed_dev:
                continue
            fiterr = float(np.sqrt(np.mean((vals-(slope*keys+offset))**2)))
            if fiterr > (.020 if relaxed else .010):
                continue
            fraction = len(keys)/max(len(times),1)
            if fraction < (.13 if relaxed else .17):
                continue
            score = len(keys)*coverage/(1+fiterr*80)
            if best is None or score > best['score']:
                best = {'score':score,'events':len(keys),'pairs':neighbors,
                        'span':span,'period':float(slope), 'fit_ms':fiterr*1000,
                        'relaxed':relaxed}
    return best

def _vinyl_window(audio):
    records = {}
    for ch in range(2):
        times = _click_candidates(audio[:, ch].astype(float), SAMPLE_RATE)
        duration = len(audio) / SAMPLE_RATE
        if len(times) < 6 or len(times) > duration * 5.5:
            continue
        for rpm, period in ((33.333, 1.8), (45.0, 4/3), (78.0, 60/78)):
            strict = _rotation_matches(times, period, relaxed=False)
            evidence = strict or _rotation_matches(times, period, relaxed=True)
            if evidence and (rpm not in records or evidence['score'] > records[rpm]['score']):
                records[rpm] = evidence
    if not records:
        return None
    ranked = sorted(records.items(),key=lambda item:(not item[1]['relaxed'],item[1]['score']),reverse=True)
    if len(ranked)>1 and ranked[0][1]['relaxed']==ranked[1][1]['relaxed'] and ranked[0][1]['score'] < ranked[1][1]['score']*1.22:
        return None
    return {'rpm':ranked[0][0],**ranked[0][1]}

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
    hits=[w['vinyl'] for w in windows if w['vinyl']]
    if not hits:
        return verdict('No reliable RPM clue','Not detected',
            'No sufficiently repeatable, sharp click train aligned with 33⅓, 45 or 78 RPM. ' 
            'Random surface crackle can indicate a record without giving its speed.')
    # Strong matches outrank tentative matches; do not average distinct speeds.
    strict=[h for h in hits if not h.get('relaxed')]
    ranked_pool=strict if strict else hits
    totals={}
    for h in ranked_pool:
        totals[h['rpm']]=totals.get(h['rpm'],0)+h['score']
    ranked=sorted(totals.items(), key=lambda kv:kv[1],reverse=True)
    if len(ranked)>1 and ranked[0][1] < ranked[1][1]*1.24:
        return verdict('Possible turntable pattern','Tentative',
            'Several rotation speeds fit similarly. Short rhythmic musical sounds may be responsible.')
    rpm=ranked[0][0]
    matched=[h for h in ranked_pool if h['rpm']==rpm]
    events=max(h['events'] for h in matched)
    name=('33⅓' if abs(rpm-33.333)<.2 else f'{rpm:g}')
    label=f'Possible {name} RPM' if not strict else f'Likely {name} RPM'
    detail=(f'{events} short click events lined up near {name} RPM in '
            f'{len(matched)} analyzed section(s). '
            + ('This was a relaxed match; percussion or editing could mimic the timing.'
               if not strict else 'Multiple consecutive revolutions supported the match, but percussion can still imitate this.')
            + ' It identifies a possible record rotation in the copying chain, not the current file format.')
    return verdict(label,'Tentative' if not strict else 'Possible',detail)

def _consolidate_electrical(windows):
    """Report the best-supported family, including a transparent weak best guess."""
    candidates=[]
    for base in (50,60):
        sections=[w['mains'][base] for w in windows]
        rich=sum(s['count']>=2 for s in sections)
        mixed=sum(s['count']>=1 and s['count']+s['weak']>=2 for s in sections)
        singles=sum(s['count']>=1 for s in sections)
        weak=sum(s['weak']>=1 for s in sections)
        total=sum(2*s['count']+s['weak'] for s in sections)
        strength=sum(s['snr'] for s in sections)
        if rich>=2: level=3
        elif rich>=1 or mixed>=2: level=2
        elif mixed>=1 or singles>=2: level=1
        elif singles>=1 or weak>=2: level=.5
        else: level=0
        freqs=[float(f) for item in sections for _,f in item['freqs']]
        candidates.append({'base':base,'level':level,'total':total,'strength':strength,'freqs':freqs})
    ranked=sorted(candidates,key=lambda c:(c['level'],c['total'],c['strength']),reverse=True)
    top,rival=ranked
    if top['level']==0:
        return verdict('No clear mains hum','Not detected',
            'No sufficiently persistent narrowband 50/60 Hz line or harmonics were found.')
    base=top['base']
    ambiguous=(rival['level']>0 and top['level']-rival['level']<1
               and top['total']<=rival['total']+2)
    if ambiguous:
        # A stronger *stable fundamental* is meaningful even without harmonics.
        # Tie-breaking is speculative, so label as tentative rather than certain.
        if top['strength'] < rival['strength']*1.20:
            return verdict('Possible 50/60 Hz interference','Tentative',
                 'Both mains-frequency families show similar weak spectral lines. '
                 'The peaks could also be sustained musical notes, so no particular region is justified.')
    region='50 Hz region (Europe and others)' if base==50 else '60 Hz region (N. America and others)'
    certainty='Strong' if top['level']>=3 and rival['level']==0 else ('Possible' if top['level']>=2 and not ambiguous else 'Tentative')
    examples=', '.join(f'{f:.1f}' for f in list(dict.fromkeys(top['freqs']))[:5])
    if ambiguous:
        detail=(f'The {base} Hz candidate has stronger narrowband evidence than the '
                f'{rival["base"]} Hz candidate, although both occur in the file. ')
    else:
        detail=(f'Persistent frequency bands are compatible with {base} Hz power. ')
    detail+=f'Detected peaks include {examples} Hz. '
    if top['level']<2: detail+='Only a weak or isolated tone was supported, not a full harmonic family. '
    detail+='This indicates possible electrical interference somewhere in the recording chain, not the studio country.'
    return verdict(('Possible ' if certainty=='Tentative' else 'Likely ')+region,certainty,detail)

def _consolidate_broadcast(windows):
    labels={'FM stereo pilot':'FM radio pilot',
            '625-line TV':'PAL/SECAM-type TV interference',
            '525-line TV':'NTSC-type TV interference'}
    findings=[]
    for name in ('FM stereo pilot','625-line TV','525-line TV'):
        reports=[w['broadcast'].get(name) for w in windows]
        strong=[r for r in reports if r and r['pass']]
        weak=[r for r in reports if r and r.get('tentative')]
        if len(strong)>=2 or (len(windows)==1 and len(strong)==1): level=2
        elif strong or len(weak)>=2 or (len(windows)==1 and len(weak)==1):level=1
        else:continue
        evidence=strong if strong else weak
        best=max(evidence,key=lambda r:r['snr'])
        findings.append((name,level,len(strong),len(weak),best))
    if not findings:
        cutoff=max((w.get('cutoff') or 0) for w in windows)
        if not cutoff or cutoff<15000:
            return verdict('High-frequency signal unavailable','Not measurable',
                'This recording may be filtered below the frequencies needed to assess TV and FM pilot tones.')
        return verdict('No broadcast tones detected','Not detected',
            'No repeatable 15.625 kHz, 15.734 kHz or 19 kHz pilot/scan tone cleared the screening checks.')
    findings.sort(key=lambda t:(t[1],t[4]['snr']),reverse=True)
    best=findings[0]
    # Corroborated findings can coexist (radio broadcast played through a TV).
    strong=[f for f in findings if f[1]==2]
    selected=strong if strong else [best]
    names=' + '.join(labels[f[0]] for f in selected)
    details=[]
    for name,level,nstrong,nweak,meas in selected:
        details.append(f'{labels[name]}: a persistent narrow peak at {meas["freq"]:.1f} Hz '
                       f'({meas["snr"]:.0f} dB above neighbouring frequencies).')
    return verdict(('Likely ' if strong else 'Possible ')+names,
        'Possible' if strong else 'Tentative',
        ' '.join(details)+' This is a clue to equipment or later copying, not proof of the original studio country.')


def _consolidate_ndr(windows):
    entries=[w.get('ndr') for w in windows]
    strong=[r for r in entries if r and r['supported']]
    possible=[r for r in entries if r and r['possible']]
    if not strong and not possible:
        available=any(r for r in entries)
        return verdict('No NDR-style notch found' if available else 'Not measurable',
            'Not detected' if available else 'Not measurable',
            'No consistently narrow dip close to 10 kHz was supported in the sampled audio.'
            if available else 'Too little audible high-frequency material was available to test the 10 kHz dip.')
    selected=strong if strong else possible
    best=max(selected,key=lambda v:v['depth_db'])
    return verdict('Possible NDR-style 10 kHz dip',
        'Possible' if strong else 'Tentative',
        f'A narrow dip centered near {best["freq"]:.0f} Hz is approximately '
        f'{best["depth_db"]:.1f} dB below neighbouring audio and appears in '
        f'{best["occurrence"]:.0%} of examined frames. Similar dips occurred on '
        'some 1980s NDR broadcasts; other audio filters can produce them too. '
        'Not proof this recording aired on NDR.')

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
        raise ValueError("Upload MP3, MPEG audio, WAV, FLAC, OGG or M4A audio.")
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
                         "pilot_jitter":pilot_jitter, "stereo_corr":stereo_corr,
                         "ndr":_ndr_notch_window(audio, metadata["input_rate"])})
        analyzed_seconds += len(audio)/SAMPLE_RATE
        del audio # Avoid keeping 100+ MB of decoded audio in RAM.
    if not analyzed:
        raise ValueError("The audio was silent or too faint to analyze.")
    rotation = _consolidate_vinyl(analyzed)
    surface = _consolidate_surface(analyzed)
    electrical = _consolidate_electrical(analyzed)
    broadcast = _consolidate_broadcast(analyzed)
    ndr = _consolidate_ndr(analyzed)
    diag = _diagnostics(analyzed)
    fm = 'FM radio pilot' in broadcast['result'] and broadcast['certainty'] in {'Possible','Tentative'}
    ntsc = 'NTSC-type TV' in broadcast['result'] and broadcast['certainty'] in {'Possible','Tentative'}
    disc = rotation['certainty'] in {'Possible','Tentative'} or surface['result']=='Disc surface noise likely'
    surface_hint = surface['certainty'] in ('Possible','Tentative')
    interruptions = diag['possible_interruptions']
    if disc:
        prefix = 'Likely record (vinyl/shellac)' if surface['result']=='Disc surface noise likely' or rotation['certainty']=='Possible' else 'Possible record (vinyl/shellac)'
        reason = ('Irregular high-frequency crackle and pops suggest a physical disc somewhere in the transfer chain. '
                  if surface_hint else 'Repeated click timings suggest a rotating disc. ')
        source = verdict(prefix,'Possible' if prefix.startswith('Likely') else 'Tentative',
                         reason + (rotation['detail'] if rotation['certainty'] in {'Possible','Tentative'} else surface['detail']))
    elif fm:
        source = verdict('Likely FM radio recording','Possible',broadcast['detail'])
    elif ntsc:
        source = verdict('Possible TV / monitor recording','Tentative',
            'A detectable NTSC-type line-frequency tone suggests audio passed near a television or monitor. '
            'It does not establish where the song was originally recorded.')
    elif ndr['certainty'] in ('Possible','Tentative'):
        source = verdict('Possible radio / cassette transfer','Tentative',ndr['detail'])
    elif interruptions >= 2:
        source = verdict('Possible cassette / tape','Tentative',
            f'{interruptions} short dropouts were found. Tape wear is one possibility, '
            'but digital glitches can also cause dropouts.')
    elif surface_hint:
        source = verdict('Possible record (vinyl/shellac)','Tentative',surface['detail'])
    else:
        source = verdict('Source uncertain','Not measurable',
            'No distinctive source artifacts were found. A clean record, cassette and digital source can sound similar.')
    stereo = _stereo_format(analyzed, metadata['channels'])
    if disc:
        medium=verdict('Disc transfer clues','Possible',source['detail'])
    elif fm or ntsc or ndr['certainty'] in ('Possible','Tentative'):
        medium=verdict('Broadcast or transfer clues','Tentative',broadcast['detail'])
    else:
        medium=verdict('No distinctive analog-medium clue','Not measurable','No clear medium-specific signal.')
    dropout=(verdict(f'{interruptions} brief interruptions','Tentative',
                    'Sudden short level losses; not unique to magnetic tape.')
             if interruptions else verdict('None found','Not detected','No brief near-silent interruptions.'))
    cutoff=diag['spectral_upper_energy_khz']
    bandwidth=(verdict(f'Audio extends to ~{cutoff:g} kHz','High',
                 'This describes the file, not the original studio recording.')
               if cutoff is not None else verdict('Unclear','Not measurable','No usable spectrum.'))
    rows=[
        ('Likely audio source',source),
        ('Vinyl rotation',rotation),
        ('Likely power system',electrical),
        ('Radio / TV signals',broadcast),
        ('NDR-style 10 kHz dip',ndr),
        ('Disc surface noise',surface),
        ('Recording-medium clues',medium),
        ('Possible tape dropouts',dropout),
        ('Playback speed',verdict('No reliable reference','Not measurable',
            'The recording cannot be judged uniformly fast or slow without a trustworthy speed reference.')),
        ('Audio bandwidth',bandwidth),
        ('Stereo format',stereo),
    ]
    metadata["analyzed_seconds"] = round(analyzed_seconds, 1)
    metadata["diagnostics"] = diag
    return rows, metadata

def analyze(data: bytes, filename: str):
    """Bytes-oriented API wrapper; temporary file is always removed."""
    ext = Path(filename).suffix.lower()
    if ext not in EXTENSIONS:
        raise ValueError("Upload MP3, MPEG audio, WAV, FLAC, OGG or M4A audio.")
    if len(data) > MAX_BYTES:
        raise ValueError("Maximum file size is 100 MB.")
    with tempfile.TemporaryDirectory(prefix="audiocheck_") as tempdir:
        path = Path(tempdir) / ("upload" + ext)
        path.write_bytes(data)
        return analyze_path(path, filename)
