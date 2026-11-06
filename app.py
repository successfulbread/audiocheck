"""AudioCheck v1.3 - folded frequency clues and improved file-age dating."""
from __future__ import annotations

import html
from pathlib import Path
import re
import tempfile

import streamlit as st

from analyzer import MAX_BYTES, analyze, analyze_path
from youtube_source import download_youtube_audio
from archive_source import fetch_archive_audio

st.set_page_config(page_title="AudioCheck | Find the clues", page_icon=":material/graphic_eq:", layout="centered", initial_sidebar_state="collapsed")

st.markdown("""
<style>
html,body,.stApp { font-family:Inter,system-ui,-apple-system,"Segoe UI",sans-serif; }
.stApp { background:#F7FAFF; color:#17314E; }
.block-container { max-width:980px; padding-top:1.1rem; padding-bottom:3rem; }
header[data-testid="stHeader"] {background:transparent;}
.ac-hero {background:linear-gradient(115deg,#DBF8ED 0%,#E8F1FF 54%,#FFF0DB 100%);
  border:1px solid #D8E7F0;border-radius:23px;padding:22px 26px;margin:0 0 18px;}
.ac-brand {font-size:clamp(2.3rem,6vw,3.3rem);line-height:1.08;letter-spacing:-.055em;font-weight:900;
  color:#16385C;margin:0 0 5px;}
.ac-brand span {color:#087E9E;}
.ac-intro {font-size:.94rem;color:#355573;margin:0;}
.ac-heading {font-size:1.3rem;font-weight:850;color:#173657;margin:16px 0 10px;}
.ac-meta {font-size:.78rem;color:#647991;margin:-3px 0 15px;overflow-wrap:anywhere;}
.ac-grid {display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px;margin-bottom:17px;}
.ac-card {border:1px solid;border-radius:19px;padding:16px 17px 13px;min-width:0;
  box-shadow:0 4px 13px #244C6810;}
.ac-card.strong {background:linear-gradient(135deg,#DCFBEA,#F3FFF6);border-color:#7CD8A9;}
.ac-card.good {background:linear-gradient(135deg,#DDEEFF,#F1FAFF);border-color:#96C8F5;}
.ac-card.maybe {background:linear-gradient(135deg,#FFF0D4,#FFF9EF);border-color:#F6C581;}
.ac-card.none {background:#F1F3F6;border-color:#DDE1E7;box-shadow:none;color:#788594;}
.ac-top {display:flex;align-items:center;gap:7px;margin-bottom:11px;}
.ac-icon {font-size:1.14rem;line-height:1.2;flex:none;}
.ac-label {font-size:.76rem;font-weight:800;color:#435B73;flex:1;}
.ac-card.none .ac-label{color:#7A8793;}
.ac-pill {border-radius:999px;font-size:.66rem;font-weight:800;padding:4px 8px;white-space:nowrap;}
.ac-card.strong .ac-pill{background:#B7F0CF;color:#08683C;}
.ac-card.good .ac-pill{background:#BADFFF;color:#164F94;}
.ac-card.maybe .ac-pill{background:#FFE0A8;color:#81500A;}
.ac-card.none .ac-pill{background:#E2E5EB;color:#697481;}
.ac-sub{font-size:.78rem;font-weight:650;color:#4B647F;margin-top:7px;}
.ac-result{font-size:1.15rem;line-height:1.3;font-weight:850;color:#17385A;overflow-wrap:anywhere;min-height:1.45em;}
.ac-card.none .ac-result{font-size:1rem;color:#697785;}
.ac-card.none .ac-sub{color:#788592;}
.ac-card details{border-top:1px solid #AFC9D533;margin-top:12px;padding-top:8px;}
.ac-card summary{font-size:.78rem;font-weight:800;color:#246193;cursor:pointer;}
.ac-card.none summary{color:#6D7C8B;}
.ac-card details p{font-size:.82rem;line-height:1.47;color:#435A71;margin:8px 0 2px;}
.ac-card details ul{margin:9px 0 0;padding-left:19px;}
.ac-card details li{font-size:.82rem;line-height:1.43;color:#435A71;margin:5px 0;}
.ac-card.none details p{color:#6D7B88;}
.ac-foot{font-size:.76rem;color:#6A7D91;margin-top:13px;}
@media(max-width:675px){.ac-grid{grid-template-columns:1fr;gap:10px;}
  .ac-hero{padding:20px 18px}.block-container{padding-top:.55rem;}
  .ac-card{padding:14px 15px 12px;}.ac-top{margin-bottom:8px;}}
</style>
""", unsafe_allow_html=True)

