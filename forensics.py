"""Bounded, evidence-first audio-forensic measurements for AudioCheQ.

A playback-speed *offset* requires a calibrated reference at the correct point
in the signal chain. Musical tuning and mechanical pitch variation are clues,
not proof that a recording was transferred at the wrong speed.
"""
from __future__ import annotations

import math
import numpy as np
from scipy import signal

FS = 44100


def _safe_corr(a, b):
    a = np.asarray(a, np.float64)
    b = np.asarray(b, np.float64)
    aa = a - np.mean(a)
    bb = b - np.mean(b)
    norm = float(np.linalg.norm(aa) * np.linalg.norm(bb))
    return float(np.dot(aa, bb) / norm) if norm > 1e-10 else None


def stereo_phase(audio, channels=2):
    """Channel correlation, polarity, and short fixed interchannel offset.

    Does not purport to identify tape azimuth from a single file: fixed delay,
    polarity, stereo mixing and codec processing have many possible causes.
    """
    if channels == 1 or audio.ndim != 2 or audio.shape[1] < 2:
        return {'result': 'Single-channel file', 'certainty': 'Not measurable',
                'detail': 'The uploaded file is mono; interchannel phase or delay cannot be measured.'}
    x = np.asarray(audio[:FS*9], np.float64)
    a = signal.resample_poly(x[:, 0], 1, 4)
    b = signal.resample_poly(x[:, 1], 1, 4)
    fs = FS/4
    rms_a = float(np.sqrt(np.mean(a*a)))
    rms_b = float(np.sqrt(np.mean(b*b)))
    if min(rms_a, rms_b) < 2e-6:
        return {'result': 'Channel too quiet', 'certainty': 'Not measurable',
                'detail': 'At least one channel was too quiet for meaningful phase comparison.'}
    zero_corr = _safe_corr(a, b)
    # Fixed-delay measurement works best on the 150-4500 Hz shared audio band.
    sos = signal.butter(3, [150, 4500], btype='bandpass', fs=fs, output='sos')
    aa = signal.sosfiltfilt(sos, a)
    bb = signal.sosfiltfilt(sos, b)
    aa -= aa.mean(); bb -= bb.mean()
    norm = float(np.linalg.norm(aa) * np.linalg.norm(bb))
    if norm < 1e-10:
        return {'result': 'Insufficient shared signal', 'certainty': 'Not measurable',
                'detail': 'No usable common 150–4500 Hz signal was found.'}
    maxlag = int(fs * .004)
    # fftconvolve, then evaluate a small lag range: bounded 9 s section.
    cross = signal.correlate(aa, bb, method='fft', mode='full')
    center = len(bb)-1
    nearby = cross[center-maxlag:center+maxlag+1] / norm
    lag = int(np.argmax(np.abs(nearby))) - maxlag
    aligned = float(nearby[lag+maxlag])
    delay_ms = lag * 1000 / fs
    bands = {}
    for name, low, high in [('Bass',80,450),('Mid',450,2000),('High',2000,4500)]:
        flt = signal.butter(3,[low,high],btype='bandpass',fs=fs,output='sos')
        bands[name] = _safe_corr(signal.sosfiltfilt(flt,a),signal.sosfiltfilt(flt,b))
    midside = 20*math.log10((np.sqrt(np.mean((a-b)**2))+1e-12) /
                            (np.sqrt(np.mean((a+b)**2))+1e-12))
    level_difference = 20*math.log10((rms_a+1e-12)/(rms_b+1e-12))
    aligned_abs=abs(aligned)
    if zero_corr is not None and zero_corr < -.96 and abs(delay_ms)<.25:
        label,certainty='Possible polarity reversal','Possible'
    elif aligned_abs > .90 and abs(delay_ms) >= .18 and abs(delay_ms)<=3.5:
        label,certainty='Possible channel delay','Possible'
    elif zero_corr is not None and zero_corr > .997:
        label,certainty='Nearly identical channels','High'
    elif zero_corr is not None and zero_corr < -.6:
        label,certainty='Strong opposite-phase content','Possible'
    else:
        label,certainty='Distinct stereo channels','High'
    detail = (f'Zero-lag Pearson r={zero_corr:+.3f}; strongest absolute cross-correlation '
              f'within ±4 ms is {aligned:+.3f} at {delay_ms:+.3f} ms (positive means '
              'left-channel content follows right in this convention). '
              f'L/R RMS level difference {level_difference:+.1f} dB; side/mid ratio '
              f'{midside:+.1f} dB. Band-limited zero-lag r: ' +
              ', '.join(f'{k} {v:+.2f}' if v is not None else f'{k} n/a' for k,v in bands.items()) +
              '. A fixed delay can come from processing, microphone placement or transfer; '
              'it is not by itself evidence of cassette azimuth or the original mix.')
    return {'result':label, 'certainty':certainty, 'detail':detail,
            'metrics':{'zero_corr':round(zero_corr,4) if zero_corr is not None else None,
                       'aligned_corr':round(aligned,4), 'delay_ms':round(delay_ms,4),
                       'level_difference_db':round(level_difference,2),
                       'side_mid_db':round(midside,2),
                       'band_corr':{k:(round(v,3) if v is not None else None) for k,v in bands.items()},
                       'lag_samples':lag, 'lag_rate':fs}}


