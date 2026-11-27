# AudioCheQ v2.5.0 — Forensic evidence and readable results

A five-minute audio-forensic tool for identifying source and recording-chain clues in MP3, FLAC, WAV, OGG, and M4A files. The app does **not** identify music by database or claim to authenticate an artist, date or broadcaster from a frequency signature.

## What's improved in 2.5.0

- **Resolved optional `measured descriptions: TypeError`** for non-text and irregular tag values. Observation notes now normalize numbers, dates, missing fields and unusual metadata structures. Remaining edge cases only affect explanatory notes, never actual signal results.
- **Evidence-led likely origin**: an independent `origin_fusion.py` combines vinyl rotation/clicks, crackle, tape dropouts, 19 kHz FM pilot, RDS *actually decoded from raw multiplex data*, 10 kHz filter notch, bandwidth, plausible wow/flutter and channel timing. Electrical hum and TV scan signals are reported as *context* but are not used as proof of FM. Confidence rises when specific, independent clues agree. An MP3 codec is not treated as proof of a digitally recorded original.
- **Combined Stereo/Mono & Phase**: a single result card with one highlighted stored-channel classification, greying the alternatives and showing numerical correlation and channel delay where measured.
- **Readable “Why?”**: explanation first, followed by a compact list of actual measurements from this file, in the same disclosure. No separate nested technical disclosure. A source-score display is clearly labelled as relative clue weights, **not probabilities**.
- **Embedded metadata in the card**: title, artist, album, comments, URLs, encoder tags and additional readable fields are displayed as a scrollable list *inside* the “Why?” section, with a full tabular copy in File details. All text is escaped to prevent HTML injection.
- **Power-frequency geography**: examples of many countries using 50/60 Hz (including Japan's east/west split) are shown with a warning that hum can be introduced during a later transfer.
- **Peak plots**: unfilled orange outline rectangles surround measured peaks and troughs; no lines are drawn through the measured graph. The optional full spectrogram renderer retains frequency reference labels on the axes, not across the data.
- **More conservative wow handling**: an extreme, unstable reference-tone track no longer produces a false claim of normal tape wow. The suspicious raw measurement is still explained.
- **The 10 kHz notch detector is unchanged from v2.4**. Both of the known MP3 examples still register the characteristic band dip.

## Deploy to Streamlit Community Cloud

1. Extract the full ZIP on your computer. Do **not** commit the ZIP itself as the app: GitHub does not unpack ZIPs.
2. Upload the extracted project files into the **root of the deployed GitHub repository**, replacing existing files. Include the hidden `.streamlit` folder and new `origin_fusion.py` module.
3. Commit on the branch selected in Streamlit Cloud, and choose **Manage app → Reboot app** to clear stale imports.
4. The website heading must show **v2.5.0** and a new report must say **Analyzed with engine: 2.5.0**.
5. `app.py` explicitly imports `audiocheq_engine_v250.py` alongside it; an older `analyzer.py` cannot silently override it. The ZIP also includes a matching `analyzer.py` for legacy tests / integrations. Older versioned engine modules can be removed from GitHub, but aren't imported by this build.

A smaller update archive contains `app.py`, `audiocheq_engine_v250.py`, `analyzer.py`, `origin_fusion.py`, `observations.py`, and `spectrograms.py`. All six are necessary for a minimal upgrade from v2.4.3.

## Evidence limitations

- Relative origin scores are heuristics, **not statistically calibrated probabilities** or verified origin claims. An FM broadcast recorded to cassette can carry signatures of both media.
- A 10 kHz dip may reflect historical broadcast filtering; it does not establish NDR as the broadcaster. A 50/60 Hz hum may have been introduced during any recording/copying stage and cannot establish the performer's country.
- Stereo/phase measurements describe the **present file** and can change with mixing and later transfers.
- Not all recordings contain stable enough electrical/TV/FM tones to estimate wow/flutter or absolute playback speed. Musical tuning cannot, alone, prove a speed error.
- `redsea` must be available on the host to decode real 57 kHz RDS multiplex data; ordinary audio files generally do not contain it. This auto-install route has not been verified on the user's live Streamlit server.
- The code and browser-static layout have been tested locally. **The live Streamlit deployment and redsea bootstrap remain unverified**.

## Development

Run `pip install -r requirements.txt`, install FFmpeg (see `packages.txt`), and use `streamlit run app.py`.

Tests: `PYTHONPATH=. pytest -q tests/` (on a sufficiently provisioned machine). The tests use synthetic signals and do not ship the user's recordings.
