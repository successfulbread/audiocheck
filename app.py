"""AudioCheck Streamlit interface, with simple upload confirmation and retry."""
import html
import streamlit as st
from analyzer import MAX_BYTES, MAX_SECONDS, analyze

st.set_page_config(page_title="AudioCheck - Audio Origin Analyzer", page_icon="🎵", layout="centered")
st.title("AudioCheck")
st.subheader("Audio Origin Analyzer")
st.write("Upload a recording to look for evidence of vinyl, electrical hum, and broadcast signals.")
st.caption("Experimental analysis only. A signal may come from a later copy or transfer, not the original studio.")

if "upload_nonce" not in st.session_state:
    st.session_state.upload_nonce = 0


def new_selection():
    st.session_state.pop("last_analysis", None)


def reset_upload():
    st.session_state.upload_nonce += 1
    st.session_state.pop("last_analysis", None)


st.caption("MP3, WAV, FLAC, OGG or M4A; maximum 5 minutes and 100 MB.")
with st.container(border=True):
    uploaded = st.file_uploader(
        "Choose an audio file",
        type=["mp3", "wav", "flac", "ogg", "m4a"],
        help="After choosing a file, wait for the filename and green confirmation below. No need to trim a song shorter than five minutes.",
        max_upload_size=100,
        key=f"song_upload_{st.session_state.upload_nonce}",
        on_change=new_selection,
    )
    if uploaded is None:
        st.info("No file received yet. Select a file above; its name will appear here when the upload finishes.")
        st.caption("On Android, if selection doesn't stick, try Chrome's Files picker or refresh the page. Some Android file pickers fail to return a file to Streamlit.")
    else:
        size_mb = uploaded.size / (1024 * 1024)
        st.success(f"File received: {uploaded.name} ({size_mb:.1f} MB)")
        if uploaded.size == 0:
            st.error("This file is empty. Please select another recording.")
        elif uploaded.size > MAX_BYTES:
            st.error("File exceeds the 100 MB limit. Choose a smaller file.")
        else:
            if st.button("Analyze recording", type="primary", use_container_width=True):
                with st.spinner("Checking audio fingerprints...", show_time=True):
                    try:
                        rows, meta = analyze(uploaded.getvalue(), uploaded.name)
                    except ValueError as exc:
                        st.error(str(exc))
                    except Exception:
                        st.error("Analysis failed. Please check the server logs or try a different file.")
                    else:
                        st.session_state.last_analysis = (uploaded.name, uploaded.size, rows, meta)
    st.button("Clear selection / try another file", on_click=reset_upload, use_container_width=True)

if uploaded is not None and "last_analysis" in st.session_state:
    name, size, rows, meta = st.session_state.last_analysis
    if name == uploaded.name and size == uploaded.size:
        st.success(f"Recording: {meta['duration']:.1f}s. Automatically analyzed {meta['analyzed_seconds']:.1f}s across {meta['diagnostics']['sampled_sections']} section(s).")
        st.markdown("### Results")
        shades = {"High": "#18794e", "Possible": "#ae7115", "Unclear": "#6b7280"}
        for label, item in rows:
            left, center, right = st.columns([2.2, 2.2, 1.1], vertical_alignment="center")
            left.markdown(f"**{html.escape(label)}**")
            center.write(item["result"])
            color = shades.get(item["certainty"], shades["Unclear"])
            right.markdown(
                f'<span style="display:inline-block;background:{color};color:white;padding:4px 9px;'
                f'border-radius:14px;font-size:12px;">{html.escape(item["certainty"])}</span>',
                unsafe_allow_html=True,
            )
            with st.expander(f"Explanation: {label}"):
                st.caption(item["detail"])
        with st.expander("Beta diagnostics (not source classifications)"):
            diag = meta["diagnostics"]
            st.write(f"Audio codec: {meta['codec']}")
            st.write(f"Input sample rate: {meta['input_rate']:,} Hz")
            st.write(f"Channels: {meta['channels']}")
            if diag["spectral_upper_energy_khz"] is not None:
                st.write(f"Upper detected spectral energy: approximately {diag['spectral_upper_energy_khz']:.1f} kHz")
            st.write(f"Near-full-scale samples: {diag['near_full_scale_percent']}%")
            st.write(f"Possible brief signal interruptions: {diag['possible_interruptions']}")
            if diag["pilot_frequency_scatter_hz"] is not None:
                st.write(f"FM pilot frequency variation (robust estimate): {diag['pilot_frequency_scatter_hz']} Hz")
            st.caption("These are experimental measurements, not definitive source identifications.")
        st.info("Unclear means insufficient evidence, not proof that a source was absent. Confidence labels are not calibrated probabilities.")

st.divider()
st.caption("The file is handled temporarily in server memory and a temporary file during analysis. Do not upload confidential material without reviewing the host's policies.")
