# AudioCheQ v1.8 validation

- **100 local Python tests passed** (`python -m pytest -q`).
- Upload-state regression: native Streamlit file uploader immediately reports the filename, separate Analyze button runs the analyzer, and a changed widget key clears the finished selection without losing stored results.
- New UI regression checks: a single native uploader outside `st.form`, disabled Analyze button until a file has been received, and unchanged Archive.org audio option.
- Button contrast checks: file-picker, Analyze, and Archive actions all exceed 4.5:1 nominal text contrast (subject to Streamlit's actual DOM and browser rendering).
- Core analyzer, spectrogram, file dating and source-detection tests remain unchanged and pass.

## Caveats

The app has not been exercised against your live Streamlit Cloud deployment or your Android file picker. Changing from a form to the native uploader is a UI and state-management improvement, not a guaranteed repair for underlying mobile/browser/server transfer failures. If a file fails before the uploader displays its filename, the app has not received it. CSS selectors for Streamlit controls are implementation-dependent and may need updates when Streamlit changes its DOM.
