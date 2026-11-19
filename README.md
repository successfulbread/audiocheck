# AudioCheck v1.6 — Dark Page / High-Contrast Evidence

A Streamlit web app that searches for clues in an audio recording: record-like clicks and rotation timing, cassette/tape artifacts, broadcast pilot/TV tones, 50/60 Hz electrical hum, an NDR-style 10 kHz spectral notch, stereo/mono, and the digital file's encoding history.

## Changes in v1.6

- **Dark navy page with an electric purple/coral header and turquoise waveform graphic.** Results stay easy to read: high-contrast pale cards for findings; subdued slate cards for absent/uncertain clues.
- **Higher-contrast spectrograms:** actual decoded audio plotted in near-black/purple-to-orange/yellow (`inferno`), with a turquoise *guide* line. A guide line is **not** evidence that a signal was detected. The heatmap uses one common colour scale across each plotted frequency band, never normalizes each frequency row, and does not feed back into the detector's scoring.
- **Technical “Why?” panels:** measured frequencies and details from the analyzer are retained; notes explain harmonic families, expected TV/FM frequencies, rotating scratch intervals, the 10 kHz dip, digital encoding dates, and limitations.
- **YouTube input removed** because server-side 403 errors made it unreliable. `yt-dlp` and Deno dependencies were removed. Keep uploading files or use a **direct Internet Archive audio-file link**.
- Preserves the five-minute limit, submit button, clearing the selected upload after analysis, source estimates, ranking, and digital-file dating.

## Updating the existing Streamlit app

Your repository remains **`audiocheck`**, entrypoint **`app.py`**. In GitHub, upload these files to the repository root (replace existing versions):

1. `app.py`
2. `spectrograms.py`
3. `requirements.txt`
4. `.streamlit/config.toml` (preserve the `.streamlit` folder)

The ZIP also includes current compatible `analyzer.py`, `archive_source.py`, `file_history.py`, and `packages.txt`. Upload those too if you are unsure whether your existing files match v1.5. The old `youtube_source.py` can be deleted from GitHub; it is no longer imported or needed. Commit changes to `main`; Streamlit should automatically redeploy. No need to move to another host. Use **Python 3.12** if recreating the app.

## Limitations

- These tests look for *evidence* in the transferred audio, not proof of where or when a song was originally recorded. A record can be copied to cassette and eventually encoded as MP3.
- The strongest narrow 50/60 Hz line can be a musical note; multiple persistent harmonics are better evidence of power hum. No signal is reported as certain without evidence.
- Bright pixels do not mean an artifact is automatically present; spectrograms are visual checks, and turquoise lines are expected frequency **references**.
- Adaptive display contrast is used **per complete band** (not per frequency), and only changes the chart appearance, not the analysis result.
- Digital codec history dates only the encoded copy; tags can be modified or rewritten.
- Cloud performance and user-device file picker behaviour still need testing on your live app.

## Tests

Run `python -m pytest tests -q` with Python 3.12+ and the requirements installed. `ffmpeg`/`ffprobe` must also be available (included via `packages.txt` on Streamlit Cloud).

See `VALIDATION.md` for results and known limits.
