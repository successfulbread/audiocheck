"""Evidence-based recording-path ranking for AudioCheQ.

These are transparent heuristic scores, NOT probabilities of original mastering
format.  An FM transmission recorded on cassette may show both signatures.
Electric-grid and television line signatures identify interference/copying paths,
not the original music medium, so they do not increase FM/analogue scores.
"""
from __future__ import annotations
import re
from math import isfinite

LABELS = ('Vinyl / Record', 'Cassette / Tape', 'FM radio', 'AM radio', 'Digital source')
CONFIRMED = ('Strong', 'High')
USABLE = CONFIRMED + ('Possible', 'Tentative')


def _number(value, default=None):
    try:
        n = float(value)
        return n if isfinite(n) else default
    except (ValueError, TypeError, OverflowError):
        return default


def score_origin(*, rotation, surface, broadcast, pilot, ndr, dropout,
                 bandwidth, metadata, stereo, phase, wow, power, speed, rds=None):
    """Return ranked clue hypothesis with reproducible, source-specific reasons.

    Score sizes encode diagnostic specificity and independence.  A verified
    19-kHz pilot is much more specific than broad frequency response.  A filter
    dip or time offset is only contextual evidence.  Avoid interpreting the
    present MP3/FLAC codec as evidence of the original recording medium.
    """
    scores = {name: 0.0 for name in LABELS}
    evidence = {name: [] for name in LABELS}
    evidence_strengths = {name: [] for name in LABELS}
    context = []

    def add(which, weight, reason, strength='support'):
        scores[which] += float(weight)
        evidence[which].append(reason)
        evidence_strengths[which].append(strength)

    rotation = rotation or {}
    surface = surface or {}
    broadcast = broadcast or {}
    pilot = pilot or {}
    ndr = ndr or {}
    dropout = dropout or {}
    bandwidth = bandwidth or {}
    metadata = metadata or {}
    stereo = stereo or {}
    phase = phase or {}
    wow = wow or {}
    power = power or {}
    speed = speed or {}
    rds = rds or {}

    # Record: surface pops and rotational clicks are stronger together.
    surface_result = str(surface.get('result', '')).lower()
    if surface.get('certainty') in USABLE and 'crackle' in surface_result and 'no ' not in surface_result:
        weight = 5.1 if surface['certainty'] in CONFIRMED else 2.5
        add('Vinyl / Record', weight, 'Measured irregular surface crackle resembles a disc transfer.', 'specific')
    rpm = str(rotation.get('result', ''))
    if rotation.get('certainty') in USABLE and re.search(r'\b(33|45|78)\s*(?:⅓\s*)?RPM\b', rpm, re.I):
        weight = 5.5 if rotation['certainty'] in CONFIRMED else 3.0 if rotation['certainty']=='Possible' else 1.4
        add('Vinyl / Record', weight, f'Click timing resembles {rpm}; drum hits can sometimes imitate this pattern.', 'specific' if weight>=3 else 'support')

    # FM: the 19k pilot is a strong medium-specific clue.  Historical 10k
    # filtering is less specific, and many ordinary FM receivers remove pilot.
    pilot_result = str(pilot.get('result', '')).lower()
    if pilot.get('certainty') in USABLE and ('pilot' in pilot_result and not pilot_result.startswith('no ')):
        weight = 9.0 if pilot['certainty'] in CONFIRMED else 5.0 if pilot['certainty']=='Possible' else 2.4
        hz = _number((pilot.get('metrics') or {}).get('measured_hz'))
        label = f'{hz:,.1f} Hz' if hz else 'near 19,000 Hz'
        add('FM radio',weight,f'A repeatable {label} pilot-like peak is characteristic of stereo FM.', 'specific' if weight>=5 else 'support')
    # Only groups actually decoded from raw FM multiplex establish RDS.
    # Plain metadata tags labelled "RDS" are not evidence of a broadcast.
    decoded = rds.get('decoded') if isinstance(rds.get('decoded'),dict) else {}
    groups = _number((rds.get('metrics') or {}).get('rds_groups'),0)
    if decoded and groups >= 1:
        add('FM radio',11.0,
            f'{int(groups)} actual RDS broadcast data group(s) decoded from this recording.', 'specific')
    if ndr.get('certainty') in USABLE and 'detected' in str(ndr.get('result','')).lower():
        m = ndr.get('metrics') or {}
        center = _number(m.get('notch_median_hz'))
        occurrences = _number(m.get('notch_sections'))
        total = _number(m.get('notch_tested_sections'))
        repeat = bool(occurrences is not None and total and occurrences / total >= .67)
        weight = 3.8 if ndr['certainty'] in CONFIRMED and repeat else 2.6 if ndr['certainty'] in CONFIRMED else 1.8
        add('FM radio',weight,
            f'A repeated broadcast-filter dip near {center:,.0f} Hz' if center else 'A 10 kHz-band broadcast-filter dip',
            'specific' if repeat else 'support')
        context.append('The 10 kHz filter is not exclusive to NDR or to FM, and could survive later tape copies.')

    bw = str(bandwidth.get('result',''))
    if 'FM-like cutoff' in bw:
        add('FM radio', 2.4, 'The treble cutoff resembles the approximately 15 kHz limit of FM broadcasting.')
        add('Cassette / Tape', .35, 'Some analog tape copies can also have limited treble.')
    elif 'Sharp cutoff' in bw:
        add('FM radio', 1.5, 'The sharp high-frequency cutoff is compatible with a filtered broadcast, but not unique to FM.')
    elif 'Limited highs' in bw:
        add('Cassette / Tape', .9, 'Weak high frequencies can be consistent with tape wear or copying.')
    elif 'Wide range' in bw:
        context.append('Wide bandwidth is not proof of a digital source; record hiss can extend well beyond the music.')

    # Dropouts and speed wobble suggest a physical transport, but neither is
    # independently a cassette fingerprint. Extreme periodic pitch tracks are
    # often a wrong harmonic; do not treat them as transport evidence.
    drops_match = re.search(r'(\d+)', str(dropout.get('result','')))
    drops = int(drops_match.group(1)) if drops_match else 0
    if drops >= 2:
        add('Cassette / Tape',min(3.0,1.2+.22*drops),
            f'{drops} brief losses of sound may be tape dropouts (editing or digital glitches also possible).')
    wm = wow.get('metrics') or {}
    wobble_cents = _number(wm.get('rms_cents'))
    wobble_rate = _number(wm.get('rate_hz'))
    wobble_good = (wow.get('certainty') in USABLE and wobble_cents is not None
                   and wobble_rate is not None and .10 <= wobble_cents <= 12.0
                   and .3 <= wobble_rate <= 12.0 and 'wow' in str(wow.get('result','')).lower())
    if wobble_good:
        add('Cassette / Tape',1.3,
            f'A reference tone wobbles {wobble_cents:.1f} cents RMS at {wobble_rate:.2f} Hz, consistent with mechanical speed variation.')
        add('Vinyl / Record',.65,'Measured pitch wobble can also come from eccentric vinyl playback.')
    elif wobble_cents is not None and wobble_cents > 12.0:
        context.append('A large pitch-variation estimate was excluded from source ranking because the tracked tone may be unreliable.')

    phase_result = str(phase.get('result','')).lower()
    if ('delay' in phase_result or 'polarity' in phase_result) and phase.get('certainty') in USABLE:
        add('Cassette / Tape', .45,
            'The channel alignment differs slightly; this can occur during analog copying or unrelated stereo processing.')
    if 'ntsc' in str(broadcast.get('result','')).lower() or 'pal' in str(broadcast.get('result','')).lower():
        context.append('A TV scanning tone points to interference in the signal chain, not necessarily to an FM or TV source.')
    if power.get('certainty') in USABLE:
        context.append('50/60 Hz electrical hum identifies possible equipment or copying-region interference, not a recording medium.')
    if speed.get('certainty') in CONFIRMED:
        context.append('A speed-reference offset may reveal an altered playback speed, but does not identify which medium caused it.')

    # AM is inherently ambiguous: narrow/mono/low-frequency audio is shared
    # with telephone, tape and encoding. Require non-sample-limited bitrate.
    narrow = re.search(r'Narrow range\s*\(\s*~([\d.]+)\s*kHz\)', bw, re.I)
    if narrow:
        cutoff = _number(narrow.group(1))
        sr = _number(metadata.get('input_rate'),0)
        channels = metadata.get('channels')
        mono = channels==1 or 'mono' in str(stereo.get('result','')).lower()
        info = (metadata.get('file_history') or {}).get('facts') or {}
        low_bit = metadata.get('codec') in ('mp3','aac','opus') and _number(info.get('bitrate_kbps'),256) <= 112
        if cutoff and cutoff <=9 and sr >=22050 and not low_bit:
            add('AM radio', 2.1 if mono else 1.2,
                f'Audio fades above {cutoff:g} kHz' + (' and is mono' if mono else '') + ', compatible with AM but also many old tape transfers.')
        elif low_bit:
            context.append('Restricted bandwidth could be caused by low-bitrate compression, rather than AM broadcast.')

    # No honest digital-origin fingerprint exists in the file container.
    # A clean copy, when no analog/broadcast signature was identified, merely
    # leaves digital as a fallback guess.
    strongest_analog = max(scores[x] for x in LABELS if x!='Digital source')
    if strongest_analog < 1.5 and 'Wide range' in bw and drops == 0:
        add('Digital source', 1.5,
            'No distinctive analog or broadcast artifact was found in this wide-band recording.')
    elif strongest_analog < .6:
        add('Digital source', .7,
            'No source-specific analog signature was strong enough to choose a medium.')

    winner=max(LABELS,key=lambda item:scores[item])
    points=scores[winner]
    runner=max((x for x in LABELS if x!=winner),key=lambda name:scores[name])
    margin=points-scores[runner]
    specific=sum(x=='specific' for x in evidence_strengths[winner])
    independent=len(evidence[winner])
    if winner=='Digital source':
        certainty='Tentative'
        result='Best guess: Digital source'
    elif winner=='AM radio':
        certainty='Possible' if points>=2.5 and margin>=1 else 'Tentative'
        result='Possible AM Radio'
    else:
        # A high-confidence verdict requires a medium-specific strong cue or
        # independent corroboration. One 10kHz notch alone stays possible.
        high= (points>=6.0 and margin>=2.8 and (specific>=1 or independent>=2))
        moderate=(points>=2.0 and margin>=.6)
        certainty='High' if high else 'Possible' if moderate else 'Tentative'
        result=('Likely ' if high else 'Possible ' if moderate else 'Tentative ') + winner
    detail_parts = evidence[winner] + context[:4]
    detail_parts.append(f'Clue ranking: {points:.1f} points vs {scores[runner]:.1f} for {runner}; these are comparative weights, not probabilities.')
    detail_parts.append('The result describes the most likely recorded/transferred signal path; several media can occur in sequence.')
    ordered=sorted(scores.items(),key=lambda x:-x[1])
    return {'result':result,'certainty':certainty,'detail':' '.join(detail_parts),
            'evidence': evidence[winner][:5], 'context':context,
            'alternative':runner,'guess_percent':None,'fallback_guess':winner=='Digital source',
            'metrics': {'clue_scores':{k:round(v,2) for k,v in ordered},
                        'leading_score':round(points,2), 'runner_up_score':round(scores[runner],2),
                        'score_margin':round(margin,2),'independent_supports':independent,
                        'specific_supports':specific}}
