"""AudioCheQ v1.8 - standard two-step upload and legible high-contrast buttons."""
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
.ac-hero-mark {position:absolute;right:20px;top:12px;width:155px;height:95px;opacity:.66;pointer-events:none;}
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
.ac-evidence-intro {margin-top:14px;margin-bottom:8px;color:#254C75;font-weight:850;font-size:.85rem;}
.ac-card.none .ac-evidence-intro {color:#D8E3F6;}
.ac-evidence {margin:10px 0 15px;padding:9px;background:#FFFFFF;border:1px solid #AFC5DD;border-radius:13px;}
.ac-evidence img {width:100%;height:auto;display:block;border-radius:8px;}
.ac-evidence figcaption {font-size:.8rem;color:#34455E;margin:9px 2px 0;line-height:1.48;}
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
 .ac-hero{padding:21px 18px}.ac-hero-mark{width:110px;right:2px;top:2px;opacity:.28;}
 .block-container{padding-top:.55rem}.ac-card{padding:14px 15px 12px;}.ac-top{margin-bottom:8px;}}
</style>
""", unsafe_allow_html=True)

st.markdown('''<div class="ac-hero">
<svg class="ac-hero-mark" aria-hidden="true" viewBox="0 0 160 92" xmlns="http://www.w3.org/2000/svg">
 <g fill="none" stroke="#9FF8EA" stroke-width="6" stroke-linecap="round">
 <path d="M12 48V37M30 65V20M48 77V11M66 60V29M84 83V7M102 58V32M120 72V17M138 54V38"/>
 </g>
</svg>
<div class="ac-brand">Audio<span>CheQ</span></div>
<p class="ac-intro">Discover clues to a song's source, record speed, broadcast signals and digital file history.</p></div>''', unsafe_allow_html=True)

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
    "Radio / TV signals": ("Radio / TV signal", "&#9737;"),
    "NDR-style 10 kHz dip": ("NDR 10 kHz dip", "&#9836;"),
    "Stereo format": ("Stereo / mono", "&#8644;"),
    "Digital file history": ("Digital file age", "&#128197;"),
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
    item = item if isinstance(item, dict) else {}
    raw = str(item.get("result", "Unclear"))
    detail = str(item.get("detail") or "").strip()
    positive = meaningful(item)

    # Preserve measured numbers provided by the signal analyzer; do not
    # invent measured peak positions, click counts, or confidence statistics.
    if not positive:
        defaults = {
            "Likely audio source": "No measured artifact reliably separated record, tape, radio and digital sources.",
            "Vinyl rotation": "No stable series of clicks matched 33⅓, 45 or 78 RPM closely enough.",
            "Likely power system": "No stable 50/60 Hz pattern or distinctive harmonics were found.",
            "Radio / TV signals": "No sufficiently persistent, narrow 15,625 / 15,734 Hz TV tone or 19,000 Hz FM pilot was measured.",
            "NDR-style 10 kHz dip": "No narrow, persistent reduction of energy around 10 kHz was established.",
            "Stereo format": "The channels could not be distinguished reliably.",
            "Digital file history": "No trustworthy encoder version or encoding-date tag was identified.",
            "Playback speed": "Overall speed needs a known reference tone or comparison recording.",
        }
        note = detail or defaults.get(key, "The audio did not provide enough evidence.")
        if key == "Likely power system":
            note += " The test examines persistent narrow peaks near 50/60 Hz and their 100/120 Hz harmonics; musical bass can imitate a single peak."
        elif key == "Radio / TV signals":
            note += " A dashed guide in the graph marks the expected frequency; it is not a detected signal."
        elif key == "NDR-style 10 kHz dip":
            note += " A true notch is a dip (less energy), not a 10 kHz tone: it would look like a dark gap in the spectrogram and needs broadband audio around that band."
        elif key == "Vinyl rotation":
            note += " Random record crackle can still indicate vinyl without revealing the RPM."
        elif key == "Digital file history":
            note += " Track-year metadata is not evidence of when this file was encoded."
        return note

    if key == "Likely audio source":
        if item.get("fallback_guess"):
            return "No reliable source-specific clue was measured. Digital is a placeholder best guess, NOT evidence that the original recording was digital. A clean tape or record can sound the same."
        return "The source estimate combines clicks, surface noise, tape interruptions, broadcast tones and bandwidth. The score ranks clues; it is not a calibrated probability."
    if key == "Vinyl rotation":
        rpm = re.search(r"(33[⅓ ]*|45|78)\s*RPM", raw, re.I)
        ref = ""
        if rpm:
            token = rpm.group(1).strip()
            interval = "1.80" if token.startswith("33") else "1.33" if token == "45" else "0.77"
            ref = f" A {token} RPM record makes one rotation about every {interval} seconds."
        return (detail or "Sharp clicks repeat at a record-like interval.") + ref + " Percussion can sometimes mimic repeated groove defects."
    if key == "Likely power system":
        return (detail or "Persistent narrowband power-frequency energy was measured.") + (
            " The analyzer checks 50/60 Hz and their harmonics (100, 120, 150, 180 Hz and higher) across repeated time windows."
            " Multiple steady lines support a mains-hum interpretation better than one isolated bass note."
            " Hum can enter during recording, copying or digitization, so this does not establish studio location.")
    if key == "Radio / TV signals":
        return (detail or "A narrow broadcast-frequency tone was measured.") + (
            " Nominal reference frequencies: 15,734.26 Hz for 525-line NTSC-type equipment,"
            " 15,625 Hz for 625-line PAL/SECAM-type equipment, and 19,000 Hz for an FM stereo pilot."
            " A persistent narrow peak supports interference somewhere in the recording chain, not necessarily at the original studio.")
    if key == "NDR-style 10 kHz dip":
        return (detail or "A narrow spectral notch was measured.") + (
            " This feature is a local reduction in energy near 10 kHz, seen as a dark band"
            " and a trough in the frequency profile. It resembles the NDR-related clue investigated"
            " during The Most Mysterious Song search but cannot identify NDR by itself.")
    if key == "Stereo format":
        return (detail or "Channel structure was measured.") + (
            " The decoded left and right signals are compared; near-identical channels can indicate dual mono."
            " This describes the file, not necessarily the original master.")
    if key == "Digital file history":
        return (detail or "Available encoder metadata was inspected.") + (
            " Encoder versions can establish an earliest plausible encoding year."
            " Tags may be edited or rewritten, and the recording itself may be decades older.")
    if key == "Playback speed":
        return (detail or "A pitch or timing reference was considered.") + (
            " Absolute speed cannot be established from musical pitch alone without a trusted reference."
            " Wow/flutter fluctuations are different from a constant playback-speed offset.")
    return detail or "The measured signal supports this interpretation."


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
    details_html = f'<p>{html.escape(description)}</p>'
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
            details_html = (f'<p>{html.escape(description)}</p>' +
                            '<ul>' + ''.join(f'<li>{html.escape(f)}</li>' for f in facts[:10]) + '</ul>')
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
    if evidence_plots:
        details_html += '<div class="ac-evidence-intro">Measured spectrogram · selected excerpt</div>'
        for entry in evidence_plots[:2]:
            img = entry.get('image_base64', '')
            if not isinstance(img, str) or not re.fullmatch(r'[A-Za-z0-9+/=]{100,400000}', img):
                continue
            caption = html.escape(str(entry.get('caption','')))
            details_html += ('<figure class="ac-evidence">'
                             '<img loading="lazy" alt="Actual audio frequency spectrogram" '
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
    return " ".join(statements)


def sorted_findings(rows):
    items = dict(rows or [])
    # Always show every check, even if absent from an older analyzer version.
    priority = list(LABELS)
    level = {"strong": 3, "good": 2, "maybe": 1, "none": 0}
    sorted_keys = sorted(priority, key=lambda k: (-level[badge_class(items.get(k, {}))], priority.index(k)))
    return [(key, items.get(key, {"certainty": "Unclear", "result": "Unclear"})) for key in sorted_keys]


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
        card(LABELS[key][0], item, key, evidence_plots=plots.get(key, []))
        for key, item in results) + '</div>', unsafe_allow_html=True)
    with st.expander("File details"):
        info = meta.get("file_history", {}).get("facts", {})
        bits = info.get("bitrate_kbps")
        rate_text = f" · {bits} kbps" if bits else ""
        st.caption(f'Codec: {meta.get("codec", "unknown")}{rate_text} · '
                   f'Sample rate: {meta.get("input_rate", "?")} Hz · '
                   f'Channels: {meta.get("channels", "?")}')
    st.markdown('<div class="ac-foot">Fun clues, not proof. Noise can come from a later recording or copy.</div>',
                unsafe_allow_html=True)
