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
from scipy import signal, ndimage
from matplotlib.figure import Figure
from matplotlib.patches import Rectangle
from matplotlib.backends.backend_agg import FigureCanvasAgg

AUDIO_RATE = 44100
PREVIEW_SECONDS = 18

PAPER = '#FFFFFF'
INK = '#14243d'
MUTED = '#53647a'
GUIDE = '#25F4DE'


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
    # A single contrast scale for the WHOLE frequency/time panel (not per row).
    # Automatic levels make weak real peaks visible without drawing false lines.
    # Never apply spectral whitening or normalize each frequency independently:
    # that would manufacture horizontal streaks that were not actually measured.
    high_db = float(np.percentile(band, 99.8))
    background_db = float(np.percentile(band, 12.0))
    dynamic_range = float(np.clip(high_db - background_db, 30.0, 65.0))
    low_db = high_db - dynamic_range
    # Inferno: low energy nearly black, strong energy bright yellow/orange.
    # Plot the actual dB matrix; colour mapping only adjusts its display range.
    ax.pcolormesh(t, f[mask], band, shading='nearest', cmap='inferno',
                  vmin=low_db, vmax=high_db, rasterized=True)
    # Reference positions belong in the margin, not on the spectrogram:
    # a dashed full-width guide could hide or imitate the very tone being tested.
    reference = [(hz, label) for hz, label in guides if low <= hz <= high]
    if reference:
        right_axis = ax.secondary_yaxis('right')
        right_axis.set_yticks([hz for hz, _ in reference],
                             labels=[f'{label} ref' for _, label in reference])
        right_axis.tick_params(axis='y', which='major', colors='#007C88',
                               length=6, width=1.6, labelsize=8, pad=6)
        right_axis.spines['right'].set_color('#007C88')
        right_axis.spines['right'].set_linewidth(1.5)
    ax.set_ylim(low, high)
    ax.set_xlim(t[0]-.5, t[-1]+.5) if len(t)==1 else ax.set_xlim(t[0], t[-1])
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
    ax.set_facecolor('#060914')


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
        f, t, db = _stft(y, fs, min(6 * fs, max(2 * fs, len(y) // 2)))  # .167-.5 Hz bins
    else:
        fs = AUDIO_RATE
        f, t, db = _stft(y, fs, 16384)  # 2.69 Hz bins, preserves narrow 10 kHz dip
    if kind == 'mains':
        fig = Figure(figsize=(8.6, 5.4), dpi=115, facecolor=PAPER)
        axes = fig.subplots(nrows=2, ncols=1)
        for i, (ax,(lo,hi,guides,title)) in enumerate(zip(axes,ranges)):
            _plot_panel(fig,ax,f,t,db,lo,hi,guides,title,show_xlabel=(i==len(ranges)-1))
        fig.subplots_adjust(left=.12,right=.79,top=.91,bottom=.12,hspace=.38)
    else:
        fig = Figure(figsize=(8.6,4.45), dpi=115, facecolor=PAPER)
        gs = fig.add_gridspec(2,1,height_ratios=[2.35,1],hspace=.52,
                              left=.12,right=.80,top=.89,bottom=.19)
        ax = fig.add_subplot(gs[0]); profile = fig.add_subplot(gs[1])
        lo,hi,guides,title = ranges[0]
        _plot_panel(fig,ax,f,t,db,lo,hi,guides,title,show_xlabel=False)
        band = (f>=lo)&(f<=hi)
        # Median spectral level from the actual time slices; useful for verifying
        # a positive peak (TV / FM) or negative notch (NDR).
        median_db = np.median(db[band],axis=1)
        profile.plot(f[band],median_db, color='#F0A000',lw=2.1)
        # The profile has reference tick labels beneath the curve, not
        # vertical lines that could visually manufacture a spectral peak.
        tick_values = sorted(set([lo, hi] + [hz for hz, _ in guides]))
        profile.set_xticks(tick_values)
        profile.set_xticklabels([f'{hz:,.0f}' for hz in tick_values])
        for tick, hz in zip(profile.get_xticklabels(), tick_values):
            tick.set_color('#007C88' if any(abs(hz-g)<1e-6 for g,_ in guides) else MUTED)
            tick.set_fontweight('bold' if any(abs(hz-g)<1e-6 for g,_ in guides) else 'normal')
        profile.set_xlim(lo,hi)
        profile.set_ylabel('Level (dB)',fontsize=9,color=MUTED)
        profile.set_xlabel('Frequency (Hz)',fontsize=9,color=MUTED)
        profile.tick_params(colors=MUTED,labelsize=8)
        profile.set_facecolor('#F8FAFF')
        for side in profile.spines.values():side.set_color('#CBD7E5')
    duration = len(audio)/AUDIO_RATE
    cap = f'Real audio: {start_seconds:.0f}-{start_seconds+duration:.0f}s · {channel}. '
    cap += ('Bright streak = sound at that frequency. '
            if kind != 'ndr' else 'A dark horizontal gap near 10 kHz would be the notch. ')
    cap += 'Yellow/orange = stronger; dark purple/black = weaker. Turquoise reference ticks are outside the signal plot, not detected lines.'
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




def render_peak_evidence(audio, kind, start_seconds=0.0, original_rate=44100,
                         target=None, mark_peak=True, notch_info=None):
    """Plot frequency-spectrum *peaks/troughs*, not time-frequency heatmaps.

    Signal strength is actual median Welch PSD; guides appear as text/x-axis
    labels outside the trace. A highest bin is not labelled a detection.
    """
    audio=np.asarray(audio)
    if audio.ndim not in (1,2) or len(audio)<AUDIO_RATE*5:
        raise ValueError('At least five seconds of real audio are needed.')
    specs={
        'mains':[(42,69,'50 / 60 Hz fundamentals',[(50,'50 Hz'),(60,'60 Hz')]),
                 (94,128,'100 / 120 Hz harmonics',[(100,'100 Hz'),(120,'120 Hz')])],
        'tv':[(15495,15855,'525- / 625-line scanning tone',[(15625,'625-line'),(15734.26,'525-line')])],
        'fm':[(18775,19225,'19,000 Hz FM-stereo pilot',[(19000,'FM pilot')])],
        'ndr':[(9280,10720,'10 kHz broadcast-filter dip — look for a trough',[(10000,'10 kHz')])],
    }
    if kind not in specs: raise ValueError('Unsupported peak-plot type.')
    if kind=='tv' and original_rate < 31700:
        raise ValueError('The source rate cannot preserve the TV band.')
    if kind=='fm' and original_rate < 38470:
        raise ValueError('The source rate cannot preserve the full FM pilot band.')
    if kind=='ndr' and original_rate < 22500:
        raise ValueError('The source rate cannot preserve the notch band.')
    selected=float(target) if target is not None else {'mains':60,'tv':15734.26,'fm':19000,'ndr':10000}[kind]
    y,channel=_pick_channel(audio,selected,kind)
    if kind=='mains':
        y=signal.resample_poly(y,20,441);fs=2000;window=min(len(y),12000)
        oversample=1
    else:
        fs=AUDIO_RATE
        window=min(len(y),16384 if kind=='ndr' else 65536)
        oversample=1 if kind=='ndr' else 2
    freq,power=signal.welch(y,fs=fs,nperseg=window,noverlap=window//2,
                            nfft=window*oversample,window='hann',
                            scaling='density' if kind=='ndr' else 'spectrum',average='median')
    db=10*np.log10(np.maximum(power,1e-24))
    ranges=specs[kind]
    rows=len(ranges)
    fig=Figure(figsize=(8.7,3.8 if rows==1 else 5.7),dpi=112,facecolor=PAPER)
    axes=fig.subplots(rows,1)
    if rows==1: axes=[axes]
    boxed=[]
    for ax,(lo,hi,title,guides) in zip(axes,ranges):
        mask=(freq>=lo)&(freq<=hi)
        ff=freq[mask]; vv=db[mask]
        if len(ff)<5: raise ValueError('Insufficient spectral resolution.')
        line='#157DC6' if kind!='ndr' else '#853DB4'
        if kind=='ndr':
            # The analysis itself smooths a median Welch spectrum over 6 Hz.
            # Plot this shape instead of misleading isolated low FFT bins.
            vv=ndimage.gaussian_filter1d(vv,6/max(float(ff[1]-ff[0]),.01))
        # Levels remain unwhitened: no per-frequency gain that could invent a peak.
        ax.plot(ff,vv,lw=2.2 if kind=='ndr' else 1.7,color=line)
        bottom=max(float(np.percentile(vv,3))-3,float(np.max(vv))-88)
        ceiling=float(np.max(vv))+7
        ax.fill_between(ff,vv,bottom,color=line,alpha=.09)
        ax.set_xlim(lo,hi);ax.set_ylim(bottom,ceiling)
        ax.set_ylabel('Level (dB)',fontsize=9,color=MUTED)
        ax.set_title(title,loc='left',fontsize=11,fontweight='bold',color=INK,pad=9)
        ax.set_xlabel('Frequency (Hz)',fontsize=9,color=MUTED)
        ax.tick_params(colors=MUTED,labelsize=8)
        ax.set_facecolor('#F8FAFF')
        for side in ax.spines.values():side.set_color('#CBD7E5')
        # These reference frequencies are only labelled *below* the curve.
        ticks=[lo]+[hz for hz,_ in guides]+[hi]
        ax.set_xticks(ticks)
        ax.set_xticklabels([f'{hz:,.0f}' for hz in ticks])
        for txt,hz in zip(ax.get_xticklabels(),ticks):
            if any(abs(hz-r)<.001 for r,_ in guides):
                txt.set_color('#007C88');txt.set_fontweight('bold')
        # Outline the actual peak or trough with an UNFILLED rectangle.
        # No vertical or horizontal guide is drawn across the measured trace.
        # Only mark peaks when the independent detector supports that signal.
        if mark_peak:
            measured = None
            if kind == 'ndr':
                measured=(notch_info or {}).get('freq')
                if isinstance(measured,(int,float)) and lo <= measured <= hi:
                    amplitude=float(np.interp(measured,ff,vv))
                    width=max(35., 2.2*float((notch_info or {}).get('width_hz',20) or 20))
                    height=12.0
                    ymin=amplitude-3.5
                else:
                    measured=None
            else:
                # Don't put the frame around an unrelated louder musical peak:
                # restrict the search to the expected, independently detected
                # 50/60, 100/120, TV scanning, or FM pilot neighbourhood.
                if kind=='mains':
                    desired=(float(selected)*2 if lo>=90 else float(selected))
                    tolerance=2.5 if lo>=90 else 1.7
                    width=5.0 if lo>=90 else 3.5
                elif kind=='tv':
                    desired=float(selected)
                    tolerance=35.0
                    width=28.0
                else:
                    desired=19000.0
                    tolerance=180.0
                    width=46.0
                near=np.where(np.abs(ff-desired)<=tolerance)[0]
                if len(near):
                    i=int(near[np.argmax(vv[near])])
                    measured=float(ff[i]);amplitude=float(vv[i])
                    height=11.0
                    ymin=amplitude-6.0
            if isinstance(measured,(int,float)) and np.isfinite(measured):
                width=float(min(width,hi-lo))
                left=max(lo,min(float(measured)-width/2,hi-width))
                ymin=max(bottom+1,min(float(ymin),ceiling-height-1))
                ax.add_patch(Rectangle((left,ymin),width,height,
                         fill=False,linewidth=1.75,edgecolor='#DE7B15',
                         zorder=8,clip_on=True,joinstyle='round'))
                # The frequency is reported in the caption rather than
                # printed on top of the measured line.
                boxed.append((title,float(measured)))
    fig.subplots_adjust(left=.12,right=.96,bottom=.20 if rows==1 else .13,
                        top=.86 if rows==1 else .92,hspace=.53)
    duration=len(audio)/AUDIO_RATE
    highlights=', '.join(f'{label}: {hz:,.1f} Hz' for label,hz in boxed)
    if kind=='ndr':
        mark_note=('Amber outline encloses the measured repeated trough; '+highlights+'. '
                   if boxed else 'No confirmed repeatable notch is outlined in this excerpt. ')
        mark_note+='Purple curve shows actual average sound energy by frequency; lower means quieter. '
    else:
        mark_note=('Amber outline encloses the detector-supported measured peak(s): '+highlights+'. '
                   if boxed else 'No frequency was highlighted because the detector did not confirm a peak. ')
    caption=(f'Real audio measured at {start_seconds:.0f}–{start_seconds+duration:.0f} s ({channel}). '
             +mark_note+
             ('The 10,000 Hz tick is a reference only; analog playback speed can shift the actual dip.'
              if kind=='ndr' else 'Reference ticks below the curve are expected frequencies, not detections.'))
    return {'png':_figure_bytes(fig),'caption':caption,'kind':kind,
            'channel':channel,'section_start_s':start_seconds}


def render_phase_evidence(audio):
    """Plot actual normalized cross-correlation at +/-4ms."""
    if audio.ndim!=2 or audio.shape[1]!=2:
        raise ValueError('Two channels are required.')
    x=np.asarray(audio[:AUDIO_RATE*8],float)
    aa=signal.resample_poly(x[:,0],1,4)
    bb=signal.resample_poly(x[:,1],1,4)
    fs=AUDIO_RATE/4
    sos=signal.butter(3,[150,4500],fs=fs,btype='bandpass',output='sos')
    aa=signal.sosfiltfilt(sos,aa);bb=signal.sosfiltfilt(sos,bb)
    aa-=aa.mean();bb-=bb.mean()
    norm=float(np.linalg.norm(aa)*np.linalg.norm(bb))
    if norm<1e-10:raise ValueError('Insufficient shared audio')
    m=int(fs*.004)
    correlation=signal.correlate(aa,bb,mode='full',method='fft')
    middle=len(bb)-1
    curve=correlation[middle-m:middle+m+1]/norm
    lags=np.arange(-m,m+1)/fs*1000
    best=int(np.argmax(abs(curve)))
    fig=Figure(figsize=(8.7,3.3),dpi=112,facecolor=PAPER)
    ax=fig.subplots()
    ax.plot(lags,curve,color='#157DC6',lw=1.6)
    ax.scatter([lags[best]],[curve[best]],color='#EC8B20',s=38,zorder=4)
    ax.set(xlim=(-4,4),ylim=(-1.08,1.08))
    ax.set_xlabel('Left relative to right — alignment lag (ms)',color=MUTED)
    ax.set_ylabel('Cross-correlation',color=MUTED)
    ax.set_title('Stereo alignment peak',loc='left',color=INK,fontweight='bold')
    ax.tick_params(colors=MUTED)
    fig.subplots_adjust(left=.13,right=.97,top=.86,bottom=.21)
    return {'png':_figure_bytes(fig),'caption':
             f'Actual channel cross-correlation. Strongest absolute peak: {lags[best]:+.3f} ms, r={curve[best]:+.3f}. '
             'Off-zero peak can indicate an interchannel delay, not necessarily a tape transfer.'}


def render_wow_evidence(track):
    seconds=np.asarray(track.get('curve_seconds',[]),float)
    cents=np.asarray(track.get('curve_cents',[]),float)
    frequencies=np.asarray(track.get('mod_freq_hz',[]),float)
    levels=np.asarray(track.get('mod_power_db',[]),float)
    if len(seconds)<20: raise ValueError('No stable reference-tone track.')
    fig=Figure(figsize=(8.7,4.5),dpi=112,facecolor=PAPER)
    top,bottom=fig.subplots(2,1,gridspec_kw={'height_ratios':[1.6,1]})
    top.plot(seconds,cents,color='#167BC0',lw=1.4)
    top.set_ylabel('Pitch shift (cents)',color=MUTED)
    top.set_xlabel('Seconds in tracked excerpt',color=MUTED)
    top.set_title('Measured reference-tone pitch variation',loc='left',fontweight='bold',color=INK)
    if len(frequencies)>3:
        bottom.plot(frequencies,levels,color='#A14BA2',lw=1.7)
        bottom.set_xlim(.3,30)
        bottom.set_ylabel('Power (dB)',color=MUTED)
        bottom.set_xlabel('Fluctuation rate (Hz)',color=MUTED)
    for ax in (top,bottom):
        ax.tick_params(colors=MUTED,labelsize=8)
        for side in ax.spines.values():side.set_color('#CBD7E5')
        ax.set_facecolor('#F8FAFF')
    fig.subplots_adjust(left=.14,right=.96,bottom=.15,top=.90,hspace=.64)
    return {'png':_figure_bytes(fig),
            'caption':f'Actual reference-tone pitch trace ({track["nominal_hz"]:,.2f} Hz nominal) and measured modulation-power peaks. A peak is not proof of any particular transport.'}


def render_tuning_evidence(tuning):
    m=tuning.get('metrics') or {}
    bins=np.asarray(m.get('bins_cents',[]),float)
    counts=np.asarray(m.get('offsets_cents',[]),float)
    if len(bins)<10 or len(counts)!=len(bins):raise ValueError('No tuning votes.')
    fig=Figure(figsize=(8.7,3.25),dpi=112,facecolor=PAPER)
    ax=fig.subplots()
    ax.bar(bins,counts,width=4.5,color='#2384C7',edgecolor='white',linewidth=.3)
    ax.set_xlim(-50,50)
    ax.set_title('Pitched spectral-peak votes relative to A440',loc='left',fontweight='bold',color=INK)
    ax.set_xlabel('Cents below / above equal-tempered note',color=MUTED)
    ax.set_ylabel('Peak votes',color=MUTED)
    ax.tick_params(colors=MUTED,labelsize=8)
    ax.set_xticks([-50,-25,0,25,50]);ax.set_facecolor('#F8FAFF')
    fig.subplots_adjust(left=.13,right=.97,top=.86,bottom=.25)
    return {'png':_figure_bytes(fig),
            'caption':'Votes from real detected pitched spectral peaks. Clustered tuning does not establish a playback-speed error; other temperament and instrument harmonics can bias this estimate.'}


def make_evidence_charts(sections, findings, original_rate):
    """Default to spectra showing actual measured peaks, not spectrogram heatmaps.

    Normal metadata still uses the existing 'spectrograms' key for backwards
    compatibility with the Streamlit UI. No audio bytes are retained.
    """
    if not sections:return {}
    charts={}
    result=dict(findings)
    kinds=[('Likely power system','mains'),('Radio / TV signals','tv'),
           ('NDR-style 10 kHz dip','ndr')]
    pilot=result.get('FM stereo pilot') or {}
    broadcast=str((result.get('Radio / TV signals') or {}).get('result',''))
    if original_rate>=38470 and pilot:
        kinds.append(('FM stereo pilot','fm'))
    elif original_rate>=38470 and 'FM' in broadcast.upper():
        kinds.append(('Radio / TV signals','fm'))
    for key,kind in kinds:
        if kind=='tv' and original_rate<31700:continue
        if kind=='ndr' and original_rate<22500:continue
        try:
            section=max(sections,key=lambda section:_window_score(section,kind,None))
            report=result.get(key) or {}
            outcome=str(report.get('result',''))
            confidence=report.get('certainty') in ('Strong','High','Possible','Tentative')
            supported=bool(confidence and (kind!='tv' or any(x in outcome.upper() for x in ('NTSC','PAL','SECAM','TV'))))
            if kind=='ndr' and ('no ' in outcome.lower() or 'not ' in outcome.lower()):
                supported=False
            target=(50 if '50 Hz' in outcome else 60) if kind=='mains' else (15625 if kind=='tv' and any(w in outcome for w in ('PAL','SECAM')) and 'NTSC' not in outcome else None)
            peak=render_peak_evidence(section['audio'],kind,section['start'],original_rate,
                                      target=target,mark_peak=supported,
                                      notch_info=section.get('ndr') if kind=='ndr' else None)
            blob=base64.b64encode(peak['png']).decode('ascii')
            if len(blob)<=400000:
                charts.setdefault(key,[]).append({'image_base64':blob,'caption':peak['caption'],
                                                   'kind':kind,'start':peak['section_start_s']})
        except (ValueError,RuntimeError,MemoryError):
            continue
    optional=[('Stereo phase / delay','phase',render_phase_evidence),
              ('Wow and flutter','wow',render_wow_evidence),
              ('Pitch / musical tuning','tuning',render_tuning_evidence)]
    for key,measure,renderer in optional:
        if key not in result:continue
        for section in sections:
            evidence=section.get(measure) or {}
            if measure=='wow' and not evidence.get('curve_seconds'):continue
            if measure=='tuning' and not evidence.get('metrics',{}).get('bins_cents'):continue
            if measure=='phase' and not evidence.get('metrics'):continue
            try:
                plot=renderer(section['audio'] if measure=='phase' else evidence)
                blob=base64.b64encode(plot['png']).decode('ascii')
                if len(blob)>400000:continue
                charts.setdefault(key,[]).append({'image_base64':blob,'caption':plot['caption'],
                                                   'kind':measure,'start':section['start']})
                break
            except (ValueError,RuntimeError,MemoryError):continue
    return charts
