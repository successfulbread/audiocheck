"""AudioCheck v0.8: dark-themed Streamlit audio provenance analysis."""
from __future__ import annotations

import html
from pathlib import Path
import tempfile

import streamlit as st

from analyzer import MAX_BYTES, analyze, analyze_path
from youtube_source import download_youtube_audio

st.set_page_config(page_title="AudioCheck | Audio Archaeology", page_icon=":material/album:",
                   layout="centered", initial_sidebar_state="collapsed")

st.markdown("""
<style>
:root {color-scheme: dark;}
.stApp{background:#0B1020;color:#F2F6FF;}
.block-container{max-width:980px;padding-top:1.2rem;padding-bottom:3rem;}
header[data-testid="stHeader"]{background:transparent;}
.ac-hero{background:radial-gradient(circle at 85% -15%,rgba(0,226,204,.27),transparent 55%),
 linear-gradient(115deg,#252059,#131b39 55%,#0d2136);border:1px solid #45418a;
 border-radius:24px;padding:29px 27px 25px;margin-bottom:20px;
 box-shadow:0 14px 44px #030618bb;position:relative;overflow:hidden;}
.ac-eyebrow{text-transform:uppercase;letter-spacing:.19em;color:#62ebdb;
 font-size:.73rem;font-weight:850;}
.ac-title{font-size:clamp(2.3rem,7vw,4.1rem);font-weight:900;color:#fff;
 line-height:1.02;letter-spacing:-.055em;margin:10px 0 10px;}
.ac-title b{color:#62f4d4;font-weight:900;}
.ac-sub{color:#b9c7dc;line-height:1.5;font-size:.95rem;max-width:630px;}
.ac-tags{display:flex;gap:8px;flex-wrap:wrap;margin-top:18px;}
.ac-tag{background:#ffffff12;border:1px solid #ffffff26;color:#d7e4ff;
 padding:6px 10px;border-radius:30px;font-size:.73rem;font-weight:700;}
.ac-heading{font-weight:850;font-size:1.3rem;color:#f7f8ff;
 letter-spacing:-.025em;margin:20px 0 8px;}
.ac-help{font-size:.88rem;color:#97a9c6;margin:0 0 13px;line-height:1.6;}
.ac-meta{background:#121b30;border:1px solid #2a3d59;color:#b9c9e5;
 border-radius:15px;padding:13px 17px;margin:15px 0 19px;font-size:.84rem;}
.ac-meta strong{color:#fff;display:block;font-size:.95rem;margin-bottom:3px;}
.ac-source{background:linear-gradient(120deg,#1b2843,#152c35 80%);
 border:1px solid #377d80;border-left:5px solid #4aebc9;
 border-radius:19px;padding:22px 23px 17px;margin:13px 0 16px;
 box-shadow:0 7px 24px #021a22a6;}
.ac-eyepill{font-size:.7rem;letter-spacing:.16em;font-weight:900;
 text-transform:uppercase;color:#7bfce3;margin-bottom:9px;}
.ac-source-title{color:#f6faff;font-weight:900;font-size:1.42rem;
 line-height:1.23;margin-bottom:9px;}
.ac-source-reason{font-size:.91rem;color:#c5e5e4;line-height:1.55;}
.ac-main-copy{background:#172139;border:1px solid #313c63;border-radius:18px;
 padding:17px 20px;margin:0 0 21px;color:#d7e2f3;}
.ac-main-copy h4{font-size:.93rem;color:#a5f0ff;margin:0 0 7px;}
.ac-main-copy p{font-size:.87rem;line-height:1.66;margin:0;}
.ac-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(245px,1fr));
 gap:13px;margin:13px 0 23px;}
.ac-card{background:#151d30;border:1px solid #303d58;border-radius:16px;
 padding:16px 16px 13px;box-shadow:0 5px 16px #050b1e88;}
.ac-card.good{border-top:4px solid #56e0ca;}
.ac-card.possible{border-top:4px solid #a993fa;}
.ac-card.weak{border-top:4px solid #f5bd64;}
.ac-label{font-size:.69rem;color:#98b1d0;font-weight:850;
 text-transform:uppercase;letter-spacing:.08em;margin-bottom:8px;}
.ac-result{font-size:1.1rem;line-height:1.3;color:#f8fbff;
 font-weight:850;margin-bottom:12px;}
.ac-badge{border-radius:99px;padding:4px 9px;display:inline-block;
 font-size:.7rem;font-weight:850;}
.ac-badge.good{background:#1b4c46;color:#a3ffe9;}
.ac-badge.possible{background:#3c2d63;color:#e5c6ff;}
.ac-badge.weak{background:#573e22;color:#ffdc9a;}
.ac-card details{border-top:1px solid #2c3a55;margin-top:12px;padding-top:10px;}
.ac-card summary{cursor:pointer;font-weight:750;color:#c1d2f3;font-size:.8rem;}
.ac-card details p{font-size:.79rem;line-height:1.55;color:#b2c2d9;margin:9px 0 0;}
.ac-secondary{background:#121827;border:1px solid #293147;border-radius:14px;
 color:#99a9c7;font-size:.81rem;padding:13px 16px;margin:15px 0 11px;}
.ac-foot{color:#8498b8;line-height:1.55;font-size:.78rem;margin:13px 0;}
@media(max-width:650px){.ac-hero{padding:22px 19px 21px;border-radius:17px}
 .ac-grid{grid-template-columns:1fr}.ac-source{padding:19px}.block-container{padding-top:.5rem}}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<section class="ac-hero">
  <div class="ac-eyebrow">Sound archaeology lab</div>
  <div class="ac-title">Audio<b>Check</b></div>
  <div class="ac-sub">Trace the clues hiding inside a recording: disc surface noise,
    vinyl rotation, electrical interference, broadcast signals and more.</div>
  <div class="ac-tags">
    <span class="ac-tag">Up to 5 minutes</span>
    <span class="ac-tag">Audio forensic clues</span>
    <span class="ac-tag">No account required</span>
  </div>
</section>
""", unsafe_allow_html=True)

