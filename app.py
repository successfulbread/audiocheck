"""AudioCheQ v2.3 - readable clues, paired stereo/phase, tested NDR dip."""
from __future__ import annotations

import html
from pathlib import Path
import re
import tempfile

import streamlit as st

from analyzer import MAX_BYTES, analyze, analyze_path
from archive_source import fetch_archive_audio

st.set_page_config(page_title="AudioCheQ | Find the clues", page_icon=":material/graphic_eq:", layout="centered", initial_sidebar_state="collapsed")

st.markdown("""
<style>
html, body, .stApp {font-family:Inter,system-ui,-apple-system,"Segoe UI",sans-serif;}
.stApp {background:linear-gradient(165deg,#101827 0%,#151329 60%,#101827 100%);color:#F2F6FF;}
.block-container {max-width:980px;padding-top:1.1rem;padding-bottom:3rem;}
header[data-testid="stHeader"] {background:transparent;}
.ac-hero {position:relative;overflow:hidden;background:linear-gradient(111deg,#4F46E5 0%,#9333EA 54%,#E34E83 100%);
 border:1px solid #B9A3FF;border-radius:24px;box-shadow:0 16px 32px #03071355;padding:26px 29px;margin:0 0 20px;}
.ac-brand {position:relative;z-index:1;font-size:clamp(2.3rem,6vw,3.4rem);line-height:1.09;letter-spacing:-.05em;
 font-weight:900;color:#FFFFFF;margin:0 0 8px;text-shadow:0 2px 7px #25144755;}
.ac-brand span {color:#FFE58F;}
.ac-intro {position:relative;z-index:1;max-width:620px;font-size:1rem;color:#F9EEFF;margin:0;line-height:1.5;}
.ac-hero-mark {position:absolute;right:16px;top:12px;width:220px;height:132px;opacity:.75;pointer-events:none;}
.ac-tagline {position:relative;z-index:1;font-size:1.10rem;font-weight:850;letter-spacing:.01em;color:#FFECB9;margin:0 0 5px;}
.ac-heading {font-size:1.37rem;font-weight:850;color:#FFFFFF;margin:18px 0 12px;}
.ac-meta {font-size:.82rem;color:#B7BED2;margin:-3px 0 15px;overflow-wrap:anywhere;}
.ac-grid {display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:13px;margin-bottom:17px;}
.ac-card {border:1.7px solid;border-radius:19px;padding:16px 17px 13px;min-width:0;
 box-shadow:0 9px 24px #00000031;}
.ac-card.strong {background:linear-gradient(135deg,#D9FFED,#F2FFF8);border-color:#24CC89;}
.ac-card.good {background:linear-gradient(135deg,#DCEEFF,#F2F8FF);border-color:#43A4FF;}
.ac-card.maybe {background:linear-gradient(135deg,#FFF0CB,#FFF9EB);border-color:#F1A83B;}
.ac-card.none {background:#293143;border-color:#515A70;box-shadow:none;color:#B4BCCB;}
.ac-top {display:flex;align-items:center;gap:7px;margin-bottom:11px;}
.ac-icon {font-size:1.15rem;line-height:1.2;flex:none;}
.ac-label {font-size:.85rem;font-weight:800;color:#243F60;flex:1;}
.ac-card.none .ac-label{color:#CCD2DF;}
.ac-pill {border-radius:999px;font-size:.68rem;font-weight:850;padding:5px 9px;white-space:nowrap;}
.ac-card.strong .ac-pill {background:#A0EECC;color:#075C38;}
.ac-card.good .ac-pill {background:#A9D6FF;color:#143E76;}
.ac-card.maybe .ac-pill {background:#FFD998;color:#704306;}
.ac-card.none .ac-pill {background:#465269;color:#E0E5EF;}
.ac-sub {font-size:.8rem;font-weight:680;color:#415E79;margin-top:8px;}
.ac-result {font-size:1.23rem;line-height:1.3;font-weight:850;color:#182F56;overflow-wrap:anywhere;min-height:1.4em;}
.ac-card.none .ac-result {font-size:1.03rem;color:#E0E6F0;}
.ac-card.none .ac-sub {color:#AEB9CA;}
.ac-card details {border-top:1px solid #7482964A;margin-top:13px;padding-top:10px;overflow:hidden;}
.ac-card summary {font-size:.9rem;font-weight:800;color:#1658A8;cursor:pointer;}
.ac-card.none summary {color:#86B9FA;}
.ac-card details p,.ac-card details li {font-size:.9rem;line-height:1.57;color:#293E57;}
.ac-card details p {margin:10px 0 4px;}
.ac-card details ul {margin:9px 0 0;padding-left:20px;}
.ac-card details li {margin:6px 0;}
.ac-card.none details p,.ac-card.none details li {color:#D5DCEA;}
.ac-card.has-spectrogram {grid-column:1 / -1;}
.ac-metrics {display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:7px;
 margin:13px 0;padding:10px;background:#FFFFFF80;border-radius:10px;}
.ac-metric {display:flex;flex-direction:column;font-size:.75rem;line-height:1.34;gap:3px;color:#405570;}
.ac-metric strong {color:#172D4B;font-size:.84rem;}
.ac-card.none .ac-metrics {background:#3B465C;}
.ac-card.none .ac-metric,.ac-card.none .ac-metric strong {color:#E1E8F2;}
.ac-observation-title {font-weight:850;color:#0A5E7C;font-size:.85rem;margin:7px 0 8px;}
.ac-interpret-label {font-size:.80rem;color:#496582;font-weight:820;margin-top:13px;}
.ac-observations {background:#FFFFFF8A;border:1px solid #C7D4E2;border-radius:11px;
 padding:10px 12px 10px 30px !important;margin:8px 0 13px !important;}
.ac-observations li {font-size:.82rem !important;margin:5px 0 !important;line-height:1.48 !important;}
.ac-card.none .ac-observation-title {color:#78E4E0;}
.ac-card.none .ac-interpret-label{color:#ADC4E6;}
.ac-card.none .ac-observations{background:#36435B;border-color:#59657A;}
.ac-evidence-intro {margin-top:14px;margin-bottom:8px;color:#254C75;font-weight:850;font-size:.85rem;}
.ac-card.none .ac-evidence-intro {color:#D8E3F6;}
.ac-evidence {margin:10px 0 15px;padding:9px;background:#FFFFFF;border:1px solid #AFC5DD;border-radius:13px;}
.ac-evidence img {width:100%;height:auto;display:block;border-radius:8px;}
.ac-evidence figcaption {font-size:.8rem;color:#34455E;margin:9px 2px 0;line-height:1.48;}
.ac-card details.ac-raw {border-top:1px dashed #9EADC0;margin-top:13px;padding-top:9px;}
.ac-card details.ac-raw summary {font-size:.79rem;font-weight:700;color:#375873;}
.ac-card.none details.ac-raw summary {color:#A8D3F8;}
.ac-card details.ac-raw li {font-size:.79rem;line-height:1.5;}
.ac-card .ac-interpret-label {margin-bottom:5px;}
.ac-foot {font-size:.78rem;color:#AFBED1;margin-top:16px;}
/* Standard native Streamlit file picker: keep all clickable text readable on dark. */
.stTabs [data-baseweb="tab"] {color:#E4EBFF !important;font-weight:800 !important;}
.stTabs [aria-selected="true"] {color:#FFF1AC !important;}
[data-testid="stFileUploader"] {border:2px solid #67E5E0 !important;border-radius:16px;
 background:#24354F !important;padding:13px 14px 7px;}
[data-testid="stFileUploader"] label,
[data-testid="stFileUploader"] label p,
[data-testid="stFileUploader"] small,
[data-testid="stFileUploader"] span,
[data-testid="stFileUploader"] [data-testid="stFileDropzoneInstructions"] {color:#F8FBFF !important;opacity:1 !important;}
[data-testid="stFileUploader"] section {background:#263C58 !important;border:1.5px dashed #8BDCF2 !important;}
[data-testid="stFileUploader"] button,
[data-testid="stFileUploader"] [data-testid="baseButton-secondary"] {background:#FFF0AC !important;
 color:#182437 !important;border:2px solid #F7D659 !important;opacity:1 !important;
 font-weight:900 !important;min-height:46px;box-shadow:0 2px 0 #0003;}
[data-testid="stFileUploader"] button *,
[data-testid="stFileUploader"] button p,
[data-testid="stFileUploader"] button span {color:#182437 !important;opacity:1 !important;}
[data-testid="stFileUploader"] button:hover {background:#FFFFFF !important;}
[data-testid="stButton"] button[kind="primary"],
[data-testid="stBaseButton-primary"] {background:#46E7D0 !important;color:#10223A !important;
 border:2px solid #A4FFF2 !important;font-weight:900 !important;
 min-height:53px !important;border-radius:12px !important;opacity:1 !important;}
[data-testid="stButton"] button[kind="primary"] *,
[data-testid="stBaseButton-primary"] * {color:#10223A !important;opacity:1 !important;}
[data-testid="stButton"] button[kind="primary"]:hover,
[data-testid="stBaseButton-primary"]:hover {background:#B5FFF0 !important;}
[data-testid="stButton"] button:disabled {background:#52647A !important;color:#ECF2F8 !important;
 border-color:#61778B !important;opacity:1 !important;}
[data-testid="stButton"] button:disabled * {color:#ECF2F8 !important;opacity:1 !important;}
[data-testid="stFormSubmitButton"] button {background:#CBB7FF !important;color:#1E1B36 !important;
 border:2px solid #E8E0FF !important;font-weight:900 !important;min-height:46px !important;}
[data-testid="stFormSubmitButton"] button * {color:#1E1B36 !important;opacity:1 !important;}
/* File state label above the primary action. */
.ac-step {font-size:.99rem;font-weight:850;color:#FFFFFF;margin:9px 0 9px;}
.ac-file-ready {background:#173F47;border:1px solid #61EACD;border-radius:12px;
 padding:11px 14px;color:#ECFFF8;font-weight:750;margin:11px 0 13px;
 overflow-wrap:anywhere;}
.ac-file-waiting {font-size:.85rem;color:#C7D2E8;margin:11px 0 13px;}
@media(max-width:675px){.ac-grid{grid-template-columns:1fr;gap:11px;}
 .ac-hero{padding:21px 18px}.ac-hero-mark{width:115px;right:2px;top:2px;opacity:.23;}
 .block-container{padding-top:.55rem}.ac-card{padding:14px 15px 12px;}.ac-top{margin-bottom:8px;}}
</style>
""", unsafe_allow_html=True)