def _refined_peak(f, p, idx):
    """Quadratic interpolation of the log power peak within a three-bin FFT."""
    if idx < 1 or idx+1 >= len(p):
        return float(f[idx])
    q = np.log(np.maximum(p[idx-1:idx+2],1e-22))
    den = float(q[0]-2*q[1]+q[2])
    off = 0.5 * float(q[0]-q[2])/den if abs(den) > 1e-9 else 0.0
    return float(f[idx]+np.clip(off,-1,1)*(f[1]-f[0]))


def pitch_tuning(audio):
    """Estimate consistent semitone-grid displacement relative to A440.

    A musical *tuning* estimate, not a verified speed estimate.  Distinct notes
    must vote for one offset; transient/noise-only material is rejected.
    """
    if len(audio) < FS*6:
        return {'result':'No reliable tuning clue','certainty':'Not measurable',
                'detail':'At least six seconds are needed for a tuning-distribution screen.'}
    y = np.mean(audio[:FS*18],axis=1,dtype=np.float64) if audio.ndim==2 else np.asarray(audio[:FS*18],float)
    y = signal.resample_poly(y,1,4)
    fs=FS/4
    nfft=8192
    f,t,z=signal.stft(y,fs=fs,nperseg=nfft,noverlap=nfft-2205,boundary=None,padded=False)
    band = (f>=145)&(f<=1800)
    freqs = f[band]
    mag = np.abs(z[band])
    if mag.size == 0 or len(t)<10:
        return {'result':'No reliable tuning clue','certainty':'Not measurable',
                'detail':'There were insufficient resolved pitched frames.'}
    db = 20*np.log10(np.maximum(mag,1e-12))
    candidates=[]
    used_frames=0
    unique_notes=set()
    # Two peaks closer than 19Hz are treated as a single partial.
    for col in range(db.shape[1]):
        frame=db[:,col]
        floor=float(np.percentile(frame,45))
        ids,_=signal.find_peaks(frame,distance=14,prominence=7,height=floor+13)
        if not len(ids):
            continue
        ids=sorted(ids,key=lambda ix:frame[ix],reverse=True)[:7]
        votes=[]
        for ix in ids:
            global_index=int(np.flatnonzero(band)[ix])
            hz=_refined_peak(f,np.abs(z[:,col])**2,global_index)
            if hz<=0:continue
            note=69+12*math.log2(hz/440)
            nearest=int(round(note))
            cents=(note-nearest)*100
            # Avoid minor peaks and extreme tails very close to +/-50c.
            if abs(cents)>=49:continue
            votes.append((float(cents),nearest))
        if votes:
            used_frames+=1
            candidates.extend(votes)
            unique_notes.update(note for _,note in votes)
    if used_frames<9 or len(candidates)<35 or len(unique_notes)<3:
        return {'result':'No reliable tuning clue','certainty':'Not measurable',
                'detail':f'Insufficient stable tonal evidence: {used_frames} pitched frames and {len(unique_notes)} distinct semitone bins.'}
    offsets=np.array([x[0] for x in candidates])
    # A histogram tests *concentration* instead of forcing a best offset on noise.
    bins=np.arange(-50,51,5)
    counts,_=np.histogram(offsets,bins=bins)
    smooth=np.convolve(counts,np.array([.25,.5,.25]),mode='same')
    center=float((bins[np.argmax(smooth)]+bins[np.argmax(smooth)+1])/2)
    nearby=abs(offsets-center)<=13
    fraction=float(np.mean(nearby))
    if fraction < .43 or int(nearby.sum())<32:
        return {'result':'Tuning not coherent','certainty':'Unclear',
                'detail':f'{len(offsets)} spectral-peak votes across {used_frames} frames had no concentrated semitone-grid offset (best 13-cent cluster {fraction*100:.0f}%).',
                'metrics':{'offsets_cents':np.histogram(offsets,bins=np.arange(-50,55,5))[0].tolist(), 'bins_cents':np.arange(-47.5,50,5).tolist(), 'fraction':round(fraction,3)}}
    deviation=float(np.median(offsets[nearby]))
    deviation=round(deviation,1)
    # Detuning may be deliberate or instrument-specific: never report actual speed.
    if abs(deviation)<9:
        label='Near A440 tuning'
    elif deviation<0:
        label=f'~{abs(deviation):.0f} cents flat'
    else:
        label=f'~{deviation:.0f} cents sharp'
    hypothetical_pct=(2**(-deviation/1200)-1)*100
    detail=(f'{len(offsets)} resolved spectral-peak votes in {used_frames} pitched STFT frames '
            f'from {len(unique_notes)} semitone bins; {fraction*100:.0f}% fall within ±13 cents '
            f'of the strongest five-cent offset cluster. Median estimated displacement '
            f'{deviation:+.1f} cents from equal temperament at A=440 Hz. '
            f'If a uniform tape/disc speed error ALONE caused this, the mathematical '
            f'correction would be {hypothetical_pct:+.2f}% in playback rate. '
            'However altered tuning, temperament, vibrato, harmonics and other musical '
            'effects can create the same offset. Do not treat this as verified wrong speed.')
    return {'result':label,'certainty':'Tentative' if abs(deviation)>=9 else 'Possible',
            'detail':detail,
            'metrics':{'deviation_cents':deviation, 'hypothetical_correction_percent':round(hypothetical_pct,2),
                       'votes':len(offsets),'frames':used_frames,'notes':len(unique_notes),
                       'fraction':round(fraction,3),
                       'bins_cents':np.arange(-47.5,50,5).tolist(),
                       'offsets_cents':counts.tolist()}}