if "report" not in st.session_state:
    st.session_state.report = None
if "report_error" not in st.session_state:
    st.session_state.report_error = None


def store_report(rows, meta, name, kind):
    st.session_state.report = {"rows": rows, "meta": meta, "name": name, "kind": kind}
    st.session_state.report_error = None


st.markdown('<div class="ac-heading">Analyze a recording</div>', unsafe_allow_html=True)
st.markdown('<div class="ac-help">Pick a song and press Analyze. You can use MP3, WAV, FLAC, OGG or M4A. Files are analyzed temporarily, without saving them to the repository.</div>', unsafe_allow_html=True)
upload_tab, youtube_tab = st.tabs(["Upload a song", "YouTube URL (beta)"])
with upload_tab:
    with st.form("upload_form", clear_on_submit=False, enter_to_submit=False):
        uploaded = st.file_uploader("Select your audio file", type=["mp3", "wav", "flac", "ogg", "m4a"],
                                    accept_multiple_files=False, max_upload_size=100)
        pressed = st.form_submit_button("Analyze recording", use_container_width=True, type="primary")
    if pressed:
        st.session_state.report = None
        if uploaded is None:
            st.session_state.report_error = ("Your browser has not sent a file. "
                                             "Please select the song again, then press Analyze.")
        elif uploaded.size > MAX_BYTES:
            st.session_state.report_error = "The file must be 100 MB or smaller."
        else:
            try:
                with st.spinner("Listening for disc, electrical and broadcast fingerprints..."):
                    name = Path(uploaded.name).name
                    rows, meta = analyze(uploaded.getvalue(), name)
                store_report(rows, meta, name, "Uploaded audio")
            except ValueError as ex:
                st.session_state.report_error = str(ex)
            except Exception:
                st.session_state.report_error = "Analysis failed; check Manage app > Logs for details."