st.markdown('''<div class="ac-hero">
<svg class="ac-hero-mark" aria-hidden="true" viewBox="0 0 240 144" xmlns="http://www.w3.org/2000/svg">
 <defs><linearGradient id="ac-waves" x1="0" y1="1" x2="1" y2="0"><stop stop-color="#A8FFF2"/><stop offset="1" stop-color="#FFE58F"/></linearGradient></defs>
 <rect x="10" y="15" width="215" height="113" rx="20" fill="#170E4A" fill-opacity=".27" stroke="#C9C5FF" stroke-opacity=".40"/>
 <path d="M19 48 L36 48 L43 31 L51 72 L62 21 L72 77 L84 47 L95 48 L105 37 L114 66 L125 40 L133 48 L145 48 L155 27 L164 80 L174 48 L192 48 L202 38 L213 48" fill="none" stroke="url(#ac-waves)" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round"/>
 <path d="M23 111 L39 104 L52 106 L67 96 L80 101 L96 89 L107 91 L121 106 L135 110 L148 93 L166 87 L182 95 L198 91 L214 81" fill="none" stroke="#FFE58F" stroke-width="2.6" stroke-linecap="round"/>
 <path d="M104 107 L122 120 L137 107" fill="none" stroke="#86FFF0" stroke-width="3" stroke-linecap="round"/>
 <circle cx="122" cy="120" r="3.4" fill="#86FFF0"/>
 <text x="24" y="129" fill="#F3EFFF" font-size="9" font-weight="700" font-family="sans-serif">SIGNAL</text>
 <text x="177" y="129" fill="#F3EFFF" font-size="9" font-weight="700" font-family="sans-serif">10 kHz</text>
</svg>
<div class="ac-brand">Audio<span>CheQ</span></div>
<p class="ac-tagline">Find the story hidden in the sound.</p>
<p class="ac-intro">Audio forensics for mystery recordings: vinyl, tape, radio, pitch, speed and broadcast fingerprints.</p></div>''', unsafe_allow_html=True)