st.markdown('''<div class="ac-hero"><div class="ac-brand">Audio<span>Check</span></div>
<p class="ac-intro">Upload a song to check its likely source, record speed, broadcast signals and digital file age.</p></div>''', unsafe_allow_html=True)

if "report" not in st.session_state:
    st.session_state.report = None
if "report_error" not in st.session_state:
    st.session_state.report_error = None
if "upload_nonce" not in st.session_state:
    st.session_state.upload_nonce = 0


def store_report(rows, meta, name, kind):
    # A YouTube re-encode is not evidence of the uploader's ORIGINAL file date.
    if kind == "YouTube":
        rows = [(key, {"result": "YouTube stream only", "certainty": "Tentative",
                       "detail": "YouTube may re-encode audio. This stream cannot date the original uploaded file."}
                 if key == "Digital file history" else value) for key, value in rows]
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
            return "No power clue"
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
    if not meaningful(item):
        return {
            "Likely audio source": "No distinctive record, tape or FM signal stood out. Clean recordings can sound alike.",
            "Vinyl rotation": "No repeating pops reliably matched 33 1/3, 45 or 78 RPM.",
            "Likely power system": "No steady 50 or 60 Hz electrical hum stood out.",
            "Radio / TV signals": "No convincing old TV scan tone or FM pilot tone was found.",
            "NDR-style 10 kHz dip": "No lasting narrow dip near 10 kHz was found.",
            "Disc surface noise": "No distinctive pops or crackle stood out in the sections checked.",
            "Possible tape dropouts": "No short, sudden losses of sound were found.",
            "Stereo format": "The channels were too faint or inconsistent to compare.",
            "Audio bandwidth": "The spectrum was too faint to measure.",
            "Digital file history": "No useful encoding date or encoder version is in the file.",
            "Playback speed": "Without a reference pitch or timing signal, overall speed can't be checked.",
        }.get(key, "Not enough evidence to make a useful guess.")
    detail = str(item.get("detail", ""))
    raw = str(item.get("result", ""))
    if key == "Likely audio source":
        return detail[:350] if detail else "Best guess from pops, tape clues, broadcast tones and frequency range."
    if key == "Vinyl rotation":
        match = re.search(r"(\d+) (?:short|quick) click", detail)
        count = f"{match.group(1)} sharp pops" if match else "Sharp pops"
        rpm = re.search(r"(33[\u2153]|33[ ]?1/3|45|78) RPM", raw)
        value = rpm.group(1) if rpm else "record"
        gap = {"45": "1.33", "78": "0.77", "33\u2153": "1.80", "33 1/3": "1.80"}.get(value)
        return f"{count} line up about every {gap} seconds, matching {value} RPM. Drums can sometimes imitate pops." if gap else "Several sharp pops repeat at record-like intervals."
    if key == "Likely power system":
        freq = "50" if "50 Hz" in raw else "60" if "60 Hz" in raw else None
        if freq:
            return f"A steady line near {freq} Hz may be electrical hum from recording or copying equipment."
        return "Weak peaks suggest possible electrical noise, but the region is uncertain."
    if key == "Radio / TV signals":
        if "NTSC" in raw:
            return "A narrow tone near 15,734 Hz matches older NTSC TV equipment."
        if "PAL" in raw or "SECAM" in raw:
            return "A narrow tone near 15,625 Hz matches older PAL/SECAM TV equipment."
        if "FM" in raw:
            return "A steady 19,000 Hz tone matches the FM stereo pilot signal."
        return "A narrow broadcast-related tone appears in the audio."
    if key == "NDR-style 10 kHz dip":
        return "A narrow dip around 10 kHz resembles one found on some NDR radio recordings. It isn't unique to NDR."
    if key == "Disc surface noise":
        clicks = re.search(r"\((\d+) in qualifying sections\)", detail)
        return ((clicks.group(1) + " short pops and gritty crackle were found, including quiet passages.")
                if clicks else "Irregular pops and gritty noise persist between musical sounds.")
    if key == "Possible tape dropouts":
        return "Brief reductions in sound were measured. Tape damage is one possibility."
    if key == "Stereo format":
        if raw == "Mono":
            return "The file contains one audio channel."
        return "The left and right channels differ." if "Stereo" in raw else "Two channels carry almost identical sound."
    if key in ("Audio bandwidth", "Digital file history"):
        # Show measured facts and meaningful alternate explanations, not a generic disclaimer.
        return detail[:275] if detail else "No date or frequency clue found."
    return detail[:160] if detail else "Some evidence supports this guess."