with youtube_tab:
    st.caption("Public video, five minutes maximum. YouTube can block automated downloads from Streamlit Cloud.")
    with st.form("youtube_form", clear_on_submit=False, enter_to_submit=False):
        link = st.text_input("Paste a YouTube video link", placeholder="https://www.youtube.com/watch?v=...")
        permitted = st.checkbox("I am authorized to download and analyze this video's audio.")
        pressed_yt = st.form_submit_button("Analyze YouTube audio", use_container_width=True, type="primary")
    if pressed_yt:
        st.session_state.report = None
        if not link.strip():
            st.session_state.report_error = "Enter a YouTube video link."
        elif not permitted:
            st.session_state.report_error = "Please confirm that downloading this audio is permitted."
        else:
            try:
                with st.spinner("Requesting the audio stream from YouTube..."):
                    with tempfile.TemporaryDirectory(prefix="audiocheck_yt_") as directory:
                        path, title = download_youtube_audio(link, Path(directory))
                        rows, meta = analyze_path(path, title)
                store_report(rows, meta, title, "YouTube audio")
            except ValueError as ex:
                st.session_state.report_error = str(ex)
            except Exception:
                st.session_state.report_error = ("The YouTube service could not return a usable audio file. "
                                                 "Try uploading a copy you may lawfully use.")

if st.session_state.report_error:
    st.error(st.session_state.report_error)


def meaningful(label, item):
    status = item["certainty"]
    result = str(item["result"]).lower()
    if status not in {"Strong", "High", "Possible", "Tentative"}:
        return False
    if "candidates" in result or "unclear" in result or "none detected" in result:
        return False
    return True


def badge_class(item):
    return {"Strong": "good", "High": "good", "Possible": "possible",
            "Tentative": "weak"}.get(item["certainty"], "weak")


def render_card(label, item):
    cls = badge_class(item)
    return (f'<section class="ac-card {cls}">'
            f'<div class="ac-label">{html.escape(str(label))}</div>'
            f'<div class="ac-result">{html.escape(str(item["result"]))}</div>'
            f'<span class="ac-badge {cls}">{html.escape(str(item["certainty"]))}</span>'
            f'<details><summary>Why this finding?</summary>'
            f'<p>{html.escape(str(item["detail"]))}</p></details></section>')


def plain_english(rows):
    found = dict(rows)
    messages = []
    source = found.get("Likely audio source", {})
    label = source.get("result", "")
    if "Disc" in label:
        messages.append("The sound carries artifacts consistent with a physical record being played. "
                        "Irregular pops and granular noise can be preserved even when that record was later copied to tape or digitized.")
    elif "FM" in label:
        messages.append("A radio-associated signal suggests the audio may have passed through an FM broadcast chain.")
    elif "Tape" in label:
        messages.append("Several abrupt level losses could be compatible with magnetic tape, "
                        "although digital faults can cause similar interruptions.")
    else:
        messages.append("This excerpt does not contain enough distinctive artifacts to identify the source confidently.")
    rotation = found.get("Vinyl rotation", {})
    if meaningful("Vinyl rotation", rotation):
        messages.append("Some clicks repeat at a rate matching "
                        + str(rotation.get("result")) + ", giving a possible disc speed.")
    electrical = found.get("Likely power system", {})
    if meaningful("Likely power system", electrical):
        if "50 Hz" in electrical["result"]:
            messages.append("A 50 Hz-related hum pattern is present, commonly associated with European and other 50 Hz electrical systems. "
                            "The interference could have entered during a later transfer.")
        elif "60 Hz" in electrical["result"]:
            messages.append("A 60 Hz-related hum pattern is present, consistent with North American and other 60 Hz electrical systems. "
                            "It does not establish the studio's location.")
    broadcast = found.get("Radio / TV signals", {})
    if meaningful("Radio / TV signals", broadcast):
        messages.append("A narrow tone consistent with " + broadcast["result"]
                        + " appears in the recording. It could have entered at a later copying stage.")
    return " ".join(messages)