if "report" not in st.session_state:
    st.session_state.report = None
if "report_error" not in st.session_state:
    st.session_state.report_error = None
if "upload_nonce" not in st.session_state:
    st.session_state.upload_nonce = 0


def store_report(rows, meta, name, kind):
    # Do not store the uploaded bytes: only the small resulting report.
    st.session_state.report = {"rows": rows, "meta": meta, "name": name, "kind": kind}
    st.session_state.report_error = None


def meaningful(item):
    if not isinstance(item, dict):
        return False
    certainty = str(item.get("certainty", "Unclear"))
    result = str(item.get("result", "Unclear")).lower()
    return certainty in {"Strong", "High", "Possible", "Tentative"} and not any(
        phrase in result for phrase in ("none detected", "none found", "not measurable", "unclear",
                                 "no reliable", "no clear", "no distinctive", "source uncertain",
                                 "cannot assess", "high-frequency signal unavailable"))


def badge_class(item):
    if not meaningful(item):
        return "none"
    return {"Strong": "strong", "High": "strong", "Possible": "good", "Tentative": "maybe"}.get(
        str(item.get("certainty", "Unclear")), "none")


LABELS = {
    "Likely audio source": ("Likely origin", "&#9835;"),
    "Vinyl rotation": ("Record speed", "&#9673;"),
    "Likely power system": ("Power region", "&#9889;"),
    "Radio / TV signals": ("TV scanning signals", "&#9737;"),
    "FM stereo pilot": ("FM stereo pilot (19 kHz)", "&#9687;"),
    "NDR-style 10 kHz dip": ("NDR 10 kHz dip", "&#9836;"),
    "Stereo & phase": ("Stereo channels & phase", "&#8646;"),
    "Wow and flutter": ("Wow / flutter", "&#8767;"),
    "Pitch / musical tuning": ("Musical pitch / tuning", "&#9839;"),
    "Digital file history": ("Digital file age", "&#128197;"),
    "Embedded metadata": ("Embedded track metadata", "&#128209;"),
    "RDS / RadioText": ("RDS / station text", "&#128225;"),
    "Playback speed": ("Playback speed", "&#8635;"),
}


