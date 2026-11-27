# AudioCheQ v2.7.0 — Analog-first origin analysis

AudioCheQ is a Streamlit audio-forensic investigation app for recordings up to five minutes. It examines vinyl/shellac transfer clues, tape hiss, dropouts, transport speed variations, FM/TV/electrical interference, the historic 10 kHz broadcast notch, pitch, file metadata and optional raw-RDS captures.

## What changed in v2.7.0

- **Prioritize analog evidence.** Vinyl crackle, rotational click patterns, a believable record-speed wobble, persistent tape-like hiss, transport speed instability and repeated dropouts all contribute more strongly to source assessment. Hiss is explicitly measured only in genuinely quiet passages and does not alone prove a cassette; a record can also carry hiss. An unreliable pitch tracker is never treated as wow/flutter.
- **FM requires measured cutoff.** The top result can be FM only when a sharp, reproducible frequency cutoff around the usual 15 kHz FM audio limit is present **and** a supporting signal (pilot, 10 kHz notch or decoded RDS) exists. A low-bitrate MP3 cutoff is excluded. FM pilot and NDR reports remain visible even when they cannot qualify the overall FM verdict. FM path confidence refers to recorded/copying stages, not the source of the original musical performance.
- **Less sensitive NDR test.** The 10 kHz filter must now be deeper, show both shoulders, outperform comparison bands and persist across checks. Notches can drift with tape speed. The two supplied NDR recordings still qualify, and EKT and the historical ragtime sample remain negative.
- **Clearer cards.** The app now shows discrete **surface crackle**, **background hiss**, **dropouts** and **frequency range/cutoff** cards, in addition to the previous checks. Positive and unavailable statuses are distinguished; unmeasurable hiss is not reported as hiss-free.
- **Fewer, more relevant details.** One **Why?** section per card defines its displayed terms (for example, RPM, Hz, dBFS, correlation, cents and RMS), interprets the specific measurement, and highlights limitations. Supporting raw observations are restricted to relevant measurements rather than showing long generic FFT diagnostics.
- **Retained v2.6 features.** Two-column desktop results and single-column phone/tablet view; percentage origin score labelled as a heuristic estimate; annotated real spectrograms for hum, 10 kHz dip and high-frequency cutoff; stereo/phase information; embedded tags and RDS.

## Install / update Streamlit Cloud

1. Download the complete ZIP and **extract it**.
2. Upload its **contents** to the root of the GitHub repository configured for Streamlit. Replace existing copies of `app.py`, `analyzer.py`, `origin_fusion.py`, and `observations.py`, and **add** `audiocheq_engine_v270.py`. Keep all remaining library files alongside them.
3. Commit to the actual deployed branch. In Streamlit Cloud, select **Manage app → Reboot app**.
4. Confirm the heading reads **v2.7.0**, and that a *freshly uploaded* report says **Analyzed with engine: 2.7.0**. Re-upload a recording if the old report remains in session state.

For a clean v2.6.0 installation, the five-file update ZIP is sufficient; otherwise prefer the full project.

## Interpretation limits

- Source-origin percentages are **not calibrated statistical probabilities**. Multiple formats can appear along one recording chain. Hiss or lost treble may result from a later copy rather than an original cassette or broadcast.
- The historical 10 kHz dip is **not unique to NDR**. 50/60 Hz hum and 15,625/15,734 Hz scan lines do not by themselves identify a country or a television broadcast.
- Detecting wow/flutter requires a trustworthy pitch reference. Without a quiet passage, hiss measurement is often unavailable rather than truly negative. Spectral cutoffs caused by MP3 compression are not broadcast evidence.
- Raw broadcast RDS decoding requires the optional redsea executable and a suitable high-rate FM multiplex capture; ordinary music files generally cannot preserve 57 kHz RDS.
- Streamlit Cloud / optional redsea compilation have not been tested live in this environment.

## Running locally

Install FFmpeg and the Linux requirements in `packages.txt`, then `pip install -r requirements.txt` and `streamlit run app.py`. Run `PYTHONPATH=. pytest -q tests/` for the regression suite. The user's audio is used only for local verification and is **not bundled**.
