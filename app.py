import streamlit as st
from analyzer import analyze

st.set_page_config(page_title='Audio Origin Analyzer', page_icon='🎵', layout='centered')
st.title('Audio Origin Analyzer')
st.write('Upload a short recording to look for clues about vinyl, electrical interference, and broadcast signals.')
st.caption('Experimental forensic tool · Not a verified determination of a recording’s location or original medium')

file = st.file_uploader('Upload an MP3, WAV, or FLAC', type=['mp3', 'wav', 'flac'], help='At least 5 seconds, at most 2 minutes and 20 MB.')
if file:
    st.audio(file)
    if st.button('Analyze recording', type='primary', use_container_width=True):
        if file.size > 20 * 1024 * 1024:
            st.error('Maximum file size is 20 MB.')
        else:
            with st.spinner('Analyzing audio signals…'):
                try:
                    results, meta = analyze(file.getvalue(), file.name)
                except Exception as exc:
                    st.error(f'Unable to analyze this file: {exc}')
                else:
                    st.success(f"Analyzed {meta['duration']:.1f} seconds at {meta['sample_rate']:,} Hz")
                    st.subheader('Results')
                    for label, item in results:
                        shade = {'High': '#18794e', 'Possible': '#b7791f', 'Unclear': '#6b7280'}[item['certainty']]
                        left, center, right = st.columns([2.1, 2, 1.2], vertical_alignment='center')
                        left.write(f'**{label}**')
                        center.write(item['result'])
                        right.markdown(f'<span style="background:{shade};color:white;padding:4px 9px;border-radius:14px;font-size:12px">{item["certainty"]}</span>', unsafe_allow_html=True)
                        with st.expander('Why this result?', expanded=False):
                            st.caption(item['detail'])
                    st.info('Unclear does not mean absent. Signals may be removed by compression, noise reduction, copying, or filtering. A detected tone may come from a later transfer rather than the original studio.')

st.divider()
st.caption('Uploads are processed in memory for the current analysis. Do not upload sensitive or unreleased recordings to a publicly hosted test instance without considering the hosting provider’s privacy terms.')