def display_result(key, item):
    raw = str(item.get("result", "Unclear")) if isinstance(item, dict) else "Unclear"
    if not meaningful(item):
        if key == "Vinyl rotation":
            return "No RPM clue"
        if key == "Likely power system":
            return "Uncertain"
        if key == "Radio / TV signals":
            return "No signal found"
        if key == "FM stereo pilot":
            return "No pilot detected"
        if key == "Wow and flutter":
            return "No measurable wobble" if str(item.get('certainty')) == 'Not measurable' else "No clear wobble"
        if key == "Pitch / musical tuning":
            return "Tuning unclear"
        if key == "Stereo phase / delay":
            return raw
        if key == "NDR-style 10 kHz dip":
            return "No 10 kHz dip"
        if key == "Possible tape dropouts":
            return "No dropouts found"
        if key == "Disc surface noise":
            return "No clear crackle"
        if key == "Playback speed":
            return "Unknown"
        if key == "Digital file history":
            return raw
        if key in ("Embedded metadata", "RDS / RadioText"):
            return raw
        return "Unclear"
    if key == "Likely audio source":
        return raw
    if key == "Vinyl rotation":
        m = re.search(r"(?:Likely|Possible) (.+? RPM)", raw)
        return m.group(1) if m else raw
    if key == "Disc surface noise":
        return "Record crackle found"
    if key == "Likely power system":
        if "50 Hz" in raw:
            return "50 Hz - likely Europe"
        if "60 Hz" in raw:
            return "60 Hz - likely N. America"
    if key == "NDR-style 10 kHz dip":
        return "10 kHz dip found"
    if key == "Radio / TV signals":
        if "NTSC" in raw:
            return "NTSC TV + FM" if "FM" in raw else "NTSC TV signal"
        if "PAL" in raw or "SECAM" in raw:
            return "PAL / SECAM TV + FM" if "FM" in raw else "PAL / SECAM TV signal"
        if "FM" in raw:
            return "FM radio pilot"
    if key == "Possible tape dropouts":
        m = re.search(r"\b(\d+)\b", raw)
        return f"{m.group(1)} possible dropouts" if m else "Possible dropouts"
    if key == "Audio bandwidth":
        return raw.replace("Audio extends to ", "Up to ")
    return raw


def why(key, item):
    """An approachable explanation. Exact measured data are shown separately."""
    item = item if isinstance(item, dict) else {}
    positive = meaningful(item)
    explanations = {
        "Likely audio source": (
            "This is the best fit for the recording's clues, not a certainty. A song can pass "
            "through radio, cassette and an MP3 copy, so more than one source can leave traces."),
        "Vinyl rotation": (
            "A record rotates once every 1.80 seconds at 33⅓ RPM, 1.33 seconds at 45 RPM "
            "or 0.77 seconds at 78 RPM. Repeated clicks at one interval can reveal the speed; "
            "random pops or drums can imitate it."),
        "Likely power system": (
            "Mains electricity can leave steady 50 or 60 Hz hum, often with extra tones at "
            "100 or 120 Hz. These are useful regional clues, but the hum might have entered "
            "during copying or digitization, not at the original studio."),
        "Radio / TV signals": (
            "An old television can leave a thin tone near 15,734.26 Hz (NTSC) or 15,625 Hz "
            "(PAL/SECAM). A repeatable peak suggests equipment interference, not necessarily "
            "that the music was recorded from television."),
        "FM stereo pilot": (
            "FM stereo uses a 19,000 Hz pilot tone to help the receiver rebuild stereo "
            "using a 38 kHz carrier. A stable peak can suggest FM reception, "
            "but receivers usually filter it out, so not finding one does not rule out FM."),
        "NDR-style 10 kHz dip": (
            "A notch is a drop in sound at a narrow range of frequencies, not a tone. "
            "Some historic German radio broadcasts have a dark band near 10 kHz; "
            "tape-speed differences can shift it above or below 10,000 Hz. "
            "We check that sound returns on BOTH sides and that the dip repeats. "
            "It cannot identify NDR by itself."),
        "Stereo & phase": (
            "Stereo compares the left and right channels. Phase measures how well they "
            "line up: a negative correlation may mean reversed polarity, and a small "
            "delay may come from tape transfer or other processing. Neither proves a tape problem."),
        "Wow and flutter": (
            "Wow is slow pitch wobble; flutter is faster vibration. Measuring them needs "
            "a steady tone, because a singer's vibrato can look similar. A repeated wobble "
            "can suggest mechanical playback but does not prove vinyl or cassette."),
        "Pitch / musical tuning": (
            "We compare musical notes with standard A=440 Hz tuning. Notes consistently "
            "sharp or flat may suggest changed pitch, but the band could simply have "
            "tuned that way. This alone cannot confirm the original playback speed."),
        "Playback speed": (
            "When an authentic 50/60 Hz hum, FM pilot or TV tone is present, its frequency "
            "can suggest a playback-speed shift. The estimate is conditional: a tone "
            "added AFTER copying tells us nothing about the original speed."),
        "Digital file history": (
            "File format, bitrate and encoder tags can date a digital copy, but not the "
            "original recording. A 1980s tape could be encoded to MP3 decades later."),
        "Embedded metadata": (
            "Tags sometimes include artist, title, source URL, recording software and "
            "comments. These fields can be edited and are not verified song identities."),
        "RDS / RadioText": (
            "Radio stations can transmit text alongside FM. Saved file tags may show "
            "it; actual over-the-air RDS needs a raw FM multiplex recording, usually "
            "containing the 57 kHz signal, and a working decoder."),
    }
    note=explanations.get(key, "This is a clue from the recording, not a certain identification.")
    if not positive:
        if key == "Likely audio source" and item.get('fallback_guess'):
            return "No distinctive source signal was strong enough to identify the original medium. Digital is a placeholder guess only. " + note
        return "This check did not establish a clear finding. " + note
    return note


