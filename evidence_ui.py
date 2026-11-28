"""Safe HTML for the measured-data areas of the existing Streamlit cards."""
import html
import math


def esc(value):
    return html.escape(str(value))


def f(value,digits=2):
    return f'{value:.{digits}f}' if isinstance(value,(int,float)) and not isinstance(value,bool) and math.isfinite(value) else 'Unavailable'


def timestamp(s):
    if not isinstance(s,(int,float)) or not math.isfinite(s):return 'Unavailable'
    # Integer millisecond formatting avoids rollover to 00:60.000.
    ms=max(0,round(s*1000)); return f'{ms//60000:02d}:{ms//1000%60:02d}.{ms%1000:03d}'


def table(head, rows):
    if not rows:return ''
    return ('<div class="ac-data-scroll"><table class="ac-data-table"><thead><tr>'+''.join('<th>'+esc(v)+'</th>' for v in head)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+esc(v)+'</td>' for v in row)+'</tr>' for row in rows)+'</tbody></table></div>')


def heading(title,body,contents=''):
    return '<div class="ac-data-section"><div class="ac-measure-head">'+esc(title)+'</div><p>'+esc(body)+'</p>'+contents+'</div>'


def score_table(contributions,only=None):
    rows=[]
    for source, entries in contributions.items():
        if only and source not in only:continue
        for e in entries:
            rows.append((source, f(e.get('points'),2), e.get('reason','')))
    if not rows:return ''
    return heading('Evidence used in the source ranking','Positive and negative points are heuristic weights, not probabilities. Each line is a clue or an explicit conflict adjustment.',table(('Source','Points','Reason'),rows))


def rotation_html(item):
    matches=item.get('click_matches') or []
    raw=item.get('click_candidates_by_excerpt') or []
    output=heading('Actual click positions','Timestamps are offsets from the beginning of the uploaded recording, estimated by the click detector. A matched click is an observed impulse selected by the best periodic fit, not an artificial marker.')
    if matches:
        rows=[]
        for v in matches:
            rows.append((timestamp(v.get('start_seconds')),v.get('channel') or 'Unknown',f(v.get('rpm'),3),f(v.get('period_s'),4),f(v.get('fit_error_ms'),2),'Strict' if v.get('strict') else 'Relaxed',len(v.get('click_times_s',[])),', '.join(timestamp(t) for t in v.get('click_times_s',[]))))
        output+=table(('Excerpt start','Channel','Candidate RPM','Period (s)','RMS fit error (ms)','Fit','Clicks','Matched click locations'),rows)
    else:output+='<p>No click sequence passed the rotational fitting test. Individual impulsive candidates may still occur.</p>'
    if raw:
        output+=heading('Individual click candidates (not necessarily periodic)','These impulses come from the surface-noise screen; percussion and other transients can be included.',table(('Excerpt start','Channel','Count','Candidate locations'),[(timestamp(v.get('start_seconds')),v.get('channel') or 'Unknown',len(v.get('click_times_s',[])),', '.join(timestamp(t) for t in v.get('click_times_s',[])) or 'None') for v in raw]))
    return output


