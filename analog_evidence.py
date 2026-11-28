"""Bounded measurements of possible analog transfer defects. No forensic authentication.
Times are absolute recording seconds; absence of measurable shared signal is not a negative.
"""
from __future__ import annotations
import numpy as np
from scipy import signal, ndimage

FS=44100

def db(power):
    return 10*np.log10(np.maximum(power,1e-18))

def _runs(mask):
    edges=np.diff(np.r_[False,mask,False].astype(np.int8))
    return zip(np.flatnonzero(edges==1),np.flatnonzero(edges==-1))

def treble_losses(x, rate):
    """Detect short HF-specific losses with sustained LF/mid and HF on both sides."""
    if rate<18000: return {'tested':0,'events':[],'reason':'Original bandwidth too low for the 4–7 kHz comparison.'}
    y=signal.resample_poly(x,160,441,axis=0)
    fs=16000; hop=800; n=len(y)//hop
    if n<40: return {'tested':0,'events':[],'reason':'Excerpt too short.'}
    def band(lo,hi):
        z=signal.sosfilt(signal.butter(3,[lo,hi],fs=fs,btype='bandpass',output='sos'),y,axis=0)
        return db(np.mean(z[:n*hop].reshape(n,hop,-1)**2,axis=(1,2)))
    low=band(250,2200); high=band(4000,7000)
    # Relative treble, not absolute level; preserve lower-band content.
    ratio=high-low
    baseline=ndimage.median_filter(ratio,size=25,mode='nearest')
    midbase=ndimage.median_filter(low,size=25,mode='nearest')
    valid=(low>-48)&(midbase>-45)&(baseline>-35)
    mask=valid & (baseline-ratio>=12) & (abs(low-midbase)<=5)
    events=[]
    for a,b in _runs(mask):
        if not 2<=b-a<=12 or a<5 or b+5>n: continue
        before=ratio[a-5:a]; after=ratio[b:b+5]
        flank=min(float(np.median(before)),float(np.median(after)))
        depth=flank-float(np.median(ratio[a:b]))
        # Both flanks must have sustained treble and comparable tone balance.
        if depth<12 or abs(np.median(before)-np.median(after))>6: continue
        if max(np.ptp(before),np.ptp(after))>9: continue
        lower_delta=float(np.median(low[a:b])-np.median(np.r_[low[a-5:a],low[b:b+5]]))
        if abs(lower_delta)>5 or np.median(np.r_[high[a-5:a],high[b:b+5]])<-58: continue
        events.append({'start':round(a*.05,3),'end':round(b*.05,3),'loss_db':round(depth,1),'mid_change_db':round(lower_delta,1)})
    return {'tested':int(valid.sum()),'events':events,'frame_s':.05}


def alignment(x, channels, rate):
    """Track delay in two independent shared bands. Not a physical head measurement."""
    if channels!=2 or rate<14000: return {'tested':0,'frames':[],'reason':'Requires two channels and usable treble.'}
    # Retain 44.1 kHz timing resolution (22.7 microseconds), use 0.5 s frames.
    bands=[]
    for lo,hi in [(350,1800),(2200,6000)]:
        bands.append(signal.sosfilt(signal.butter(3,[lo,hi],fs=FS,btype='bandpass',output='sos'),x,axis=0))
    hop=FS//2; n=len(x)//hop; maxlag=round(.0008*FS); frames=[]
    for i in range(n):
        measured=[]
        for z in bands:
            a,b=z[i*hop:(i+1)*hop].T
            if min(np.mean(a*a),np.mean(b*b))<1e-7: break
            a=a-a.mean(); b=b-b.mean()
            cross=signal.correlate(a,b,method='fft'); center=len(a)-1
            corr=cross[center-maxlag:center+maxlag+1]/max(np.sqrt(np.dot(a,a)*np.dot(b,b)),1e-15)
            j=int(np.argmax(corr)); peak=float(corr[j]); lag=j-maxlag
            # Reject near-boundary maxima and ambiguous alternatives outside the central peak.
            if j==0 or j==len(corr)-1 or peak<.85: break
            remote=np.abs(np.arange(len(corr))-j)>8
            if remote.any() and peak-np.max(corr[remote])<.025: break
            ym,y0,yp=corr[j-1:j+2]; denom=ym-2*y0+yp
            frac=float(np.clip(.5*(ym-yp)/denom,-.5,.5)) if abs(denom)>1e-9 else 0.
            measured.append(((lag+frac)*1000/FS,peak,float(corr[maxlag])))
        if len(measured)!=2 or abs(measured[0][0]-measured[1][0])>.055: continue
        delay=(measured[0][0]+measured[1][0])/2
        frames.append({'time':round(i*.5+.25,3),'delay_ms':round(delay,4),'mid_corr':round(measured[0][1],3),'high_corr':round(measured[1][1],3),'high_zero_corr':round(measured[1][2],3)})
    delays=np.array([a['delay_ms'] for a in frames]); qualified=len(frames)>=max(6,n*.30)
    span=float(np.percentile(delays,90)-np.percentile(delays,10)) if len(delays)>=3 else None
    # Require multiple locally stable non-zero-delay frames and an actual change in lag.
    shifted=[f for f in frames if abs(f['delay_ms'])>=.10 and f['high_corr']-f['high_zero_corr']>=.10]
    variable=bool(qualified and len(shifted)>=4 and span is not None and span>=.13)
    fixed=bool(qualified and len(shifted)>=max(4,len(frames)*.6) and span is not None and span<.10)
    return {'tested':n,'frames':frames,'span_ms':round(span,4) if span is not None else None,
            'median_ms':round(float(np.median(delays)),4) if len(delays) else None,
            'shifted':len(shifted),'variable':variable,'fixed':fixed}


