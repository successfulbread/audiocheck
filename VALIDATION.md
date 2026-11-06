# AudioCheck v0.7 validation record

- 32 local automated checks passed (`PYTHONPATH=. pytest -q tests`).
- Audio signal tests cover synthetic 50/60 Hz mains with music/noise, anti-phase stereo, mono controls, 33 1/3 / 45 / 78 RPM signal processing, FM/TV tones, and FFmpeg decoding of short and five-minute recordings.
- YouTube link checks cover accepted/forbidden URLs, rejecting over-five-minute videos before a download, successful mocked retrieval, and blocked retrieval.
- The Streamlit page compiles with Python 3.13 (`python -m py_compile`).
- No live YouTube download was run. Server extraction may be blocked by YouTube and may require a supported JavaScript runtime on Streamlit Community Cloud.
- The new Streamlit form was not runtime-tested because Streamlit could not be installed in the offline test environment. It uses Streamlit's documented `st.form` and `st.form_submit_button` APIs.
- These are regression/synthetic tests, not a field-validated accuracy study on real historical media.