def card(label, item, key=None, evidence_plots=None):
    key = key or label
    item = item if isinstance(item, dict) else {}
    cls = badge_class(item)
    pill = {"strong": "Clear clue", "good": "Good clue", "maybe": "Best guess", "none": "No clue"}[cls]
    if evidence_plots:
        cls += " has-spectrogram"
    icon = LABELS.get(key, (label, "&#9835;"))[1]
    value = display_result(key, item)
    description = why(key, item)
    sub = ""
    details_html = f'<div class="ac-interpret-label">What it means</div><p>{html.escape(description)}</p>'
    if key == "Likely audio source":
        pct = item.get("guess_percent")
        if meaningful(item) and isinstance(pct, (int, float)) and 0 < pct < 100:
            sub = f'<div class="ac-sub">~{int(pct)}% rough clue score</div>'
        evidence = item.get("evidence", [])
        facts = [str(x) for x in evidence if x] if isinstance(evidence, list) else []
        # Bandwidth supports a source guess but also has alternate causes.
        # Report the measured range and caveat in the same Why? disclosure.
        freq = item.get("frequency_clue") or {}
        if isinstance(freq, dict) and freq.get("certainty") not in ("Not measurable", "Unclear"):
            summary = str(freq.get("result") or "").strip()
            reason = str(freq.get("detail") or "").strip()
            if summary:
                facts.append("Frequency range: " + summary + (". " + reason if reason else ""))
        # Short factual list. An uncertain source still gets the frequency facts.
        if facts:
            details_html += ('<ul>' + ''.join(f'<li>{html.escape(f)}</li>' for f in facts[:4]) + '</ul>')
    elif key == "Digital file history":
        facts = item.get("facts", {}) if isinstance(item.get("facts"), dict) else {}
        fmt = str(facts.get("codec") or "").upper()
        enc = str(facts.get("encoder") or "")
        bitrate = facts.get("bitrate_kbps")
        mode = str(facts.get("bitrate_mode") or "")
        bits = [fmt] if fmt else []
        if bitrate:
            bits.append(f'{bitrate} kbps')
        if mode:
            bits.append(mode)
        if enc:
            bits.append(enc[:38])
        if bits:
            sub = f'<div class="ac-sub">{html.escape(" · ".join(bits))}</div>'
    # Only observed scalar measurements are shown. Never present derived
    # scores, reference ticks or absent arrays as detected frequencies.
    metrics = item.get('metrics') if isinstance(item.get('metrics'),dict) else {}
    metric_labels = {
        'measured_hz':'Measured pilot (Hz)', 'deviation_hz':'Pilot offset (Hz)',
        'prominence_db':'Local prominence (dB)', 'relative_db':'Level vs RMS² (dB)',
        'strong_sections':'Strong excerpts','sampled_sections':'Sampled excerpts',
        'zero_corr':'Stereo r at zero lag','aligned_corr':'Best aligned r',
        'delay_ms':'Interchannel delay (ms)','side_mid_db':'Side / mid (dB)',
        'speed_error_percent':'Apparent speed error (%)',
        'correction_percent':'Conditional correction (%)',
        'pitch_offset_cents':'Reference pitch shift (cents)',
        'deviation_cents':'A440 tuning bias (cents)',
        'hypothetical_correction_percent':'Tuning-only hypothetical speed (%)',
        'votes':'Spectral-peak votes', 'frames':'Pitched frames',
        'fraction':'Within tuning cluster (fraction)',
        'notes':'Distinct semitone bins',
        'rms_cents':'Pitch wobble RMS (cents)',
        'rate_hz':'Strongest modulation rate (Hz)',
        'modulation_amplitude_cents':'Modulation peak (cents)',
        'tone_hz':'Tracked tone (Hz)',
        'nominal_hz':'Reference frequency (Hz)',
        'embedded_fields':'Readable tag fields','tag_sources':'Tag parser sources',
        'rds_tag_fields':'RDS-named tag fields','artwork_items':'Artwork attachments',
        'tagged_rds_fields':'RDS-named tag fields','rds_groups':'Validated RDS groups',
        'rds_band_contrast_db':'57 kHz band vs controls (dB)',
        'pilot_prominence_db':'19 kHz pilot prominence (dB)',
        'input_sample_rate_hz':'File sample rate (Hz)', 'nyquist_hz':'File Nyquist (Hz)',
        'analyzed_seconds':'Audio examined (s)','possible_interruptions':'Level interruptions',
        'bandwidth_min_khz':'Minimum sampled extent (kHz)',
        'bandwidth_max_khz':'Maximum sampled extent (kHz)',
        'notch_candidate_hz':'Strongest dip centre (Hz)',
        'notch_median_hz':'Typical dip centre (Hz)',
        'notch_depth_db':'Notch depth (dB)',
        'notch_control_db':'Control notch depth (dB)',
        'notch_occurrence_percent':'Notch persistence (%)',
        'notch_sections':'Sections with notch',
        'notch_width_hz':'Dip width scale (Hz)',
        'level_difference_db':'Left/right level difference (dB)',
        'pilot_hits':'Strong pilot excerpts','pilot_possible':'Weak pilot excerpts',
        'matched_sections':'Rotation-match excerpts','click_events':'Matched click events',
        'fitted_rotation_period_s':'Fitted revolution (s)',
        'click_fit_error_ms':'Click-grid RMS error (ms)',
        'stereo_median_corr':'Median stereo correlation',
        'stereo_min_corr':'Minimum stereo correlation',
        'stereo_max_corr':'Maximum stereo correlation',
        'reference_families':'Qualified reference families',
    }
    key_metrics={
        'Likely audio source':('sampled_sections','analyzed_seconds','possible_interruptions'),
        'Vinyl rotation':('matched_sections','click_events','fitted_rotation_period_s','click_fit_error_ms'),
        'Likely power system':('sampled_sections',),
        'Radio / TV signals':('sampled_sections',),
        'FM stereo pilot':('pilot_hits','pilot_possible','measured_hz','prominence_db'),
        'NDR-style 10 kHz dip':('notch_median_hz','notch_depth_db','notch_occurrence_percent','notch_sections'),
        'Stereo & phase':('stereo_median_corr','zero_corr','delay_ms','level_difference_db'),
        'Wow and flutter':('tone_hz','rms_cents','rate_hz','modulation_amplitude_cents'),
        'Pitch / musical tuning':('deviation_cents','votes','notes','frames'),
        'Playback speed':('speed_error_percent','correction_percent','reference_families'),
        'Digital file history':('analyzed_seconds',),
        'Embedded metadata':('embedded_fields','rds_tag_fields','artwork_items'),
        'RDS / RadioText':('rds_groups','rds_band_contrast_db','rds_tag_fields','input_sample_rate_hz'),
    }
    scalar_lines=[]
    for metric in key_metrics.get(key,tuple(metric_labels)[:4]):
        title=metric_labels.get(metric,metric)
        metric_value=metrics.get(metric)
        if isinstance(metric_value,(int,float)) and not isinstance(metric_value,bool):
            scalar_lines.append('<div class="ac-metric"><span>'+html.escape(title)+'</span>'+
                                '<strong>'+html.escape(str(metric_value))+'</strong></div>')
    if scalar_lines:
        details_html = '<div class="ac-observation-title">Key measurements</div><div class="ac-metrics">'+''.join(scalar_lines)+'</div>' + details_html
    observations = item.get('observations', [])
    if isinstance(observations,list) and observations:
        notes=[str(x)[:600] for x in observations if x]
        # Preserve the actual measurements for audiophiles, without flooding
        # the first Why? view with FFT jargon and every failed control test.
        details_html += ('<details class="ac-raw"><summary>Full measurements and testing details</summary>'
                         '<ul>' + ''.join(f'<li>{html.escape(x)}</li>' for x in notes[:22]) +
                         (f'<li>{html.escape(str(item.get("detail") or ""))}</li>' if item.get('detail') else '') +
                         '</ul></details>')
    elif item.get('detail'):
        details_html += ('<details class="ac-raw"><summary>Additional technical details</summary>'
                         '<p>'+html.escape(str(item['detail']))+'</p></details>')
    if evidence_plots:
        details_html += '<div class="ac-evidence-intro">Measured audio evidence · peak plots</div>'
        for entry in evidence_plots[:2]:
            img = entry.get('image_base64', '')
            if not isinstance(img, str) or not re.fullmatch(r'[A-Za-z0-9+/=]{100,400000}', img):
                continue
            caption = html.escape(str(entry.get('caption','')))
            details_html += ('<figure class="ac-evidence">'
                             '<img loading="lazy" alt="Measured audio evidence chart" '
                             f'src="data:image/png;base64,{img}" />'
                             f'<figcaption>{caption}</figcaption>'
                             '</figure>')
    return (f'<section class="ac-card {cls}">' 
            f'<div class="ac-top"><span class="ac-icon">{icon}</span>'
            f'<span class="ac-label">{html.escape(label)}</span>'
            f'<span class="ac-pill">{pill}</span></div>'
            f'<div class="ac-result">{html.escape(value)}</div>{sub}'
            f'<details><summary>Why?</summary>{details_html}</details>'
            f'</section>')