def _best_channel(audio, center_hz):
    if audio.ndim != 2: return np.asarray(audio, np.float64)
    test = [audio[:,0],audio[:,1]]
    strengths=[]
    for s in test:
        f,p = signal.welch(s,fs=FS,nperseg=min(len(s),FS*2))
        mask=abs(f-center_hz)<5
        strengths.append(float(np.max(p[mask])) if np.any(mask) else 0)
    return np.asarray(test[int(np.argmax(strengths))],np.float64)


def track_reference_tone(audio, center_hz, nominal_hz, snr_db):
    """Demodulate a corroborated line and measure *variation*, not overall speed.

    Complex downconversion to 0 Hz, decimation to 300 Hz, and phase derivative
    provide sub-FFT-bin frequency tracking. Lock only to a tone already screened
    as present and persistent by the separate spectral detector.
    """
    if len(audio)<FS*6 or snr_db<13 or center_hz>=FS/2-100:
        return None
    x=_best_channel(audio[:FS*18],center_hz)
    n=np.arange(len(x))
    base=signal.resample_poly(x * np.exp(-2j*np.pi*center_hz*n/FS),1,147)
    fs=300
    # +/- 40 Hz search around a stable reference; remove out-of-band music.
    sos=signal.butter(4,38,fs=fs,output='sos')
    base=signal.sosfiltfilt(sos,base)
    mag=np.abs(base)
    if np.median(mag)<1e-7 or np.mean(mag>=max(np.median(mag)*.25,1e-7))<.85:
        return None
    inst = center_hz + np.gradient(np.unwrap(np.angle(base)))*fs/(2*np.pi)
    # The smoothed derivative resolves 0.5-30 Hz modulation.
    inst=signal.savgol_filter(inst,5,2)
    # Suppress filtering boundaries and any remaining transient frames.
    inst=inst[fs:-fs]
    if len(inst)<fs*4 or not np.all(np.isfinite(inst)):
        return None
    center=float(np.median(inst))
    cents=1200/np.log(2)*(inst-center)/center
    cents=cents - np.mean(cents)
    rms=float(np.sqrt(np.mean(cents*cents)))
    f,p=signal.welch(cents,fs=fs,nperseg=min(len(cents),4096),scaling='spectrum')
    # Separate slow wow and faster flutter. A weak mains line is unsuitable
    # for confident high-rate modulation; keep that result explicitly unavailable.
    band_metrics={}
    for name,lo,hi in [('slow',.3,6),('fast',6,25)]:
        if name=='fast' and (nominal_hz<500 or snr_db<18):
            continue
        mask=(f>=lo)&(f<hi)
        if not mask.any():continue
        ids=np.flatnonzero(mask); idx=ids[int(np.argmax(p[ids]))]
        # Welch Hann spectrum has 1.5-bin equivalent noise bandwidth.
        band_rms=float(np.sqrt(max(0,np.sum(p[mask])/1.5)))
        local=mask & (abs(f-f[idx])>.24)
        prominence_band=float(10*np.log10((p[idx]+1e-15)/(np.median(p[local])+1e-15))) if local.any() else 0.
        band_metrics.update({name+'_rms_cents':round(band_rms,3),name+'_peak_hz':round(float(f[idx]),3),name+'_prominence_db':round(prominence_band,1)})
    band_metrics['valid_fast_band_hz']='6–25 Hz' if 'fast_rms_cents' in band_metrics else None
    useful=(f>=.3)&(f<=25)
    # Top periodic component across the whole wow+flutter band.
    region=np.flatnonzero(useful)
    if not len(region): return None
    i=region[int(np.argmax(p[region]))]
    peak_hz=float(f[i]); peak_power=float(p[i]);
    near=(f>=.3)&(f<=30)&(abs(f-peak_hz)>.24)
    floor=float(np.median(p[near])) if np.any(near) else 1e-12
    prominence=10*np.log10((peak_power+1e-15)/(floor+1e-15))
    amplitude=float(np.sqrt(max(0,2*peak_power)))
    # Confidence gates matter: a single FFT wiggle in noise is not wow.
    periodic=bool(prominence>=12 and amplitude>=.65 and rms>=.50)
    if periodic and .3<=peak_hz<6:
        classification='Periodic wow'
    elif periodic and 6<=peak_hz<=25 and 'fast_rms_cents' in band_metrics:
        classification='Possible flutter'
    elif rms>=1.4:
        classification='Pitch drift / instability'
    else:
        classification='No clear wobble'
    return {'result':classification,'certainty':'Possible' if periodic else 'Tentative' if rms>=1.4 else 'Not detected',
            'rms_cents':round(rms,2), 'rate_hz':round(peak_hz,3),
            'modulation_amplitude_cents':round(amplitude,2),
            'prominence_db':float(round(float(prominence),1)),'tone_hz':round(center,3),
            'nominal_hz':round(nominal_hz,3), **band_metrics,
            'detail':(f'A tracked reference tone at {center:.3f} Hz (nominal {nominal_hz:,.2f} Hz) '
                      f'showed {rms:.2f} cents RMS short-term pitch variation. '
                      f'Strongest 0.3–25 Hz frequency-modulation component: {peak_hz:.2f} Hz, '
                      f'{amplitude:.2f} cents peak amplitude, {prominence:.1f} dB above other modulation rates. '
                      'Wow refers to slower speed fluctuations (below ~6 Hz); flutter is faster. '
                      'A clear peak near 0.556 / 0.750 / 1.300 Hz may be compatible with '
                      '33⅓ / 45 / 78 RPM eccentricity, but vibrato or electrical frequency '
                      'variation can mimic a wobble. This only describes the sampled segment.'),
            'curve_seconds':(np.arange(0,len(cents),15)/fs+1).round(3).tolist(),
            'curve_cents':cents[::15].round(3).tolist(),
            'mod_freq_hz':f[useful][::2].round(4).tolist(),
            'mod_power_db':(10*np.log10(np.maximum(p[useful][::2],1e-14))).round(3).tolist()}


