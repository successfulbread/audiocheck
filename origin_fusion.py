"""Rank audible recording paths using independent, observable clues.

These scores are explanatory heuristics, not calibrated probabilities of the
original master. A cassette recording of FM can contain *both* signatures.
An FM verdict requires a measured, plausible FM-bandwidth filter, not just a
pilot-like electronic tone or a historic 10 kHz notch.
"""
from __future__ import annotations
import math
import re
from math import isfinite

LABELS = ('Vinyl / Record', 'Cassette / Tape', 'FM radio', 'AM radio',
          'TV / Video signal', 'Digital source')
CONFIRMED = ('Strong', 'High')
USABLE = CONFIRMED + ('Possible', 'Tentative')


def _number(value, default=None):
    try:
        n = float(value)
        return n if isfinite(n) else default
    except (ValueError, TypeError, OverflowError):
        return default


def _fm_cutoff(bandwidth, metadata):
    """True only for a measured ~15 kHz steep rolloff not explained by codec.

    An MP3 encoded at low bitrate can manufacture a very similar cutoff;
    do not use it as positive FM evidence. A missing measurement is not a pass.
    """
    m = bandwidth.get('metrics') or {}
    cutoff = _number(m.get('estimated_cutoff_khz'))
    drop = _number(m.get('median_15khz_drop_db'))
    sharp = _number(m.get('sharp_sections'), 0)
    count = _number(m.get('tested_sections'), 0)
    nyquist = _number(m.get('nyquist_khz'), _number(metadata.get('input_rate'), 0)/2000)
    bitrate = _number(m.get('codec_bitrate_kbps'))
    if bitrate is None:
        bitrate = _number(((metadata.get('file_history') or {}).get('facts') or {}).get('bitrate_kbps'))
    codec = str(metadata.get('codec') or '').lower()
    lossy_limited = codec in ('mp3','aac','opus','vorbis') and bitrate is not None and bitrate < 176
    is_sharp = bool(sharp >= max(1, math.ceil(count*.5)) and count >= 1 and drop is not None and drop >= 18)
    return bool(not lossy_limited and cutoff is not None and 13.5 <= cutoff <= 16.7
                and nyquist >= 18 and is_sharp), cutoff, drop