def analog_html(item):
    d=item.get('analog_measurements') or {}; out=''
    if not d:return ''
    components=item.get('component_results') or {}
    surf=(d.get('surface') or {}).get('sections',[])
    out+=heading('1. Surface crackle and pops',f'{components.get("crackle") or "Unavailable"}. Sharp, irregular clicks and crackly quiet passages favour disc surface wear; percussion, clipping and digital glitches can imitate them. Counts below use the stronger channel in each excerpt.',table(('Excerpt start','Channel','Active 0.5 s frames','Crackly frames','Quiet crackly frames','Click candidates','Quiet clicks','Irregular'),[(timestamp(v.get('start')),v.get('channel') or 'Unknown',v.get('frames'),v.get('crackly_frames'),v.get('quiet_frames'),v.get('clicks'),v.get('quiet_clicks'),'Yes' if v.get('irregular') else 'No') for v in surf]))
    hs=(d.get('hiss') or {}).get('sections',[])
    readings=[r for v in hs for r in v.get('quiet_readings',[])]
    out+=heading('2. Hiss and noise-floor variation',f'{components.get("hiss") or "Unavailable"}. Measured in quieter one-second passages in the 4.8–7.4 kHz band. dBFS is decibels relative to maximum digital level; flatter broadband noise resembles hiss. IQR is the middle 50% spread, not a diagnosis of Dolby noise reduction. Varying hiss may accompany tape copying, but music and processing also affect it.' if hs else 'Not measurable: too few suitably quiet passages, or insufficient source bandwidth. This does not mean there is no hiss.',table(('Excerpt start','Quiet frames','Median (dBFS)','Flatness (0–1)','Hiss-like frames (%)','IQR (dB)'),[(timestamp(v.get('start')),v.get('quiet_frames'),f(v.get('noise_dbfs'),1),f(v.get('flatness'),3),f(100*v['persistent'],1) if isinstance(v.get('persistent'),(float,int)) else 'Unavailable',f(v.get('spread_db'),1)) for v in hs])+table(('Quiet-frame midpoint','Level (dBFS)','Flatness'),[(timestamp(v.get('time')),f(v.get('noise_dbfs'),1),f(v.get('flatness'),3)) for v in readings]))
    wow=(d.get('wow') or {}).get('sections',[])
    out+=heading('3. Wow and flutter (speed instability)',f'{components.get("wow") or "Unavailable"}. Slow wow = 0.3–6 Hz modulation; faster flutter = 6–25 Hz in a sufficiently strong high-frequency reference. One cent is 1/100 of a semitone; RMS is typical variation. Regular wobble near 0.556, 0.750 or 1.300 Hz may match 33⅓, 45 or 78 RPM. Faster or irregular wobble supports tape transport more than an off-centre disc; motors and later electrical interference can also cause it.' if wow else 'Not measurable: no sufficiently stable technical reference tone to track. Ordinary musical vibrato is not a reliable substitute. No conclusion about the absence of wow or flutter.',table(('Excerpt start','Reference (Hz)','Overall RMS (cents)','Peak rate (Hz)','Peak prominence (dB)','Slow RMS (cents)','Slow peak (Hz)','Fast RMS (cents)','Fast peak (Hz)','Fast prominence (dB)'),[(timestamp(v.get('start')),f(v.get('tone_hz'),3),f(v.get('rms_cents')),f(v.get('rate_hz'),3),f(v.get('prominence_db'),1),f(v.get('slow_rms_cents'),3),f(v.get('slow_peak_hz'),3),f(v.get('fast_rms_cents'),3),f(v.get('fast_peak_hz'),3),f(v.get('fast_prominence_db'),1)) for v in wow]))
    dp=d.get('dropouts') or {}; tr=d.get('treble') or {}
    out+=heading('4. Whole-sound interruptions',f'{len(dp.get("events",[]))} candidate(s) in {dp.get("tested_frames",0)} 50 ms frames. Brief losses of the whole signal may reflect a defect in tape, editing, intentional silence or digital glitches.',table(('Start','End','Duration (ms)','Level loss (dB)'),[(timestamp(v.get('start')),timestamp(v.get('end')),f((v['end']-v['start'])*1000,0),f(v.get('loss_db'),1)) for v in dp.get('events',[])]))
    out+=heading('5. Frequency-specific treble dropouts',f'{len(tr.get("events",[]))} candidate(s) in {tr.get("tested_frames",0)} eligible 50 ms frames across {tr.get("sections",0)} excerpt(s) with candidates. Treble loss is relative to 250–2,200 Hz sound, which must remain approximately steady. This pattern may indicate worn tape or poor tape-to-head contact. Zero eligible frames means not measurable; an instrument change can still mimic the pattern.',table(('Start','End','Duration (ms)','4–7 kHz relative loss (dB)','Mid-band change (dB)'),[(timestamp(v.get('start')),timestamp(v.get('end')),f((v['end']-v['start'])*1000,0),f(v.get('loss_db'),1),f(v.get('mid_change_db'),1)) for v in tr.get('events',[])]))
    al=d.get('alignment') or {}; aframes=al.get('frames',[])
    out+=heading('6. Tape-head alignment / azimuth candidates',f'{len(aframes)} shared-signal frames accepted out of {al.get("tested_frames",0)} tested. {al.get("variable_sections",0)} varying-delay excerpt(s), {al.get("fixed_sections",0)} fixed-delay excerpt(s). The test compares two frequency bands (350–1,800 Hz and 2.2–6 kHz); a consistent timing shift that restores high-band correlation is compatible with head alignment. Changing delay is more discriminating. A physical tape head cannot be inspected from sound alone; microphones, mixing and stereo processing can create delay. No accepted frames means no reliable measurement.',table(('Excerpt start','Frames tested','Accepted','Median L/R delay (ms)','10th–90th percentile span (ms)','Shifted frames','Pattern'),[(timestamp(v.get('start')),v.get('tested'),v.get('accepted'),f(v.get('median_ms'),4),f(v.get('span_ms'),4),v.get('shifted') if v.get('shifted') is not None else 'Unavailable','Varying' if v.get('variable') else 'Fixed' if v.get('fixed') else 'Not confirmed') for v in al.get('sections',[])])+table(('Frame midpoint','L/R delay (ms)','Mid correlation after alignment','High correlation after alignment','High correlation before alignment'),[(timestamp(v.get('time')),f(v.get('delay_ms'),4),f(v.get('mid_corr'),3),f(v.get('high_corr'),3),f(v.get('high_zero_corr'),3)) for v in aframes]))
    ru=(d.get('rumble') or {}).get('sections',[])
    out+=heading('7. Low-frequency rumble',f'{sum(bool(v.get("candidate")) for v in ru)} excerpt(s) with persistent low-frequency candidates. The measured 10–35 Hz level is compared with 80–300 Hz bass. Mechanical turntable noise and warps can cause rumble; music, handling, mains-related equipment, tape machinery and filters make it weak evidence.',table(('Excerpt start','2 s frames','10–35 Hz (dBFS)','Relative to bass (dB)','Elevated frames','Persistent candidate'),[(timestamp(v.get('start')),v.get('tested'),f(v.get('low_dbfs'),1),f(v.get('relative_db'),1),v.get('persistent'),'Yes' if v.get('candidate') else 'No') for v in ru]))
    e=d.get('echo') or {}; events=e.get('events',[])
    out+=heading('8. Print-through and possible reversed-copy similarity',f'{e.get("tested_templates",0)} suitable loud templates compared with substantially quieter passages within 0.8–7 seconds; {len(events)} similarity candidate(s). A faint forward copy before/after a loud passage can resemble tape print-through. A reversed copy can be consistent with bleed, but intentional echoes, repeated music and production effects can mimic either. Unknown audio from the opposite cassette side cannot be verified without a matching reference. Not used as decisive origin evidence.',table(('Quiet passage','Loud passage','Offset (s)','Relative level (dB)','Similarity (0–1)','Direction'),[(timestamp(v.get('quiet_time')),timestamp(v.get('loud_time')),f(v.get('offset_s'),3),f(v.get('level_db'),1),f(v.get('correlation'),3),'Reversed' if v.get('reversed') else 'Forward') for v in events]))
    return out+score_table(item.get('score_contributions') or {},('Vinyl / Record','Cassette / Tape'))
