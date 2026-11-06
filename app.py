"""AudioCheck v0.7 - Streamlit upload form + optional YouTube link."""
from __future__ import annotations

import html
from pathlib import Path
import tempfile

import streamlit as st

from analyzer import MAX_BYTES, analyze, analyze_path
from youtube_source import download_youtube_audio

st.set_page_config(
    page_title="AudioCheck | Sonic Archaeology",
    page_icon="🎛️",
    layout="centered",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
  :root { --ink: #172044; --lavender: #ece8ff; --mint: #b1f3de; }
  .block-container { max-width: 940px; padding-top: 1.5rem; padding-bottom: 4rem; }
  .ac-hero { border-radius: 22px; padding: 26px 27px 21px;
    background: linear-gradient(120deg,#361a70 0%,#6236aa 42%,#087d98 100%);
    box-shadow: 0 12px 30px rgba(50,34,117,.20); color: white; margin-bottom: 15px; }
  .ac-eyebrow {font-size: .78rem; font-weight: 800; text-transform: uppercase;
    color:#bff6ed; letter-spacing:.17em;}
  .ac-title {font-weight: 850; letter-spacing: -.045em; font-size:clamp(2.2rem,6vw,3.5rem);
    line-height:1.08; color:#fff; margin: 8px 0 7px;}
  .ac-subtitle { font-size:1rem; color:#eff7ff; line-height:1.5; margin-bottom: 7px; }
  .ac-pill {display:inline-block; border:1px solid #ffffff88; border-radius:40px;
    padding:5px 10px; font-size: .73rem; font-weight:700; margin:6px 6px 0 0; color:white;}
  .ac-section {margin:25px 0 10px; font-size:1.38rem; font-weight:800;}
  .ac-help {font-size:.89rem;color:#64718c;margin-bottom: 14px;}
  .ac-grid {display:grid; grid-template-columns:repeat(auto-fit,minmax(245px,1fr)); gap:13px;
    margin-top:14px;margin-bottom:20px;}
  .ac-card {background:#fff; border:1px solid #dce0f4; border-radius:18px;
    box-shadow:0 5px 18px rgba(35,37,90,.06);padding:17px 17px 14px; color:var(--ink);}
  .ac-card.ac-strong {border-top:5px solid #02ad90;}
  .ac-card.ac-maybe {border-top:5px solid #a264df;}
  .ac-card.ac-muted {border-top:5px solid #c5cad8;}
  .ac-label {font-size:.77rem;letter-spacing:.045em;text-transform:uppercase;
    font-weight:800;color:#64718d;margin-bottom:8px;}
  .ac-value {font-size:1.15rem; font-weight:820;line-height:1.3;min-height:1.5rem; margin-bottom:9px;}
  .ac-badge {display:inline-block;padding:4px 9px;border-radius:99px;font-size:.73rem;font-weight:800;}
  .ac-badge.ac-strong {background:#d7f8e9;color:#08795f;}
  .ac-badge.ac-maybe {background:#eee1ff;color:#7638aa;}
  .ac-badge.ac-muted {background:#eef0f4;color:#596578;}
  .ac-card details {margin-top:12px; border-top:1px solid #e8e9f5;padding-top:9px;}
  .ac-card summary {font-size:.78rem; color:#56658a;cursor:pointer; font-weight:700;}
  .ac-card details p {color:#39425d; font-size:.81rem; line-height:1.55; margin:8px 0 0;}
  .ac-summary {border-radius:15px;background:linear-gradient(125deg,#e5fff6,#eae8ff);
    border:1px solid #d3ddf1; padding:14px 17px; color:#253758; margin:8px 0 13px;}
  .ac-note {font-size:.83rem;color:#617084;line-height:1.48;margin:5px 0 14px;}
  @media(max-width: 650px){.ac-hero{padding:22px 20px 18px}.ac-grid{grid-template-columns:1fr}}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="ac-hero">
  <div class="ac-eyebrow">Forensic sound explorer</div>
  <div class="ac-title">AudioCheck</div>
  <div class="ac-subtitle">Where did this recording come from? Examine vinyl, tape,
  radio, electrical hum and more with simple evidence-based clues.</div>
  <span class="ac-pill">Up to 5 minutes</span>
  <span class="ac-pill">MP3 / WAV / FLAC / M4A</span>
  <span class="ac-pill">Experimental science</span>
</div>
""", unsafe_allow_html=True)

st.markdown('<div class="ac-section">Choose your audio</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="ac-help">Select a file and press the separate analyze button, '
    'or try a YouTube video link.</div>', unsafe_allow_html=True
)

if "report" not in st.session_state:
    st.session_state.report = None
if "report_error" not in st.session_state:
    st.session_state.report_error = None


def store_report(rows, meta, source_name, source_kind):
    st.session_state.report = {
        "rows": rows,
        "meta": meta,
        "name": source_name,
        "kind": source_kind,
    }
    st.session_state.report_error = None


upload_tab, youtube_tab = st.tabs(["Upload an audio file", "YouTube link (beta)"])

with upload_tab:
    st.caption("Choose your recording first. Analysis starts only when you press the button.")
    with st.form("audio_upload_submit", clear_on_submit=False, enter_to_submit=False):
        uploaded = st.file_uploader(
            "Choose MP3, WAV, FLAC, OGG or M4A",
            type=["mp3", "wav", "flac", "ogg", "m4a"],
            accept_multiple_files=False,
            max_upload_size=100,
        )
        submitted_upload = st.form_submit_button(
            "Analyze recording", type="primary", use_container_width=True
        )
    if submitted_upload:
        st.session_state.report = None
        st.session_state.report_error = None
        if uploaded is None:
            st.session_state.report_error = (
                "No audio file reached AudioCheck. Please select the file again, "
                "then press Analyze recording."
            )
        elif uploaded.size > MAX_BYTES:
            st.session_state.report_error = "The maximum upload size is 100 MB."
        else:
            try:
                with st.spinner("Examining the recording's audio fingerprints..."):
                    safe_name = Path(uploaded.name).name
                    rows, meta = analyze(uploaded.getvalue(), safe_name)
                store_report(rows, meta, safe_name, "Uploaded file")
            except ValueError as exc:
                st.session_state.report_error = str(exc)
            except Exception:
                st.session_state.report_error = "Analysis failed. See the Streamlit Cloud logs for details."

with youtube_tab:
    st.caption(
        "For a public video up to 5 minutes long. YouTube can block automatic "
        "audio retrieval from cloud servers; direct uploads are more reliable."
    )
    with st.form("youtube_submit", clear_on_submit=False, enter_to_submit=False):
        yt_url = st.text_input(
            "YouTube video URL", placeholder="https://www.youtube.com/watch?v=..."
        )
        permitted = st.checkbox(
            "I have permission to download and analyze this video's audio."
        )
        submitted_youtube = st.form_submit_button(
            "Analyze YouTube audio", type="primary", use_container_width=True
        )
    if submitted_youtube:
        st.session_state.report = None
        st.session_state.report_error = None
        if not yt_url.strip():
            st.session_state.report_error = "Paste a YouTube video link first."
        elif not permitted:
            st.session_state.report_error = (
                "Confirm that you are authorized to download and analyze this audio."
            )
        else:
            try:
                with st.spinner("Retrieving the permitted audio and checking its fingerprints..."):
                    with tempfile.TemporaryDirectory(prefix="audiocheck_youtube_") as folder:
                        path, title = download_youtube_audio(yt_url, Path(folder))
                        rows, meta = analyze_path(path, path.name)
                store_report(rows, meta, title, "YouTube audio")
            except ValueError as exc:
                st.session_state.report_error = str(exc)
            except Exception:
                st.session_state.report_error = (
                    "YouTube audio couldn't be analyzed. "
                    "This may be a Streamlit Cloud or YouTube restriction; try uploading a file."
                )

if st.session_state.report_error:
    st.error(st.session_state.report_error)

report = st.session_state.report
if report:
    rows = report["rows"]
    meta = report["meta"]
    diag = meta["diagnostics"]
    name = html.escape(str(report["name"]))
    kind = html.escape(str(report["kind"]))
    st.markdown('<div class="ac-section">Your audio fingerprint</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="ac-summary"><b>' + name + '</b><br>'
        + kind + ' &nbsp; &middot; &nbsp; '
        + f'{meta["duration"]:.1f}s long &nbsp; &middot; &nbsp; '
        + f'{meta["analyzed_seconds"]:.1f}s examined in '
        + f'{diag["sampled_sections"]} sections</div>', unsafe_allow_html=True
    )
    cards = []
    for label, item in rows:
        status = str(item["certainty"])
        color = (
            "ac-strong" if status == "High"
            else "ac-maybe" if status in {"Possible", "Tentative"}
            else "ac-muted"
        )
        title = html.escape(str(label))
        value = html.escape(str(item["result"]))
        detail = html.escape(str(item["detail"]))
        cards.append(
            f'<article class="ac-card {color}">'
            f'<div class="ac-label">{title}</div>'
            f'<div class="ac-value">{value}</div>'
            f'<span class="ac-badge {color}">{html.escape(status)}</span>'
            f'<details><summary>Why this result?</summary><p>{detail}</p></details>'
            f'</article>'
        )
    st.markdown('<div class="ac-grid">' + ''.join(cards) + '</div>', unsafe_allow_html=True)
    with st.expander("More technical details (beta)"):
        st.write(f"Codec: {meta['codec']}")
        st.write(f"Input sample rate: {meta['input_rate']:,} Hz")
        st.write(f"Audio channels: {meta['channels']}")
        st.write(f"Near-full-scale samples: {diag['near_full_scale_percent']}%")
        st.write(f"Possible brief interruptions: {diag['possible_interruptions']}")
        st.write(f"Upper spectral energy: {diag['spectral_upper_energy_khz']} kHz")
        if diag["pilot_frequency_scatter_hz"] is not None:
            st.write(f"19 kHz pilot variation: {diag['pilot_frequency_scatter_hz']} Hz")
    st.markdown(
        '<div class="ac-note"><b>Interpreting the findings:</b> Strong signals are not '
        'proof of an original recording location. Noise or hum can come from copying '
        'and digitization. "None detected" means the specific signal was not found '
        'in the examined sections, not that the medium was definitely absent.</div>',
        unsafe_allow_html=True,
    )
else:
    st.markdown(
        '<div class="ac-note">AudioCheck does not identify song titles or artists. '
        'Audio is processed temporarily; do not submit sensitive or unreleased recordings '
        'without accepting the hosting provider\'s privacy terms. YouTube downloads '
        'must be authorized under applicable platform terms and rights.</div>',
        unsafe_allow_html=True,
    )
