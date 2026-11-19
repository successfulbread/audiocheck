"""Real, zoomed spectral evidence images for AudioCheck.

Figures are rendered from *decoded user audio*, not synthesised diagrams.
Harmonic/TV/FM target markings are reference guides, NEVER detections.
The core audio classifier lives in analyzer.py; these plots do not affect scores.
"""
from __future__ import annotations

import base64
from io import BytesIO
import math

import numpy as np
from scipy import signal
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg

AUDIO_RATE = 44100
PREVIEW_SECONDS = 18

PAPER = '#ffffff'
INK = '#14243d'
MUTED = '#53647a'
GUIDE = '#ff5d73'


def _line_contrast(y, fs, target):
    """Simple local, relative prominence for DISPLAY-channel selection only."""
    if not len(y) or fs <= 2 * (target + 12):
        return -999.0
    nper = min(len(y), max(2048, int(fs * 2)))
    f, p = signal.welch(y.astype(np.float64), fs=fs, nperseg=nper)
    near = abs(f - target) < 2.5
    flank = (abs(f - target) >= 5) & (abs(f - target) <= 16)
    if not np.any(near) or not np.any(flank):
        return -999.0
    peak = float(np.max(p[near])); floor = float(np.median(p[flank]))
    # Avoid inflating empty/silent bands during channel selection.
    if peak < 1e-21:
        return -999.0
    return 10 * math.log10((peak + 1e-24) / (floor + 1e-24))


def _pick_channel(audio, target, mode):
    """Pick L or R by local evidence, since opposite-phase hum can cancel in mono."""
    if audio.ndim == 1:
        return np.asarray(audio, dtype=np.float64), 'Mono'
    if mode == 'ndr':
        # The 10 kHz notch classifier uses the mono mix; show that same mix.
        return np.mean(audio.astype(np.float64), axis=1), 'L+R mix'
    left = audio[:, 0].astype(np.float64)
    right = audio[:, 1].astype(np.float64)
    fl = _line_contrast(left, AUDIO_RATE, target)
    fr = _line_contrast(right, AUDIO_RATE, target)
    return (right, 'Right') if fr > fl + 0.3 else (left, 'Left')