def summary(found):
    found = found if isinstance(found, dict) else {}
    source = found.get("Likely audio source") or {}
    raw = str(source.get("result", "")).lower()
    statements = []
    if "record" in raw or "vinyl" in raw:
        statements.append("The pops and crackle point to a record transfer.")
    elif "cassette" in raw:
        statements.append("Tape-like dropouts suggest a cassette copy.")
    elif "fm radio" in raw:
        statements.append("An FM pilot or cutoff suggests a radio recording.")
    elif "am radio" in raw:
        statements.append("Narrow mono audio may come from AM radio.")
    elif "digital" in raw:
        statements.append("A clean, wide-range signal may be digital.")
    else:
        statements.append("The source is hard to distinguish.")
    if meaningful(found.get("NDR-style 10 kHz dip")):
        statements.append("A 10 kHz dip was found.")
    if meaningful(found.get("FM stereo pilot")):
        statements.append("A separate 19 kHz FM pilot clue was found.")
    if meaningful(found.get("Playback speed")):
        statements.append("A conditional playback-speed estimate is available.")
    return " ".join(statements)


def merged_stereo(items):
    """One visible finding from the independently computed channel and phase checks."""
    fmt=items.get('Stereo format') or {}
    phase=items.get('Stereo phase / delay') or {}
    if not fmt and not phase:
        return {'result':'Unclear','certainty':'Not measurable'}
    f=str(fmt.get('result') or '')
    p=str(phase.get('result') or '')
    if f=='Mono' or p=='Single-channel file':
        result,certainty='Mono file','High'
    elif 'polarity' in p.lower() or 'opposite-phase' in p.lower():
        result,certainty='Stereo • phase difference','Possible'
    elif 'delay' in p.lower() and 'channel' in p.lower():
        result,certainty='Stereo • channel delay','Possible'
    elif 'identical' in p.lower() or 'dual mono' in f.lower():
        result,certainty='Dual mono / near-mono','High'
    elif f=='Stereo' or 'stereo channels' in p.lower():
        result,certainty='Stereo channels','High'
    else:
        result,certainty=f or p or 'Unclear',fmt.get('certainty') or 'Unclear'
    metrics=dict(fmt.get('metrics') or {})
    metrics.update(phase.get('metrics') or {})
    measurements=list(fmt.get('observations') or [])+list(phase.get('observations') or [])
    detail=('File channel format: '+f+'. ' if f else '')+(str(phase.get('detail') or ''))
    return {'result':result,'certainty':certainty,'detail':detail,
            'metrics':metrics,'observations':measurements}