def score_origin(*, rotation, surface, broadcast, pilot, ndr, dropout,
                 bandwidth, metadata, stereo, phase, wow, power, speed,
                 rds=None, hiss=None):
    """Give a ranked best guess with measured supporting evidence and caveats."""
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
    hiss = hiss or {}

    # A record's random surface crackle AND recurring RPM-related clicks are
    # strong, complementary clues; do not count percussion as conclusive.
    s = str(surface.get('result', '')).lower()
    if surface.get('certainty') in USABLE and 'crackle' in s and not s.startswith('no '):
        w = 7.2 if surface['certainty'] in CONFIRMED else 3.6 if surface['certainty']=='Possible' else 1.7
        add('Vinyl / Record', w, 'Irregular disc-like crackle was measured, including quieter moments when drumbeats are less likely.',
            'specific' if w >= 3.5 else 'support')
    rpm = str(rotation.get('result', ''))
    if rotation.get('certainty') in USABLE and re.search(r'\b(33|45|78)\s*(?:⅓\s*)?RPM\b', rpm, re.I):
        w = 6.5 if rotation['certainty'] in CONFIRMED else 4.0 if rotation['certainty']=='Possible' else 2.0
        add('Vinyl / Record', w, f'Repeated clicks fit {rpm}; musical rhythm can sometimes imitate a revolving disc.',
            'specific' if w>=4 else 'support')

    # Broadband hiss is common on analog tape, but is not tape-specific. Only
    # a fairly steady broadband floor earns weight: high cymbals or electronic
    # music alone can resemble hiss.
    hm = hiss.get('metrics') or {}
    hiss_result = str(hiss.get('result', '')).lower()
    if hiss.get('certainty') in USABLE and 'hiss' in hiss_result and 'no ' not in hiss_result:
        strength = 'specific' if hiss.get('certainty') in CONFIRMED else 'support'
        w = 4.8 if hiss.get('certainty') in CONFIRMED else 2.8 if hiss.get('certainty')=='Possible' else 1.3
        pers = _number(hm.get('persistent_percent'))
        level = _number(hm.get('quiet_hiss_dbfs'))
        pieces = []
        if pers is not None: pieces.append(f'{pers:.0f}% of checked quieter frames')
        if level is not None: pieces.append(f'around {level:.0f} dBFS')
        at = ' ('+', '.join(pieces)+')' if pieces else ''
        add('Cassette / Tape',w,'A sustained broadband hiss-like noise floor'+at+' is consistent with tape copying, but not unique to cassette.',strength)
        add('Vinyl / Record', .35 if w>=3 else .20, 'Records and analog transfers can also retain broadband background hiss.')

    # Intermittent losses favour tape; a few cuts could instead be an edit.
    drops_match = re.search(r'(\d+)', str(dropout.get('result','')))
    drops = int(drops_match.group(1)) if drops_match else 0
    if drops >= 2:
        add('Cassette / Tape', min(5.4, 2.6 + .40*drops),
            f'{drops} brief sound dropouts can be caused by damaged or poorly contacting tape.',
            'specific' if drops >= 3 else 'support')

    wm = wow.get('metrics') or {}
    wobble_cents = _number(wm.get('rms_cents'))
    wobble_rate = _number(wm.get('rate_hz'))
    wobble_pm = _number(wm.get('prominence_db'), 12)
    wobble_good = (wow.get('certainty') in USABLE and wobble_cents is not None
                   and wobble_rate is not None and 0.10 <= wobble_cents <= 12.0
                   and 0.30 <= wobble_rate <= 12.0 and wobble_pm >= 6
                   and ('wow' in str(wow.get('result','')).lower() or
                        'flutter' in str(wow.get('result','')).lower()))
    if wobble_good:
        matched = next(((label, hz) for label,hz in (('33⅓ RPM', 1/1.8),
                         ('45 RPM', .75), ('78 RPM', 1.30))
                        if abs(wobble_rate-hz)/hz <= .045), None)
        if matched and wobble_rate <= 1.45:
            add('Vinyl / Record', 4.9 if wow.get('certainty') in CONFIRMED else 3.4,
                f'Pitch wobbles about {wobble_rate:.3f} times per second, near the {matched[0]} rotation rate; an off-centre record can do this.', 'specific')
            add('Cassette / Tape', .5, 'Tape transports can also produce regular pitch wobble.')
        else:
            weight = 3.9 if wow.get('certainty') in CONFIRMED else 2.9
            add('Cassette / Tape', weight,
                f'The measured pitch varies {wobble_cents:.1f} cents RMS at {wobble_rate:.2f} cycles/second, consistent with mechanical tape-transport instability.',
                'specific' if wow.get('certainty') in CONFIRMED else 'support')
            add('Vinyl / Record',1.2,'Turntable motors can cause similar pitch fluctuations.')
    elif wobble_cents is not None and wobble_cents > 12:
        context.append('An implausibly large pitch variation was excluded because the tone tracker may have followed music instead of the reference.')

    phase_result = str(phase.get('result','')).lower()
    if ('delay' in phase_result or 'polarity' in phase_result) and phase.get('certainty') in USABLE:
        add('Cassette / Tape', .4, 'The channels differ slightly in timing or polarity; tape azimuth or later stereo processing may cause this.')

    bw = str(bandwidth.get('result',''))
    fm_gate, fm_cut, fm_drop = _fm_cutoff(bandwidth,metadata)
    if 'Limited highs' in bw or 'Narrow range' in bw:
        add('Cassette / Tape', .9, 'Some treble is missing, which can result from aging tape or repeated analog copies.')
    if 'Wide range' in bw:
        context.append('Wide frequency range alone does not establish a digital original; record/tape hiss can extend above the music.')

    # A 19k pilot and a 10k notch are recorded as observations regardless of
    # the result. For an *FM verdict*, additionally require a measured FM-like
    # 15k audio cutoff not explained by low-bitrate encoding.
    pr = str(pilot.get('result','')).lower()
    pilot_found = (pilot.get('certainty') in USABLE and 'pilot' in pr
                   and not pr.startswith('no ') and 'unavailable' not in pr)
    ndr_found = (ndr.get('certainty') in USABLE and 'detected' in str(ndr.get('result','')).lower())
    decoded = rds.get('decoded') if isinstance(rds.get('decoded'),dict) else {}
    groups = _number((rds.get('metrics') or {}).get('rds_groups'),0)
    rds_real = bool(decoded and groups>=1)
    if fm_gate:
        add('FM radio',2.4,
            f'A steep audio cutoff around {fm_cut:.1f} kHz ({fm_drop:.1f} dB drop) matches the usual ~15 kHz FM audio limit; digital processing can imitate it.') if (pilot_found or ndr_found or rds_real) else None
        if pilot_found:
            w = 9.0 if pilot['certainty'] in CONFIRMED else 5.0 if pilot['certainty']=='Possible' else 2.3
            hz = _number((pilot.get('metrics') or {}).get('measured_hz'))
            add('FM radio', w,
                f'A repeatable {hz:,.1f} Hz stereo pilot-like tone accompanies the cutoff.' if hz else
                'A repeatable 19 kHz stereo pilot-like tone accompanies the cutoff.',
                'specific' if w>=5 else 'support')
        if ndr_found:
            m = ndr.get('metrics') or {}
            cen = _number(m.get('notch_median_hz'))
            occ = _number(m.get('notch_sections'),0)
            total = _number(m.get('notch_tested_sections'),0)
            repeat = bool(total and occ/total>=.67)
            w=3.2 if ndr.get('certainty') in CONFIRMED and repeat else 2.1 if ndr.get('certainty') in CONFIRMED else 1.1
            add('FM radio',w,
                f'A repeated broadcast-chain filter dip near {cen:,.0f} Hz supports a filtered radio path.' if cen else
                'A 10 kHz-band filter dip supports a radio-processing path, but is not specific to FM.',
                'support')
        if rds_real:
            add('FM radio',11.,f'{int(groups)} RDS group(s) actually decoded from raw FM multiplex data.', 'specific')
    else:
        if pilot_found or ndr_found or rds_real:
            # This explicit gate matters: without cutoff the presence of
            # 19k electronic noise or 10k notch cannot force an FM verdict.
            context.append('FM was not ranked because a reliable FM-style ~15 kHz audio cutoff was not measured. A pilot-like tone or 10 kHz filter dip alone does not meet this requirement.')
    if ndr_found:
        context.append('A 10 kHz-band notch is a broadcast/copying filter clue, not proof of NDR or FM.')
    if fm_gate and not (pilot_found or ndr_found or rds_real):
        context.append('The 15 kHz-type cutoff was found, but without an independent FM clue it cannot identify FM on its own.')

    tv_result = str(broadcast.get('result','')).lower()
    if any(name in tv_result for name in ('ntsc', 'pal/secam', 'tv interference')) and broadcast.get('certainty') in USABLE:
        add('TV / Video signal',4.0 if broadcast.get('certainty') in CONFIRMED else 2.4,
            'A steady TV scan-frequency tone suggests a television/video stage or nearby-screen interference, not necessarily a televised song.')
    if power.get('certainty') in USABLE:
        context.append('50/60 Hz electrical hum points to equipment or the copying chain, not a particular music format.')
    if speed.get('certainty') in CONFIRMED:
        context.append('A reference-frequency offset can suggest changed speed but cannot identify the playback medium.')

    # AM-style narrow response is weak and non-exclusive.
    narrow = re.search(r'Narrow range\s*\(\s*~([\d.]+)\s*kHz\)',bw,re.I)
    if narrow:
        cutoff = _number(narrow.group(1))
        sr = _number(metadata.get('input_rate'),0)
        mono = metadata.get('channels')==1 or 'mono' in str(stereo.get('result','')).lower()
        info = ((metadata.get('file_history') or {}).get('facts') or {})
        low_bit = str(metadata.get('codec','')).lower() in ('mp3','aac','opus') and _number(info.get('bitrate_kbps'),256)<=112
        if cutoff and cutoff<=9 and sr>=22050 and not low_bit:
            add('AM radio',2.1 if mono else 1.2,
                f'Audio fades above {cutoff:g} kHz'+(' and is mono' if mono else '')+'; this is compatible with AM, but also telephone or tape filtering.')
        elif low_bit:
            context.append('Low-bitrate compression may explain the restricted treble without an AM broadcast.')

    # Digital is a *fallback*, never inferred from the format of the uploaded
    # file. After a non-FM-specific notch, we still cannot tell the medium.
    strongest = max(scores[x] for x in LABELS if x != 'Digital source')
    if strongest < .6:
        add('Digital source',1.5 if 'Wide range' in bw and drops==0 else .7,
            'No distinctive analog source artifact was confirmed; this is only a fallback guess.')

    winner=max(LABELS,key=lambda item:scores[item])
    points=scores[winner]
    runner=max((x for x in LABELS if x!=winner),key=lambda name:scores[name])
    margin=points-scores[runner]
    specific=sum(x=='specific' for x in evidence_strengths[winner])
    independent=len(evidence[winner])
    if winner == 'Digital source':
        percent=38 if points>=1.5 else 32
    else:
        dominance=points/(points+scores[runner]+2.7) if points else 0.0
        completeness=min(1.,points/7.)
        percent=round(35+62*dominance*completeness)
        if winner in ('AM radio','TV / Video signal') and specific<1:
            percent=min(percent,64)
        if winner=='FM radio' and not (pilot_found or rds_real):
            percent=min(percent,72)
        if winner=='Cassette / Tape' and independent<2:
            percent=min(percent,60)
        percent=max(26,min(95,percent))
    if winner=='Digital source':
        certainty='Tentative'
        result='Best guess: Digital source'
    else:
        certainty='High' if percent>=70 and (specific or independent>=2) else 'Possible' if percent>=48 else 'Tentative'
        result=('Likely ' if certainty=='High' else 'Possible ' if certainty=='Possible' else 'Tentative ')+winner
    if winner=='TV / Video signal':
        result=('Possible ' if certainty!='Tentative' else 'Tentative ')+'TV / video-related signal'
        certainty='Possible' if certainty=='High' else certainty
    detail_parts=evidence[winner]+context[:4]
    detail_parts.append(f'Leading clue score {points:.1f}; runner-up {runner} at {scores[runner]:.1f}.')
    detail_parts.append('The percentage is a heuristic evidence score, not a measured probability of the original master format.')
    detail_parts.append('A recording may pass through radio, tape, disc and digital copies in succession.')
    ordered=sorted(scores.items(),key=lambda x:-x[1])
    return {'result':result,'certainty':certainty,'detail':' '.join(detail_parts),
            'evidence':evidence[winner][:6], 'context':context,
            'alternative':runner,'guess_percent':int(percent),
            'fallback_guess':winner=='Digital source',
            'metrics':{'clue_scores':{k:round(v,2) for k,v in ordered},
                       'leading_score':round(points,2),'runner_up_score':round(scores[runner],2),
                       'score_margin':round(margin,2),'independent_supports':independent,
                       'specific_supports':specific,'confidence_percent':int(percent),
                       'source_rank':winner,'fm_cutoff_qualifies':fm_gate,
                       'fm_cutoff_khz':round(fm_cut,2) if fm_cut else None}}
