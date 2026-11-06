# AudioCheck v0.5 - Alternate uploader + measurable evidence

Streamlit application for MP3, WAV, FLAC, OGG and M4A recordings up to **5 minutes** and **100 MB**. The server automatically analyzes up to four sections across the song (up to about 160 seconds total).

## New: alternative mobile upload method

AudioCheck now defaults to a custom browser file picker using JavaScript FileReader and Streamlit component communication, **rather than** the native Streamlit file uploader's upload endpoint. This alternative supports **25 MB files** (sufficient for nearly all five-minute MP3s) to protect phone/browser memory. Use **Standard upload** for WAV/FLAC files up to **100 MB**. Audio bytes are sent only to the current Streamlit app, not to a third-party upload host.

This alternate method may avoid some `st.file_uploader` mobile/connection bugs, but it still depends on Android successfully returning a file to the browser and on the web connection. It has not been verified on every Android device. A green `File received` line is the confirmation.

## Results

- **No distinctive signature / None detected** means the specific test found no qualifying signal, **not** that the recording was certainly not vinyl/cassette/radio.
- **Possible** means a signal passed an engineering threshold, not a calibrated probability.
- **Not measurable** is used for playback speed without a trusted reference, or frequencies outside the audio sample rate.
- Vinyl speed, 50/60 Hz power signatures, and FM/TV tones use the previously validated synthetic test methods.
- **Possible tape dropouts** and **upper audio energy** replace the speculative number of copy generations. Neither establishes whether a cassette was used.
- A record copied onto tape or broadcast on FM can retain signatures of multiple stages.

## Deploy to GitHub + Streamlit Community Cloud

1. Unzip and upload files to the **root** of the repository named `audiocheck`, replacing existing ones.
2. Commit changes to `main`; the deployed https://audiocheckq.streamlit.app/ app should update automatically.
3. The required `requirements.txt` installs Streamlit 1.60+, supporting custom components v2. `packages.txt` installs FFmpeg.
4. No additional upload hosting, API keys, or account setup is required.
5. Choose **Alternate phone-friendly upload** (default), select an MP3 and confirm green `File received` before pressing **Analyze recording**.

## Important limits

- The backup uploader transfers base64 over the app connection, raising memory usage by roughly one third or more; it is capped at 25 MB. Native upload remains available for bigger files.
- Source classification cannot reliably identify cassette from normal hiss/cutoff alone; don't assign a cassette result without new validation data.
- Musical percussion can mimic vinyl rotation, musical bass lines can mimic power harmonics, and synthesizers can produce stable high-frequency tones. The application does not claim calibrated confidence or original geographic provenance.
- Absence of pilot tone does **not** exclude FM: analog or MP3 low-pass filtering may remove it.
- Full Android mobile upload and Streamlit Cloud deployment are not covered by unit tests. Test the deployed app and report any problem.

## Run unit tests

`python -m unittest discover -s tests -v`