def reference_candidates(windows):
    """Collect *corroborated* observations; conflicting references stay separate."""
    out=[]
    for name,nominal in [('FM stereo pilot',19000.0),('525-line TV',15734.26),('625-line TV',15625.0)]:
        good=[w['broadcast'][name] for w in windows if w.get('broadcast',{}).get(name) and
              w['broadcast'][name].get('pass')]
        if good:
            # TV candidates close to both 525/625 are not distinct standards;
            # only choose the confirmed signal family from the detector.
            freqs=[float(r['freq']) for r in good]
            out.append({'kind':name,'nominal':nominal,'observed':float(np.median(freqs)),
                        'prominence_db':float(np.median([r['snr'] for r in good])),
                        'sections':len(good),'reference_grade': 3 if name=='FM stereo pilot' else 2})
    for nominal in (50,60):
        good=[]
        for w in windows:
            s=w.get('mains',{}).get(nominal,{})
            if s.get('count',0)<2:continue
            actual=[float(hz)/harm for harm,hz in s.get('freqs',[]) if harm>0]
            if len(actual)>=2 and float(np.std(actual))<=.24:
                good.append((float(np.median(actual)),s['snr']))
        if good:
            out.append({'kind':f'{nominal} Hz hum','nominal':float(nominal),
                        'observed':float(np.median([o for o,_ in good])),
                        'prominence_db':float(np.median([snr for _,snr in good])),
                        'sections':len(good),'reference_grade':1})
    return out