def rumble(x):
    """Report low-band level and persistence; bass, handling and filters confound."""
    y=signal.resample_poly(x,1,49,axis=0); fs=900
    n=len(y)//(2*fs)
    if n<2:return {'tested':0}
    values=[]
    for i in range(n):
        z=y[i*2*fs:(i+1)*2*fs]
        f,p=signal.welch(z,fs=fs,nperseg=900,axis=0)
        p=p.mean(axis=1)
        sub=float(np.sum(p[(f>=10)&(f<=35)])); bass=float(np.sum(p[(f>=80)&(f<=300)]))
        # f bins 1 Hz; sum PSD = integrated power.
        if bass<1e-9:continue
        values.append((float(db(sub)),float(db(sub/max(bass,1e-18)))))
    if not values:return {'tested':0}
    v=np.asarray(values); persistent=int(np.sum((v[:,0]>=-58)&(v[:,1]>=-12)))
    return {'tested':len(v),'low_dbfs':round(float(np.median(v[:,0])),1),'relative_db':round(float(np.median(v[:,1])),1),'persistent':persistent,
            'candidate':bool(len(v)>=3 and persistent>=len(v)*.75)}


def echo_screen(x):
    """A bounded same-excerpt faint-copy screen, not a detector of unknown reverse-side content.
    Search only genuinely quiet-to-loud comparisons, with whitened broadband templates.
    """
    fs=3000
    y=signal.resample_poly(x[:,int(np.argmax(np.mean(x*x,axis=0)))],10,147)
    y=signal.sosfilt(signal.butter(3,[300,1250],fs=fs,btype='bandpass',output='sos'),y)
    hop=fs//2; n=len(y)//hop
    if n<10:return {'tested':0,'events':[]}
    levels=np.sqrt(np.mean(y[:n*hop].reshape(n,hop)**2,axis=1)+1e-18)
    selected=sorted(range(n),key=lambda i:levels[i],reverse=True)[:5]
    events=[]; tested=0
    length=hop
    # Precompute running window power for normalised correlation.
    cs=np.r_[0.,np.cumsum(y*y,dtype=np.float64)]
    norms=np.sqrt(np.maximum(cs[length:]-cs[:-length],1e-18))
    for i in selected:
        a=i*hop; template=y[a:a+length]; power=float(np.linalg.norm(template))
        if power<.015:continue
        f,p=signal.welch(template,fs=fs,nperseg=256)
        p=p[(f>=350)&(f<=1150)]; flat=float(np.exp(np.mean(np.log(p+1e-18)))/max(np.mean(p),1e-18))
        if flat<.18:continue # avoid musical pure tones / periodic note coincidences
        offsets=np.arange(len(norms))-a
        ratios=norms/power
        mask=(np.abs(offsets)>=.8*fs)&(np.abs(offsets)<=7*fs)&(ratios>=.006)&(ratios<=.16)
        if mask.sum()<fs*.2:continue
        tested+=1
        for reversed_copy in (False,True):
            t=template[::-1] if reversed_copy else template
            corr=np.abs(signal.correlate(y,t,mode='valid',method='fft'))/np.maximum(norms*power,1e-15)
            corr[~mask]=0; j=int(np.argmax(corr)); c=float(corr[j])
            if c<.72:continue
            # Reject periodic / ambiguous matches and require both halves to match.
            far=mask&(abs(np.arange(len(corr))-j)>fs*.20)
            if far.any() and c-float(np.max(corr[far]))<.12:continue
            q=y[j:j+length]; half=length//2
            sub=[abs(np.dot(u,v))/max(np.linalg.norm(u)*np.linalg.norm(v),1e-15) for u,v in ((q[:half],t[:half]),(q[half:],t[half:]))]
            if min(sub)<.60:continue
            events.append({'quiet_time':round(j/fs,3),'loud_time':round(a/fs,3),'offset_s':round((j-a)/fs,3),'level_db':round(float(20*np.log10(ratios[j])),1),'correlation':round(c,3),'reversed':reversed_copy})
    return {'tested':tested,'events':events}


def measure_window(audio, input_rate, channels):
    x=np.asarray(audio,dtype=np.float32)
    return {'treble':treble_losses(x,input_rate),'alignment':alignment(x,channels,input_rate),
            'rumble':rumble(x),'echo':echo_screen(x) if input_rate>=4000 else {'tested':0,'events':[]}}


