# AudioCheck v1.5 — Signal viewer

A lightweight, colourful Streamlit app for exploring clues in an audio recording. Upload an audio file (maximum **five minutes**), paste a direct Internet Archive audio link, or use the experimental YouTube option. The app suggests vinyl/record, cassette, FM/AM, or digital source clues, plus RPM, 50/60 Hz mains interference, historical television-frequency signals, the 10 kHz NDR-style dip, and digital-file dating information.

## What's new in v1.5

- The **Power region → Why?** card displays a *real spectrogram* of the uploaded audio around **50/60 Hz** and its **100/120 Hz harmonics**.
- The **Radio / TV signal → Why?** card displays a real zoomed view of **15,625 Hz** (625-line) and **15,734.26 Hz** (525-line) TV scanning frequencies. An extra **19,000 Hz** FM pilot view appears when the analyzer suggests FM evidence.
- The **NDR 10 kHz dip → Why?** card shows the audio around **10,000 Hz**; the clue is a **dark notch**, not a bright line. A frequency-profile graph underneath helps spot a dip.
- Graphs are made from **selected sections of the actual user recording**, not example audio. The dashed markings are **reference guides**, *not* detections. Bright horizontal streaks indicate measured narrowband energy; musical tones can sometimes resemble interference.
- Automatic positive-first ordering and grey uncertain cards remain. The refreshed light colour scheme uses stronger contrast, teal/blue/violet accents, and larger text.
- Only rendered PNG snippets are kept with the results during the Streamlit session. Decoded sound snippets are discarded after chart creation.

## Update your existing `audiocheck` GitHub repository

Replace `app.py`, `analyzer.py`, and `requirements.txt`, **add the new `spectrograms.py`**, and replace `.streamlit/config.toml` to get the new theme. Commit to `main`. Streamlit Community Cloud normally redeploys automatically. Leave `archive_source.py`, `youtube_source.py`, and `file_history.py` unchanged if you already have v1.4, or upload them from this ZIP as well.

The Streamlit entry point remains `app.py`; there is **no migration** or change of hosting service.

## Dependencies

- Python 3.12 or a supported newer version.
- `ffmpeg` and `ffprobe` (specified in `packages.txt`).
- Dependencies from `requirements.txt`, including **new** `matplotlib>=3.8,<4`.

## How to read the charts

- **Power**: look for a *persistent* horizontal streak near 50 or 60 Hz, ideally also at 100 or 120 Hz. A single musical note at 60 Hz isn't proof of mains hum.
- **TV/FM**: a narrow bright horizontal line and a corresponding spectral-profile spike suggest a broadcast-related tone. Its presence may reflect *later copying*, not the original studio.
- **NDR dip**: a persistent *dark* horizontal band and a spectral-profile trough near 10 kHz can resemble the known NDR-related recording artifact; it is not uniquely attributable to NDR.
- A **dashed red marker** simply shows where a reference frequency would be; it does not indicate a measurement was found.
- For performance, the app examines selected sections of each song, not every single second of a five-minute recording. It chooses the section with the most evidence for each plot.

## Research methods

Forensic ENF guidance recommends high-resolution windowed spectrograms, narrow frequency zooms, and inspection of harmonics. This implementation uses a **Hamming-window short-time Fourier transform**, a 2 kHz downsample for the power bands, and a 44.1 kHz decoded signal for higher-frequency TV/FM/notch views. Selected 18-second excerpts provide manageable plots. The plots are exploratory visualizations; the separate signal detectors supply the verdicts.

References:
- [ENFSI, Best Practice Guidelines for ENF Analysis, section 5.1.2](https://enfsi.eu/wp-content/uploads/2016/09/forensic_speech_and_audio_analysis_wg_-_best_practice_guidelines_for_enf_analysis_in_forensic_authentication_of_digital_evidence_0.pdf)
- [BitEU/ENF-Extractor](https://github.com/BitEU/ENF-Extractor)
- [josuenadal/ENF-extractor](https://github.com/josuenadal/ENF-extractor)
- [nate-griff/enf](https://github.com/nate-griff/enf)

## Test

From the repository root:

```bash
python -m pytest -q
```

Requires `pytest` in the local test environment (not a Streamlit hosting dependency). See `VALIDATION.md`.