report = st.session_state.report
if report:
    rows = report["rows"]
    meta = report["meta"]
    diag = meta["diagnostics"]
    found = dict(rows)
    st.markdown('<div class="ac-heading">Your audio fingerprint</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="ac-meta"><strong>' + html.escape(str(report["name"])) + '</strong>'
        + html.escape(str(report["kind"])) + f' &middot; {meta["duration"]:.0f}s long'
        + f' &middot; {meta["analyzed_seconds"]:.0f}s examined in '
        + f'{diag["sampled_sections"]} sections</div>', unsafe_allow_html=True,
    )
    source = found.get("Likely audio source")
    if source and meaningful("Likely audio source", source):
        st.markdown(
            '<section class="ac-source"><div class="ac-eyepill">Most likely source</div>'
            + '<div class="ac-source-title">' + html.escape(source["result"]) + '</div>'
            + '<div class="ac-source-reason">' + html.escape(source["detail"]) + '</div></section>',
            unsafe_allow_html=True,
        )
    st.markdown('<section class="ac-main-copy"><h4>What the evidence suggests</h4><p>'
                + html.escape(plain_english(rows)) + '</p></section>', unsafe_allow_html=True)

    # Prioritize meaningful provenance tests. Don't lead with stereo or bandwidth,
    # which are easy to measure but do not establish country/medium.
    preferred = ["Disc surface noise", "Vinyl rotation", "Likely power system",
                 "Radio / TV signals", "Possible tape dropouts"]
    show = [(label, found[label]) for label in preferred if label in found
            and meaningful(label, found[label])]
    if show:
        st.markdown('<div class="ac-heading">Signals we found</div>', unsafe_allow_html=True)
        st.markdown('<div class="ac-grid">' + ''.join(render_card(*item) for item in show)
                    + '</div>', unsafe_allow_html=True)

    tech = [(label, found[label]) for label in ("Stereo format", "Audio bandwidth")
            if label in found and meaningful(label, found[label])]
    if tech:
        st.markdown('<div class="ac-heading">Audio profile</div>', unsafe_allow_html=True)
        st.markdown('<div class="ac-grid">' + ''.join(render_card(*item) for item in tech)
                    + '</div>', unsafe_allow_html=True)

    # Everything uncertain, absent, or overlapping is still accessible, but not
    # given the same visual emphasis as genuine measured findings.
    deferred = [(label, item) for label, item in rows
                if label not in {"Likely audio source", "Recording-medium clues"}
                and label not in {r[0] for r in show+tech}]
    if deferred:
        with st.expander(f"Other checks: {len(deferred)} inconclusive or negative findings"):
            for label, item in deferred:
                st.markdown(f"**{label}:** {item['result']}")
                st.caption(item["detail"])
    with st.expander("Technical measurements (beta)"):
        st.write(f"File codec: {meta['codec']}")
        st.write(f"Input sample rate: {meta['input_rate']:,} Hz")
        st.write(f"Channels: {meta['channels']}")
        st.write(f"Near-full-scale samples: {diag['near_full_scale_percent']}%")
        st.write(f"Possible interruptions: {diag['possible_interruptions']}")
        if diag["pilot_frequency_scatter_hz"] is not None:
            st.write(f"FM pilot frequency scatter: {diag['pilot_frequency_scatter_hz']} Hz")
    st.markdown('<div class="ac-foot">These are evidence-based suggestions, not verified '
                'probabilities. A disc transferred to tape or radio may retain clues from '
                'multiple stages. This tool cannot identify the song itself.</div>',
                unsafe_allow_html=True)
else:
    st.markdown('<div class="ac-foot">Results prioritize signals we can measure. '
                'Missing or uncertain signatures are summarized separately. '
                'Audio uploads are processed temporarily; YouTube availability depends on '
                'provider access and authorization.</div>', unsafe_allow_html=True)
