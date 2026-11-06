"""AudioCheck Streamlit interface: minimal results plus optional beta diagnostics."""
import html
import streamlit as st
from analyzer import MAX_BYTES, MAX_SECONDS, analyze

st.set_page_config(page_title="AudioCheck - Audio Origin Analyzer", page_icon="\U0001F3B5", layout="centered")
st.title("AudioCheck")
st.subheader("Audio Origin Analyzer")
st.write("Upload a recording to look for evidence of vinyl, electrical hum, and broadcast signals.")
st.caption("Experimental analysis only. A result may describe a later copy or transfer, not the original studio.")

uploaded = st.file_uploader(
    "Upload audio (up to 5 minutes)",
    type=["mp3", "wav", "flac", "ogg", "m4a"],
    help="Up to 300 seconds and 100 MB. The app automatically analyzes several sections of longer recordings.",
    max_upload_size=100,
)
if uploaded is not None:
    st.audio(uploaded)
    st.caption(f"File size: {uploaded.size / (1024 * 1024):.1f} MB. Maximum duration: {MAX_SECONDS / 60:.0f} minutes.")
    if st.button("Analyze recording", type="primary", use_container_width=True):
        if uploaded.size > MAX_BYTES:
            st.error("File exceeds the 100 MB limit.")
        else:
            with st.spinner("Checking audio fingerprints...", show_time=True):
                try:
                    rows, meta = analyze(uploaded.getvalue(), uploaded.name)
                except ValueError as exc:
                    st.error(str(exc))
                except Exception:
                    st.error("Analysis failed. Please check the server logs or try a different file.")
                else:
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
                        st.caption("These are experimental measurements. Dropouts can be musical edits; pilot variation does not independently prove tape wow/flutter. Clipping, frequency content and file encoding do not prove the original source.")
                    st.info("Unclear means insufficient evidence, not that a source was absent. Certainty labels are conservative heuristics, not calibrated probabilities.")

st.divider()
st.caption("The uploaded file is temporarily handled in server memory and a temporary file during analysis. Do not upload confidential material to a public demo without reviewing the hosting service's policies.")