def sorted_findings(rows):
    items=dict(rows or [])
    # Compatible with older analyzer rows while showing a single combined card.
    items['Stereo & phase']=merged_stereo(items)
    priority=list(LABELS)
    level={'strong':3,'good':2,'maybe':1,'none':0}
    sorted_keys=sorted(priority,key=lambda k:(-level[badge_class(items.get(k,{}))],priority.index(k)))
    return [(key,items.get(key,{'certainty':'Unclear','result':'Unclear'})) for key in sorted_keys]


st.markdown('<div class="ac-heading">Check a song</div>', unsafe_allow_html=True)
file_tab, archive_tab = st.tabs(["Upload audio", "Archive.org link"])
with file_tab:
    # Regular Streamlit uploader OUTSIDE a form: the selected filename appears
    # as soon as the browser has successfully delivered the file to Streamlit.
    st.markdown('<div class="ac-step">1. Choose an audio file</div>', unsafe_allow_html=True)
    uploaded = st.file_uploader(
        "Select MP3, WAV, FLAC, M4A or OGG (max 5 minutes / 100 MB)",
        type=["mp3", "mpeg", "mpga", "wav", "flac", "ogg", "m4a"],
        accept_multiple_files=False,
        max_upload_size=100,
        key=f"audio_file_{st.session_state.upload_nonce}",
        help="Pick one file. Its name appears below when it has reached the app.",
    )
    if uploaded is not None:
        ready_name = html.escape(Path(uploaded.name).name)
        ready_mb = uploaded.size / (1024 * 1024)
        st.markdown(
            f'<div class="ac-file-ready">&#10003; File received: {ready_name} '
            f'({ready_mb:.1f} MB)</div>', unsafe_allow_html=True)
    else:
        st.markdown(
            '<div class="ac-file-waiting">Your selected filename will appear here. '
            'Then press Analyze.</div>', unsafe_allow_html=True)
    st.markdown('<div class="ac-step">2. Analyze</div>', unsafe_allow_html=True)
    pressed = st.button(
        "ANALYZE SELECTED AUDIO", key="analyze_upload", type="primary",
        use_container_width=True, disabled=uploaded is None,
    )
    if pressed and uploaded is not None:
        st.session_state.report_error = None
        if uploaded.size > MAX_BYTES:
            st.session_state.report_error = "File too large (100 MB max)."
        else:
            try:
                with st.spinner("Listening for clues..."):
                    name = Path(uploaded.name).name
                    rows, meta = analyze(uploaded.getvalue(), name, charts=True)
                store_report(rows, meta, name, "Upload")
                # Incrementing the key drops the previous browser selection.
                st.session_state.upload_nonce += 1
                st.rerun()
            except ValueError as exc:
                st.session_state.report_error = str(exc)
            except Exception:
                st.session_state.report_error = "Analysis failed. Check the app logs."
