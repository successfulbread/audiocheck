"""Numerical, file-specific observation notes for every AudioCheQ finding.

Only summarizes measurements already made by the signal analyzer. The data
below are never created from reference ticks or classifier expectations.
"""
from __future__ import annotations

from collections import Counter
from math import isfinite

from forensics import reference_candidates


def enrich_findings(rows, windows, metadata, intervals):
    found = dict(rows)
    count = len(windows)
    analyzed = round(sum(float(s) for _, s in intervals), 1)
    window_times = ', '.join(f'{start:.1f}–{start+length:.1f}s' for start, length in intervals)
    fs = int(metadata.get('input_rate') or 0)
    bitrate = metadata.get('file_history', {}).get('facts', {}).get('bitrate_kbps')
    clipped = [w.get('clipped', 0) for w in windows]

    def add(key, *notes, **metrics):
        item = found.get(key)
        if item is None:
            return
        saved = item.setdefault('observations', [])
        saved.extend(str(s) for s in notes if s is not None and str(s))
        current = item.setdefault('metrics', {})
        for name, value in metrics.items():
            if isinstance(value, (float, int)) and not isinstance(value, bool) and isfinite(value):
                current.setdefault(name, value)

    common = (f'File: {metadata.get("codec", "unknown")} codec; {fs:,} Hz sampling; '
              f'{metadata.get("channels", "?")} channel(s); original Nyquist {fs/2:,.0f} Hz.')
    spans = f'Examined {count} decoded excerpt(s) ({analyzed:.1f} s total); locations: {window_times}.'
    add('Likely audio source', common, spans,
        f'Clipping at ≥99.8% full-scale: {100*sum(clipped)/len(clipped):.3f}% of decoded samples across excerpts.' if clipped else None,
        f'Brief-level interruptions detected: {sum(w.get("dropouts", 0) for w in windows)}.',
        f'Codec bitrate in this digital file: {bitrate} kbps.' if bitrate else None,
        sampled_sections=count, analyzed_seconds=analyzed,
        possible_interruptions=sum(w.get('dropouts', 0) for w in windows))

    rotations = [w['vinyl'] for w in windows if w.get('vinyl')]
    if rotations:
        top = max(rotations, key=lambda x: x.get('score', 0))
        add('Vinyl rotation',
            f'Accepted click-period matches in {len(rotations)}/{count} excerpts; '
            f'best: {top["rpm"]:.2f} RPM from {top["events"]} aligned click events, '
            f'{top["pairs"]} consecutive-revolution pairs.',
            f'Fitted click interval {top["period"]:.4f} s; RMS fit error {top["fit_ms"]:.2f} ms; '
            f'coverage span {top["span"]:.1f} s; ' + ('relaxed' if top['relaxed'] else 'strict') + ' interval gate.',
            matched_sections=len(rotations), click_events=top['events'],
            fitted_rotation_period_s=round(top['period'], 4), click_fit_error_ms=round(top['fit_ms'], 2))
    else:
        add('Vinyl rotation', f'0 of {count} excerpts yielded a qualifying 33⅓, 45 or 78 RPM click-train fit.',
            'Reference revolution periods tested: 1.800, 1.333 and 0.769 s. This does not mean that zero individual clicks occurred.',
            matched_sections=0)

    surf = [w.get('surface') or {} for w in windows]
    quiet = sum(x.get('quiet_frames', 0) for x in surf)
    broad = sum(x.get('crackly_frames', 0) for x in surf)
    click_count = sum(x.get('clicks', 0) for x in surf)
    active = sum(x.get('frames', 0) for x in surf)
    add('Likely audio source',
        f'High-frequency surface-noise screen: {broad} crackly 0.5-second frames, '
        f'{quiet} qualifying quiet frames and {click_count} isolated click candidates in {active} active frames.')

    for base in (50, 60):
        tested = [w.get('mains', {}).get(base) or {} for w in windows]
        accepted = sum(int(x.get('count', 0)) for x in tested)
        weak = sum(int(x.get('weak', 0)) for x in tested)
        framecount = sum(int(x.get('frames', 0)) for x in tested)
        frequencies = [(harm, hz) for x in tested for harm, hz in x.get('freqs', [])]
        freqs_text = ', '.join(f'{f:.2f} Hz (×{harm})' for harm, f in frequencies[:7]) or 'none passed persistence gates'
        add('Likely power system',
            f'{base} Hz family: {accepted} accepted / {weak} weak distinct harmonic tests '
            f'across {framecount} analysed ~8 s FFT frames; measured accepted lines: {freqs_text}.')
    add('Likely power system', spans,
        'Persistent harmonics require repeated 7–10 dB local prominence and ≥60% of analyzable frames. A 300 Hz harmonic alone cannot distinguish 50 from 60 Hz.',
        sampled_sections=count)

    for name, target in [('525-line TV', 15734.26), ('625-line TV', 15625.0)]:
        candidates = [w.get('broadcast', {}).get(name) for w in windows]
        strong = [x for x in candidates if x and x.get('pass')]
        weak = [x for x in candidates if x and x.get('tentative') and not x.get('pass')]
        if strong or weak:
            best = max(strong or weak, key=lambda x:x.get('snr', 0))
            note = (f'{name}, reference {target:,.2f} Hz: observed {best["freq"]:,.2f} Hz '
                    f'(offset {best["freq"]-target:+.2f} Hz); prominence {best["snr"]:+.1f} dB; '
                    f'{len(strong)} strong / {len(weak)} tentative excerpt(s).')
        else:
            note = f'{name}, reference {target:,.2f} Hz: 0 qualifying peaks out of {count} excerpt(s).'
        add('Radio / TV signals', note)
    add('Radio / TV signals', f'Original Nyquist {fs/2:,.0f} Hz; search around 15,625 ±30 Hz and 15,734.26 ±30 Hz.',
        sampled_sections=count)

    pil = [w.get('broadcast', {}).get('FM stereo pilot') for w in windows]
    passed = [r for r in pil if r and r.get('pass')]
    maybe = [r for r in pil if r and r.get('tentative') and not r.get('pass')]
    add('FM stereo pilot', f'19,000 Hz reference: {len(passed)} strong and {len(maybe)} tentative '
        f'peak observations across {count} excerpt(s); original Nyquist {fs/2:,.0f} Hz.',
        'The audio detector searches ±180 Hz of 19,000 and requires signal persistence across half-windows.',
        sampled_sections=count, pilot_hits=len(passed), pilot_possible=len(maybe))

    dips = [w.get('ndr') for w in windows if w.get('ndr')]
    if dips:
        strongest = max(dips, key=lambda r:r['depth_db']-r['control95'])
        add('NDR-style 10 kHz dip',
            f'Measured strongest candidate at {strongest["freq"]:,.1f} Hz: local dip {strongest["depth_db"]:.2f} dB; '
            f'95th-percentile control dip {strongest["control95"]:.2f} dB; advantage '
            f'{strongest["depth_db"]-strongest["control95"]:+.2f} dB.',
            f'Candidate appears in {strongest["occurrence"]*100:.1f}% of {strongest["frames"]} usable frames; '
            'positive detection needs enough depth, difference from controls and recurring frames.',
            notch_candidate_hz=round(strongest['freq'], 2),
            notch_depth_db=round(strongest['depth_db'], 2),
            notch_occurrence_percent=round(strongest['occurrence']*100, 1),
            notch_control_db=round(strongest['control95'], 2))
    else:
        add('NDR-style 10 kHz dip', f'0 of {count} excerpts yielded enough usable 9.3–10.7 kHz notch data; original Nyquist {fs/2:,.0f} Hz.')

    stereo = [w['stereo_corr'] for w in windows if w.get('stereo_corr') is not None]
    if stereo:
        import numpy as np
        median = float(np.median(stereo))
        add('Stereo format',
            f'Decoded {metadata.get("channels")} source channel(s). Across {len(stereo)} excerpt(s), '
            f'left/right Pearson correlation median r={median:+.4f}, range [{min(stereo):+.4f}, {max(stereo):+.4f}].',
            stereo_median_corr=round(median, 4), stereo_min_corr=round(min(stereo), 4),
            stereo_max_corr=round(max(stereo), 4))
    else:
        add('Stereo format', f'{metadata.get("channels")} source channel(s); '
            f'no valid cross-channel Pearson correlation in {count} excerpt(s).')

    phase = found.get('Stereo phase / delay', {})
    band = phase.get('metrics', {}).get('band_corr', {})
    if isinstance(band, dict) and band:
        add('Stereo phase / delay',
            'Phase-band L/R zero-lag correlations: ' + ', '.join(
                f'{name} {value:+.3f}' if isinstance(value, (float, int)) else f'{name} unavailable'
                for name, value in band.items()) + '.',
            f'Stereo analysis is computed at 11,025 Hz with ±4 ms lag search (0.091 ms sample resolution).')
    else:
        add('Stereo phase / delay', f'{count} excerpt(s); source channels: {metadata.get("channels")}; '
            'no measured band-by-band cross-channel phase was accepted.')

    periods = [w['wow'] for w in windows if w.get('wow')]
    if periods:
        best = max(periods, key=lambda x: x.get('prominence_db', 0))
        add('Wow and flutter',
            f'{len(periods)}/{count} excerpts had a trackable reference; strongest reported '
            f'{best["rate_hz"]:.3f} Hz pitch-modulation rate, RMS wobble {best["rms_cents"]:.2f} cents; '
            f'peak modulation {best["modulation_amplitude_cents"]:.2f} cents.',
            f'Wobble spectrum tests 0.3–30 Hz, with 0.556 / 0.750 / 1.300 Hz rotation benchmarks.')
    else:
        add('Wow and flutter', f'0/{count} excerpts provided a confirmed, stable reference tone '
            '(power hum / TV scanning / FM pilot) suitable for phase tracking.',
            'A lack of a reference prevents measurement; it is not evidence that the recording has zero flutter.')

    tunes = [w.get('tuning') or {} for w in windows]
    tuned = [t for t in tunes if (t.get('metrics') or {}).get('votes', 0)]
    if tuned:
        best = max(tuned, key=lambda x:x['metrics']['votes'])
        m = best['metrics']
        add('Pitch / musical tuning',
            f'Tuning test: {m["votes"]} spectral-peak votes over {m["frames"]} pitched STFT frames '
            f'from {m["notes"]} note bins; best ±13-cent cluster contains {m["fraction"]*100:.1f}% of votes.',
            'Reference convention A=440 Hz, 12-tone equal temperament; this is not a guaranteed original pitch.')
    else:
        detail = ', '.join(t.get('detail', '')[:100] for t in tunes[:2] if t.get('detail'))
        add('Pitch / musical tuning', f'{count} excerpts examined for stable pitches between 145 and 1,800 Hz; '
            f'no accepted multi-note pitch cluster. {detail}')

    references = reference_candidates(windows)
    if references:
        add('Playback speed',
            f'{len(references)} distinct reference family/families qualified: ' + ', '.join(
                f'{x["kind"]} observed {x["observed"]:,.3f} Hz / nominal {x["nominal"]:,.3f} Hz '
                f'({x["sections"]} supporting excerpt(s))' for x in references[:5]) + '.',
            'A constant pitch deviation is not proof of source speed; hum, pilot or TV tone may have been added later.',
            reference_families=len(references))
    else:
        add('Playback speed',
            f'0 confirmed frequency-reference families in {count} excerpts. '
            'Checked 50/60 Hz hum harmonics, 15,625/15,734.26 Hz TV lines and 19,000 Hz FM pilot.',
            'Without a confirmed pre-existing reference, AudioCheQ cannot measure correct original playback speed.',
            reference_families=0)

    bands = [w['bandwidth_feature'] for w in windows if w.get('bandwidth_feature')]
    if bands:
        limits = [x['range_khz'] for x in bands]
        drops = [x['drop_db'] for x in bands if x.get('drop_db') is not None]
        add('Likely audio source',
            f'Estimated high-frequency audible/noise extent {min(limits):.1f}–{max(limits):.1f} kHz '
            f'across {len(bands)} sections; ' +
            (f'FM-filter comparator median {sorted(drops)[len(drops)//2]:+.1f} dB.' if drops else 'FM-filter comparator unavailable.'),
            bandwidth_min_khz=round(min(limits), 1), bandwidth_max_khz=round(max(limits), 1))

    age = found.get('Digital file history', {})
    facts = age.get('facts', {})
    add('Digital file history', common, spans,
        f'Digital-file rate: {bitrate} kbps; encoder: {facts.get("encoder") or "not tagged"}; '
        f'encode date tag: {facts.get("encoding_date") or "not found"}; '
        f'tagging date: {facts.get("tagging_date") or "not found"}.',
        'Song release/year tags are not file creation timestamps.',
        sampled_sections=count)

    embedded = found.get('Embedded metadata') or {}
    entries = embedded.get('tags', [])
    add('Embedded metadata',
        f'{len(entries)} readable, distinct text fields; Mutagen parser: {embedded.get("parser", "unknown")}; '
        f'{embedded.get("artwork_items",0)} artwork attachments skipped.',
        *[f'{e["field"]} [{e["source"]}]: {e["value"][:200]}' for e in entries[:14]],
        'Tags may be added or changed after recording; none is an authenticated artist match.')

    rds = found.get('RDS / RadioText') or {}
    m = rds.get('metrics') or {}
    add('RDS / RadioText',
        f'Original sample rate {fs:,} Hz; Nyquist {fs/2:,.1f} Hz. On-air RDS subcarrier nominal 57,000 Hz; '
        'a complete MPX capture needs at least 128,000 samples/s.',
        f"RDS text fields embedded as file tags: {m.get('tagged_rds_fields',0)}; "
        f"validated RDS decoder groups: {m.get('rds_groups',0)}.",
        *[f'Decoded {k}: {v}' for k,v in (rds.get('decoded') or {}).items()],
        'An ordinary audio file, even one with a 19 kHz pilot trace, does not contain decodable 57 kHz RDS.')
    return rows