def card(label, item, key=None):
    key = key or label
    item = item if isinstance(item, dict) else {}
    cls = badge_class(item)
    pill = {"strong": "Clear clue", "good": "Good clue", "maybe": "Best guess", "none": "No clue"}[cls]
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
            details_html = '<ul>' + ''.join(f'<li>{html.escape(f)}</li>' for f in facts[:7]) + '</ul>'
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
        statements.append("An FM pilot suggests a radio recording.")
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
file_tab, archive_tab, youtube_tab = st.tabs(["Upload audio", "Archive.org link", "YouTube (beta)"])
with file_tab:
    with st.form("upload_form", enter_to_submit=False, clear_on_submit=False):
        uploaded = st.file_uploader("Choose a file (up to 5 minutes)",
                                    type=["mp3", "mpeg", "mpga", "wav", "flac", "ogg", "m4a"],
                                    accept_multiple_files=False, max_upload_size=100,
                                    key=f"audio_file_{st.session_state.upload_nonce}")
        pressed = st.form_submit_button("Analyze recording", type="primary", use_container_width=True)
    if pressed:
        st.session_state.report_error = None
        if uploaded is None:
            st.session_state.report_error = "Choose a file first."
        elif uploaded.size > MAX_BYTES:
            st.session_state.report_error = "File too large (100 MB max)."
        else:
            try:
                with st.spinner("Listening for clues..."):
                    name = Path(uploaded.name).name
                    rows, meta = analyze(uploaded.getvalue(), name)
                store_report(rows, meta, name, "Upload")
                # A new widget key removes the finished file from the upload bar.
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
                        rows, meta = analyze_path(path, title)
                store_report(rows, meta, title, "Archive")
            except ValueError as exc:
                st.session_state.report_error = str(exc)
            except Exception:
                st.session_state.report_error = "This archive link could not be analyzed. Try uploading the MP3."

with youtube_tab:
    st.caption("YouTube can block cloud servers (403). Archive.org direct audio links or file uploads are more reliable.")
    with st.form("youtube_form", enter_to_submit=False):
        link = st.text_input("Video address", placeholder="https://www.youtube.com/watch?v=...")
        allowed = st.checkbox("I have permission to retrieve and analyze this audio")
        pressed_yt = st.form_submit_button("Analyze YouTube audio", use_container_width=True)
    if pressed_yt:
        st.session_state.report_error = None
        if not link.strip():
            st.session_state.report_error = "Paste a YouTube link first."
        elif not allowed:
            st.session_state.report_error = "Confirm that audio retrieval is permitted."
        else:
            try:
                with st.spinner("Fetching audio..."):
                    with tempfile.TemporaryDirectory(prefix="audiocheck_yt_") as td:
                        path, title = download_youtube_audio(link, Path(td))
                        rows, meta = analyze_path(path, title)
                store_report(rows, meta, title, "YouTube")
            except ValueError as exc:
                st.session_state.report_error = str(exc)
            except Exception:
                st.session_state.report_error = "YouTube refused this request. Try uploading an audio file."

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
    st.markdown('<div class="ac-grid">' + "".join(
        card(LABELS[key][0], item, key) for key, item in results) + '</div>', unsafe_allow_html=True)
    with st.expander("File details"):
        info = meta.get("file_history", {}).get("facts", {})
        bits = info.get("bitrate_kbps")
        rate_text = f" · {bits} kbps" if bits else ""
        st.caption(f'Codec: {meta.get("codec", "unknown")}{rate_text} · '
                   f'Sample rate: {meta.get("input_rate", "?")} Hz · '
                   f'Channels: {meta.get("channels", "?")}')
        if report.get("kind") == "YouTube":
            st.caption("YouTube gives us a downloaded stream, not the original uploader's file or original metadata.")
    st.markdown('<div class="ac-foot">Fun clues, not proof. Noise can come from a later recording or copy.</div>',
                unsafe_allow_html=True)
