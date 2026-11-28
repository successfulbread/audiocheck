# AudioCheQ v2.7.3 — Detailed analog measurements

Web-based Streamlit app for lostwave audio investigation. This release keeps the existing 5-minute/100 MB limits, upload cleanup, responsive cards, NDR detector and FM cutoff gate.

## Install this update

1. Extract `audiocheq-v273-measured-evidence-update.zip`.
2. Upload **all extracted files** to the root of the existing GitHub repository (replace matching files; add the new modules). Do not upload the ZIP itself.
3. Commit the changes and reboot the app in Streamlit Cloud. Confirm the title says **v2.7.3**, then upload a fresh recording.

The update assumes the current v2.7.2 installation. Use the full ZIP for a fresh deployment or if any supporting modules are missing. The full ZIP contains requirements, Streamlit configuration and tests. Run locally with `streamlit run app.py` after installing dependencies in `requirements.txt` and `packages.txt`.

## What changed

- One combined Analog wear, tape & disc measurements card: surface clicks/crackle, quiet-band hiss and variation, wow/flutter by modulation band, whole-signal interruptions, treble-only dropouts, changing stereo-delay/azimuth candidates, rumble and faint-copy similarity screening. Open **Why?** to see actual measurements and time locations.
- Actual matched RPM click times, unmatched click candidates, channel, fitted period and fit error. All timestamps are relative to the uploaded file.
- Tape-like evidence contributes directly to source scoring. Credible alignment evidence prevents weakly corroborated vinyl signatures from winning over tape. Strong independent disc clues can still win; the report notes possible mixed transfer chains. Origin and analog cards show the exact same weighted scores and individual contributions.
- More numerical observations throughout the existing cards, including measured frequencies, harmonic observations, notch depth, candidate prominence, range/cutoff and pitch data. No new source categories or hosting dependencies.
- Preserves bounded excerpt-based processing and releases temporary upload/plot files. Audio itself is not retained in the report.

## Interpretation limits

A recording may pass through several media. Delay is compatible with tape-head azimuth, not a physical head measurement; mixing and digital processing can imitate it. Wow/flutter needs a reliable technical tone; faster modulation requires a sufficiently high and prominent reference. These are unweighted estimates, not calibrated industry wow/flutter measurements. A lack of a usable reference is reported as not measurable. A faint-copy similarity screen only compares content present in sampled excerpts; it cannot verify unknown audio from the opposite side of a cassette. Echo candidates are not scored as decisive medium evidence. All scores are heuristic evidence weights, not statistical probabilities. Results cover selected excerpts rather than every second of longer recordings.

## Additional existing limitations

- Source-origin percentages are **not calibrated statistical probabilities**. Multiple formats can appear along one recording chain. Hiss or lost treble may result from a later copy rather than an original cassette or broadcast.
- The historical 10 kHz dip is **not unique to NDR**. 50/60 Hz hum and 15,625/15,734 Hz scan lines do not by themselves identify a country or a television broadcast.
- Detecting wow/flutter requires a trustworthy pitch reference. Without a quiet passage, hiss measurement is often unavailable rather than truly negative. Spectral cutoffs caused by MP3 compression are not broadcast evidence.
- Raw broadcast RDS decoding requires the optional redsea executable and a suitable high-rate FM multiplex capture; ordinary music files generally cannot preserve 57 kHz RDS.
- Streamlit Cloud / optional redsea compilation have not been tested live in this environment.

## Running locally

Install FFmpeg and the Linux requirements in `packages.txt`, then `pip install -r requirements.txt` and `streamlit run app.py`. Run `PYTHONPATH=. pytest -q tests/` for the regression suite. The user's audio is used only for local verification and is **not bundled**.