def speed_assessment(windows, tuning=None):
    refs=reference_candidates(windows)
    if refs:
        # Only compare corroborated reference lines. Constant pitch shift
        # remains ambiguous when the reference entered *after* copying.
        refs.sort(key=lambda x:(x['reference_grade'],x['sections'],x['prominence_db']),reverse=True)
        main=refs[0]
        ratio=main['observed']/main['nominal']
        speed_error=(ratio-1)*100
        correction=(1/ratio-1)*100
        cents=1200*math.log2(ratio)
        disagreement=[r for r in refs[1:] if abs(r['observed']/r['nominal']-ratio)>.002]
        values=', '.join(f"{r['kind']} {r['observed']:.2f}/{r['nominal']:.2f} Hz" for r in refs[:4])
        if disagreement:
            return {'result':'Conflicting reference tones','certainty':'Unclear',
                    'detail':f'Different reference families disagree by over 0.2%: {values}. The tones may have entered at different stages; applying one correction would be unsupported.',
                    'metrics':{'references':refs}}
        if abs(speed_error)<=.035:
            label='Near reference speed'
        elif speed_error<0:
            label=f'~{abs(speed_error):.2f}% slow'
        else:
            label=f'~{speed_error:.2f}% fast'
        details=(f'Reference family: {main["kind"]}; observed {main["observed"]:.3f} Hz '
                 f'versus nominal {main["nominal"]:.3f} Hz. Observed/nominal ratio '
                 f'{ratio:.7f} => apparent speed deviation {speed_error:+.3f}%; '
                 f'a matching variable-speed correction would be {correction:+.3f}% '
                 f'({cents:+.2f} cents pitch offset). '
                 f'Corroborating reference observations: {values}. '
                 'This is conditional on the line being a genuine calibration/broadcast/mains '
                 'reference already on the recording BEFORE its speed was altered. '
                 'A tone acquired during digitization or a later transfer cannot establish '
                 'the original song speed; a matching ratio does not prove intended musical pitch.')
        return {'result':label, 'certainty':'Possible' if main['sections']>=2 else 'Tentative',
                'detail':details,
                'metrics':{'observed_hz':round(main['observed'],3), 'nominal_hz':main['nominal'],
                           'speed_error_percent':round(speed_error,3),
                           'correction_percent':round(correction,3),
                           'pitch_offset_cents':round(cents,2),
                           'reference_kind':main['kind'],'references':refs}}
    if tuning and tuning.get('metrics',{}).get('deviation_cents') is not None:
        off=tuning['metrics']['deviation_cents']
        return {'result':'Only tuning-based clue','certainty':'Unclear',
                'detail':f'The music appears {off:+.1f} cents from A440, but the source may simply use nonstandard tuning. No confirmed 50/60 Hz, TV scan or FM pilot line establishes playback speed; no speed correction is warranted.'}
    return {'result':'No reliable speed reference','certainty':'Not measurable',
            'detail':'No persistent calibrated pilot, TV-scanning or corroborated power-line harmonics were available. Musical tempo, apparent voice pitch and instrument brightness alone cannot determine absolute transfer speed.'}