def _stft(y, fs, nperseg):
    y = np.asarray(y, dtype=np.float64)
    y = signal.detrend(y, type='constant')
    nperseg = min(int(nperseg), len(y))
    if nperseg < 512:
        raise ValueError('Not enough audio for a spectrogram.')
    hop = max(1, nperseg // 8)
    f, t, z = signal.stft(y, fs=fs, window='hamming',
                          nperseg=nperseg, noverlap=nperseg-hop,
                          boundary=None, padded=False)
    return f, t, 20 * np.log10(np.maximum(np.abs(z), 1e-12))


def _plot_panel(fig, ax, f, t, db, low, high, guides, title, show_xlabel=True):
    mask = (f >= low) & (f <= high)
    if np.count_nonzero(mask) < 5:
        raise ValueError('Input has insufficient frequency resolution.')
    band = db[mask]
    # Relative scale within the *entire selected frequency band*. Never normalize
    # each frequency row: doing so would fabricate strong horizontal streaks.
    top = float(np.percentile(band, 99.5))
    mapped = np.clip(band - top, -62, 8)
    # Spectrogram: x=time, y=frequency. Horizontal bright streaks are actual energy.
    ax.pcolormesh(t, f[mask], mapped, shading='nearest', cmap='viridis',
                  vmin=-62, vmax=8, rasterized=True)
    for hz, label in guides:
        if low <= hz <= high:
            ax.axhline(hz, lw=1.1, ls=(0,(4,4)), color=GUIDE, alpha=.9)
            ax.annotate(label, (t[0], hz), xytext=(4, 3), textcoords='offset points',
                        va='bottom', fontsize=8.5, weight='bold', color='#db415d')
    ax.set_ylim(low, high)
    ax.set_xlim(t[0], t[-1])
    ax.set_title(title, fontsize=11, fontweight='bold', color=INK, loc='left', pad=7)
    ax.set_ylabel('Frequency (Hz)', fontsize=9, color=MUTED)
    if show_xlabel:
        ax.set_xlabel('Seconds into excerpt', fontsize=9, color=MUTED)
    else:
        ax.set_xticklabels([])
    ax.tick_params(colors=MUTED, labelsize=9)
    ax.grid(False)
    for side in ax.spines.values():
        side.set_color('#CBD7E5')
    ax.set_facecolor('#f6f8fe')


def _figure_bytes(fig):
    output = BytesIO()
    FigureCanvasAgg(fig).print_png(output)
    return output.getvalue()


def render_evidence(audio, kind, start_seconds=0.0, original_rate=44100, target=None):
    """Return a PNG and truthful caption for one *real* audio excerpt.

    kind: mains | tv | fm | ndr. Guide lines denote expected frequencies.
    Uses a high-order Hamming STFT (ENF recommendations); plots are visual
    evidence only and never silently change detector verdicts.
    """
    audio = np.asarray(audio)
    if audio.ndim not in (1,2) or len(audio) < AUDIO_RATE * 5:
        raise ValueError('At least five seconds of decoded audio are needed.')
    original_rate = int(original_rate)
    if kind == 'tv' and original_rate < 31700:
        raise ValueError('The original file cannot preserve the TV scan frequencies.')
    if kind == 'fm' and original_rate < 38200:
        raise ValueError('The original file cannot preserve the 19 kHz FM pilot.')
    if kind == 'ndr' and original_rate < 22500:
        raise ValueError('The original file has insufficient high-frequency bandwidth.')
    specs = {
        'mains': (60, [(40,70,[(50,'50 Hz'),(60,'60 Hz')], '50 / 60 Hz fundamentals'),
                        (94,128,[(100,'100 Hz'),(120,'120 Hz')], 'Electrical harmonics')]),
        'tv': (15734.26, [(15550,15800,[(15625,'625-line TV'),(15734.26,'525-line TV')], 'Historical TV scanning tones')]),
        'fm': (19000, [(18910,19090,[(19000,'FM pilot')], '19 kHz FM pilot')]),
        'ndr': (10000, [(9450,10550,[(10000,'10 kHz')], 'The NDR-style notch (a DARK dip)')]),
    }
    if kind not in specs:
        raise ValueError('Unsupported spectrogram type.')
    expected, ranges = specs[kind]
    if target is not None and math.isfinite(float(target)):
        expected = float(target)
    y, channel = _pick_channel(audio, expected, kind)
    if kind == 'mains':
        y = signal.resample_poly(y, 20, 441)
        fs = 2000
        f, t, db = _stft(y, fs, 6 * fs)  # .167 Hz bins; ~1s movement
    else:
        fs = AUDIO_RATE
        f, t, db = _stft(y, fs, 16384)  # 2.69 Hz bins, preserves narrow 10 kHz dip
    if kind == 'mains':
        fig = Figure(figsize=(8.6, 5.4), dpi=115, facecolor=PAPER)
        axes = fig.subplots(nrows=2, ncols=1)
        for i, (ax,(lo,hi,guides,title)) in enumerate(zip(axes,ranges)):
            _plot_panel(fig,ax,f,t,db,lo,hi,guides,title,show_xlabel=(i==len(ranges)-1))
        fig.subplots_adjust(left=.12,right=.97,top=.91,bottom=.12,hspace=.38)
    else:
        fig = Figure(figsize=(8.6,4.45), dpi=115, facecolor=PAPER)
        gs = fig.add_gridspec(2,1,height_ratios=[2.35,1],hspace=.52,
                              left=.12,right=.97,top=.89,bottom=.16)
        ax = fig.add_subplot(gs[0]); profile = fig.add_subplot(gs[1])
        lo,hi,guides,title = ranges[0]
        _plot_panel(fig,ax,f,t,db,lo,hi,guides,title,show_xlabel=False)
        band = (f>=lo)&(f<=hi)
        # Median spectral level from the actual time slices; useful for verifying
        # a positive peak (TV / FM) or negative notch (NDR).
        median_db = np.median(db[band],axis=1)
        profile.plot(f[band],median_db, color='#087e9e',lw=1.6)
        for hz,label in guides:
            profile.axvline(hz, ls=(0,(4,4)),color=GUIDE,lw=1,alpha=.9)
        profile.set_xlim(lo,hi)
        profile.set_ylabel('Level (dB)',fontsize=9,color=MUTED)
        profile.set_xlabel('Frequency (Hz)',fontsize=9,color=MUTED)
        profile.tick_params(colors=MUTED,labelsize=8)
        profile.set_facecolor('#f6f8fe')
        for side in profile.spines.values():side.set_color('#CBD7E5')
    duration = len(audio)/AUDIO_RATE
    cap = f'Real audio: {start_seconds:.0f}-{start_seconds+duration:.0f}s · {channel}. '
    cap += ('Bright streak = sound at that frequency. '
            if kind != 'ndr' else 'A dark horizontal gap near 10 kHz would be the notch. ')
    cap += 'Dashed = guide only. Colours show relative strength.'
    return {'png':_figure_bytes(fig), 'caption':cap,
            'section_start_s':float(start_seconds),'section_duration_s':float(duration),
            'channel':channel,'kind':kind}


def _window_score(section,kind,target):
    if kind=='mains':
        power = section.get('mains',{})
        freqs=[50,60] if target is None else [int(target)]
        return max((10*power.get(b,{}).get('count',0)+
                    3*power.get(b,{}).get('weak',0)+
                    power.get(b,{}).get('snr',0)/20 for b in freqs),default=0)
    if kind in ('tv','fm'):
        keys={'tv':['525-line TV','625-line TV'],'fm':['FM stereo pilot']}[kind]
        b=section.get('broadcast',{})
        return max(((100 if b[k].get('pass') else 20 if b[k].get('tentative') else 0)
                     + b[k].get('snr',0) for k in keys if b.get(k)),default=0)
    if kind=='ndr':
        ndr=section.get('ndr') or {}
        return (30 if ndr.get('supported') else 10 if ndr.get('possible') else 0)+ndr.get('depth_db',0)
    return 0


def make_evidence_charts(sections, findings, original_rate):
    """Produce small base64 PNG snippets for the relevant result cards.

    sections holds <=4 bounded excerpts from *this upload*. No audio is returned
    to session state, only the charts. Missing/unsupported bands are omitted.
    """
    if not sections:
        return {}
    charts={}
    result=dict(findings)
    kinds=[('Likely power system','mains'),('Radio / TV signals','tv'),('NDR-style 10 kHz dip','ndr')]
    broadcast=str((result.get('Radio / TV signals') or {}).get('result',''))
    # FM has its own 19 kHz view when the analyzer has suggested an FM pilot.
    if 'FM' in broadcast.upper() and original_rate>=38200:
        kinds.insert(2,('Radio / TV signals','fm'))
    power_result=str((result.get('Likely power system') or {}).get('result',''))
    base = 50 if '50 Hz' in power_result else 60 if '60 Hz' in power_result else None
    for key,kind in kinds:
        if kind=='tv' and original_rate<31700:continue
        if kind=='ndr' and original_rate<22500:continue
        try:
            section=max(sections,key=lambda s:_window_score(s,kind,base))
            target = float(base) if kind=='mains' and base else None
            plot=render_evidence(section['audio'],kind,section['start'],original_rate,target=target)
            image_data = base64.b64encode(plot['png']).decode('ascii')
            charts.setdefault(key,[]).append({'image_base64':image_data,'caption':plot['caption'],
                                               'kind':kind,'start':plot['section_start_s']})
        except (ValueError,RuntimeError,MemoryError):
            # A missing chart must never fail a real analysis.
            continue
    return charts