with archive_tab:
    with st.form("archive_form", enter_to_submit=False):
        archive_link = st.text_input("Direct audio file URL", placeholder="https://archive.org/download/record-id/track.mp3")
        archive_allowed = st.checkbox("I may download and analyze this recording")
        archive_submit = st.form_submit_button("Analyze archive audio", use_container_width=True)
    if archive_submit:
        st.session_state.report_error = None
        if not archive_link.strip():
            st.session_state.report_error = "Paste a direct Internet Archive audio-file link."
        elif not archive_allowed:
            st.session_state.report_error = "Confirm you have permission to analyze the audio."
        else:
            try:
                with st.spinner("Fetching archive audio..."):
                    with tempfile.TemporaryDirectory(prefix="audiocheck_archive_") as td:
                        path, title = fetch_archive_audio(archive_link, Path(td))
                        rows, meta = analyze_path(path, title, charts=True)
                store_report(rows, meta, title, "Archive")
            except ValueError as exc:
                st.session_state.report_error = str(exc)
            except Exception:
                st.session_state.report_error = "This archive link could not be analyzed. Try uploading the MP3."

if st.session_state.report_error:
    st.error(st.session_state.report_error)

report = st.session_state.report
if report:
    meta = report.get("meta", {})
    name = html.escape(str(report.get("name", "Recording")))
    duration = float(meta.get("duration", 0))
    st.markdown('<div class="ac-heading">What we found</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="ac-meta">{name} &middot; {duration:.0f} sec</div>', unsafe_allow_html=True)
    results = sorted_findings(report.get("rows", []))
    plots = meta.get("spectrograms", {})
    st.markdown('<div class="ac-grid">' + "".join(
        card(LABELS[key][0], item, key, evidence_plots=(plots.get('Stereo phase / delay',[]) if key=='Stereo & phase' else plots.get(key,[])))
        for key, item in results) + '</div>', unsafe_allow_html=True)
    with st.expander("File details & all embedded tags"):
        info = meta.get("file_history", {}).get("facts", {})
        bits = info.get("bitrate_kbps")
        rate_text = f" · {bits} kbps" if bits else ""
        st.caption(f'Codec: {meta.get("codec", "unknown")}{rate_text} · '
                   f'Sample rate: {meta.get("input_rate", "?")} Hz · '
                   f'Channels: {meta.get("channels", "?")} · '
                   f'Container: {meta.get("container", "unknown")} · '
                   f'Sample type: {meta.get("sample_fmt") or "unknown"} · '
                   f'Stored bit depth: {meta.get("bits_per_sample") or "unknown"} · '
                   f'Size: {meta.get("file_size_bytes", 0):,} bytes · '
                   f'Analyzed: {meta.get("analyzed_seconds", 0):.1f} s')
        tags = meta.get('embedded_metadata') or {}
        entries = tags.get('tags', []) if isinstance(tags, dict) else []
        st.markdown(f'**Embedded fields:** {len(entries)} (artwork is not displayed).'
                 ' These are editable file tags, not authenticated song identifications.')
        if entries:
            st.dataframe(entries, hide_index=True, use_container_width=True)
        else:
            st.caption('No readable track / station / encoder text fields were found in this file.')
        rds = meta.get('rds') or {}
        found_rds = rds.get('decoded') or {}
        if found_rds:
            st.markdown('**Decoded over-the-air RDS**')
            st.dataframe([{'field': k, 'value': v} for k, v in found_rds.items()],
                         hide_index=True, use_container_width=True)
        else:
            st.caption('No on-air RadioText, station name or RT+ artist/title was decoded.')
    st.markdown('<div class="ac-foot">Fun clues, not proof. Noise can come from a later recording or copy.</div>',
                unsafe_allow_html=True)
