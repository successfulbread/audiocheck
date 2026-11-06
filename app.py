"""AudioCheck: independent browser upload fallback and source evidence indicators."""
from __future__ import annotations

import hashlib
import html

import streamlit as st

from alt_uploader import decode_component_file, render_alternative
from analyzer import MAX_BYTES, analyze

st.set_page_config(page_title="AudioCheck - Audio Origin Analyzer", page_icon="🎵", layout="centered")
st.title("AudioCheck")
st.subheader("Audio Origin Analyzer")
st.write("Upload up to five minutes of audio to check for vinyl, electrical and broadcast fingerprints.")
st.caption("Experimental: signals can originate during copying or digitization, not necessarily in the original studio.")

for key, initial in {
    "upload_nonce": 0,
    "saved_audio": None,
    "saved_upload_id": None,
    "last_analysis": None,
}.items():
    if key not in st.session_state:
        st.session_state[key] = initial


def clear_selection():
    st.session_state.upload_nonce += 1
    st.session_state.saved_audio = None
    st.session_state.saved_upload_id = None
    st.session_state.last_analysis = None


st.radio(
    "Choose upload method",
    ["Alternate phone-friendly upload", "Standard upload (larger files)"],
    key="upload_method",
    on_change=clear_selection,
)
with st.container(border=True):
    if st.session_state.upload_method == "Alternate phone-friendly upload":
        st.caption("Uses a different browser upload mechanism. Recommended for MP3 files up to 25 MB.")
        try:
            selection = render_alternative(key=f"alt_{st.session_state.upload_nonce}")
            value = getattr(selection, "file", None)
            if value and value.get("upload_id") != st.session_state.saved_upload_id:
                name, data, upload_id = decode_component_file(value)
                st.session_state.saved_audio = (name, data)
                st.session_state.saved_upload_id = upload_id
                st.session_state.last_analysis = None
        except ValueError as exc:
            st.error(str(exc))
        except Exception as exc:
            st.error("The alternative upload component failed to load. Switch to Standard upload.")
            st.caption(f"Technical detail: {type(exc).__name__}")
    else:
        st.caption("Original Streamlit uploader. Supports files up to 100 MB.")
        uploaded = st.file_uploader(
            "Choose an audio file",
            type=["mp3", "wav", "flac", "ogg", "m4a"],
            max_upload_size=100,
            key=f"standard_upload_{st.session_state.upload_nonce}",
        )
        if uploaded is not None:
            new_id = hashlib.sha256(uploaded.getvalue()).hexdigest()[:20]
            if new_id != st.session_state.saved_upload_id:
                st.session_state.saved_audio = (uploaded.name, uploaded.getvalue())
                st.session_state.saved_upload_id = new_id
                st.session_state.last_analysis = None

    file_info = st.session_state.saved_audio
    if file_info is None:
        st.info("No file received yet. Choose a file above. A green confirmation appears when it reaches AudioCheck.")
    else:
        name, data = file_info
        if len(data) > MAX_BYTES:
            st.error("This audio file exceeds 100 MB.")
        else:
            st.success(f"File received: {name} ({len(data) / (1024 * 1024):.1f} MB)")
            if st.button("Analyze recording", type="primary", use_container_width=True):
                with st.spinner("Analyzing selected sections of the recording..."):
                    try:
                        rows, meta = analyze(data, name)
                    except ValueError as exc:
                        st.error(str(exc))
                    except Exception:
                        st.error("Analysis failed. Check the app logs for details.")
                    else:
                        st.session_state.last_analysis = (st.session_state.saved_upload_id, rows, meta)
    st.button("Clear selection / choose another file", on_click=clear_selection, use_container_width=True)

report = st.session_state.last_analysis
if report is not None and report[0] == st.session_state.saved_upload_id:
    _, rows, meta = report
    st.success(
        f"Recording: {meta['duration']:.1f}s. Analyzed {meta['analyzed_seconds']:.1f}s "
        f"across {meta['diagnostics']['sampled_sections']} section(s)."
    )
    st.markdown("### Results")
    shades = {
        "High": "#167247", "Possible": "#a56613", "Not detected": "#667085",
        "Not measurable": "#667085", "Unclear": "#667085",
    }
    for label, item in rows:
        left, center, right = st.columns([2.3, 2.2, 1.25], vertical_alignment="center")
        left.markdown(f"**{html.escape(label)}**")
        center.write(item["result"])
        color = shades.get(item["certainty"], shades["Unclear"])
        right.markdown(
            f'<span style="display:inline-block;background:{color};color:white;padding:4px 8px;'
            f'border-radius:14px;font-size:11px;">{html.escape(item["certainty"])}</span>',
            unsafe_allow_html=True,
        )
        with st.expander(f"Why: {label}"):
            st.caption(item["detail"])
    with st.expander("Beta diagnostics"):
        diag = meta["diagnostics"]
        st.write(f"Codec: {meta['codec']}")
        st.write(f"Input sampling rate: {meta['input_rate']:,} Hz")
        st.write(f"Channels: {meta['channels']}")
        st.write(f"Near-full-scale samples: {diag['near_full_scale_percent']}%")
        st.write(f"Possible brief interruptions: {diag['possible_interruptions']}")
        if diag["pilot_frequency_scatter_hz"] is not None:
            st.write(f"19 kHz pilot frequency variation: {diag['pilot_frequency_scatter_hz']} Hz")
    st.info(
        "'None detected' means no qualifying signature was found in the analyzed portions, "
        "NOT that the source was definitively absent. 'Not measurable' is reserved for "
        "questions that cannot be answered from this audio alone."
    )

st.divider()
st.caption("Uploads are handled temporarily for processing. Avoid sensitive or unreleased material unless you accept the hosting provider's privacy terms.")