def consolidate(windows, intervals):
    """Compact actual event data, not raw audio arrays; all times absolute."""
    out={'treble':{'tested_frames':0,'events':[],'sections':0},'alignment':{'tested_frames':0,'frames':[],'variable_sections':0,'fixed_sections':0,'sections':[]},
         'rumble':{'sections':[]},'echo':{'tested_templates':0,'events':[]},'hiss':{'sections':[]},'surface':{'sections':[]},'wow':{'sections':[]},'dropouts':{'events':[],'tested_frames':0},'excerpts':len(windows)}
    for w,(start,duration) in zip(windows,intervals):
        a=w.get('analog') or {}; start=float(start)
        def at(v):return round(start+v,3)
        t=a.get('treble') or {}; al=a.get('alignment') or {}; r=a.get('rumble') or {}; e=a.get('echo') or {}
        out['treble']['tested_frames']+=t.get('tested',0); out['treble']['sections']+=bool(t.get('events'))
        out['treble']['events'] += [{**v,'start':at(v['start']),'end':at(v['end'])} for v in t.get('events',[])]
        out['alignment']['tested_frames']+=al.get('tested',0)
        out['alignment']['frames'] += [{**v,'time':at(v['time'])} for v in al.get('frames',[])]
        out['alignment']['variable_sections']+=bool(al.get('variable')); out['alignment']['fixed_sections']+=bool(al.get('fixed'))
        out['alignment']['sections'].append({'start':round(start,2), 'tested':al.get('tested',0),'accepted':len(al.get('frames',[])),**{k:al.get(k) for k in ('span_ms','median_ms','shifted','variable','fixed','reason')}})
        if r.get('tested'):out['rumble']['sections'].append({'start':round(start,2),**r})
        out['echo']['tested_templates']+=e.get('tested',0)
        out['echo']['events'] += [{**v,'quiet_time':at(v['quiet_time']),'loud_time':at(v['loud_time'])} for v in e.get('events',[])]
        h=w.get('hiss') or {}
        if h.get('usable'):out['hiss']['sections'].append({'start':round(start,2),**{k:h.get(k) for k in ('quiet_frames','noise_dbfs','flatness','persistent','spread_db','possible','supported')},'quiet_readings':[{**v,'time':at(v['time'])} for v in h.get('quiet_readings',[])]})
        s=w.get('surface') or {}
        if s:out['surface']['sections'].append({'start':round(start,2),**{k:s.get(k) for k in ('quiet_frames','crackly_frames','frames','clicks','quiet_clicks','irregular','channel')},'click_times_s':[at(v) for v in s.get('click_times_s',[])]})
        p=w.get('wow') or {}
        if p:out['wow']['sections'].append({'start':round(start,2),**{k:p.get(k) for k in ('result','rms_cents','rate_hz','prominence_db','tone_hz','nominal_hz','modulation_amplitude_cents','slow_rms_cents','fast_rms_cents','slow_peak_hz','fast_peak_hz','fast_prominence_db','valid_fast_band_hz')}})
        d=w.get('dropout_detail') or {};out['dropouts']['tested_frames']+=d.get('tested',0)
        out['dropouts']['events'] += [{**v,'start':at(v['start']),'end':at(v['end'])} for v in d.get('events',[])]
    return out


def analog_card(data,source,surface,hiss,wow,dropout):
    """Same scores as origin ranking; individual measurements kept together."""
    scores=(source.get('metrics') or {}).get('clue_scores',{})
    vinyl=float(scores.get('Vinyl / Record',0)); tape=float(scores.get('Cassette / Tape',0))
    top=max(vinyl,tape); gap=abs(vinyl-tape)
    if top<1.5: result,certainty='No strong analog-wear clue','Unclear'
    elif gap<1.5: result,certainty='Mixed analog clues','Possible'
    else:
        result='Mostly record-like wear clues' if vinyl>tape else 'Mostly tape-like wear clues'
        certainty='Possible' if top>=3 else 'Tentative'
    hm=hiss.get('metrics') or {}; wm=wow.get('metrics') or {}; al=data['alignment']; tr=data['treble']
    return {'result':result,'certainty':certainty,
        'detail':'Measured analog wear and transport clues, interpreted together. The scores are the same vinyl and cassette scores used in the origin ranking, not independent probabilities. A tape copy of a record may have both kinds of evidence.',
        'metrics':{'record_score':vinyl,'tape_score':tape,'dropouts':len(data['dropouts']['events']),
                   'treble_dropouts':len(tr['events']),'hiss_level_dbfs':hm.get('quiet_hiss_dbfs'),
                   'wobble_cents':wm.get('rms_cents'),'wobble_rate_hz':wm.get('rate_hz'),
                   'alignment_frames':len(al['frames']),'alignment_variable_sections':al['variable_sections'],
                   'record_clues':[x['reason'] for x in source.get('score_contributions',{}).get('Vinyl / Record',[])],
                   'tape_clues':[x['reason'] for x in source.get('score_contributions',{}).get('Cassette / Tape',[])]},
        'analog_measurements':data,'component_results':{'crackle':surface.get('result'),'hiss':hiss.get('result'),'wow':wow.get('result'),'dropouts':dropout.get('result')},
        'score_contributions':source.get('score_contributions',{})}
