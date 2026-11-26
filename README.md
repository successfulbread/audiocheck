# AudioCheQ v2.4 — audio-forensic clues

AudioCheQ is a Streamlit app for forensic analysis of short music recordings (up to five minutes): possible source medium, broadcast/tape signatures, stereo, phase/time delay, wow/flutter, pitch, playback-speed references, metadata, and possible recoverable RDS.

## v2.4 changes

- Clearly distinguish a **measured dip near 10 kHz** from the much weaker claim that the recording came from NDR. The reliable finding is the dip itself, not the station attribution. A broad, shifted and persistent dip is detected across samples near ~9.9 and ~10.3 kHz.
- Each result card displays every relevant outcome as a label, with **exactly one highlighted** and all others muted. An unavailable check is not silently treated as negative.
- Separate **Stereo / mono** and **Phase & channel timing** cards. The latter shows the multi-excerpt median channel correlation and offset in milliseconds, where measurable. A delay is not by itself proof of a tape transfer problem.
- Most cards show one or two relevant measurements in the main result, with a single, readable **Why?** explanation that references measured evidence from this file.
- A fixed, visible **v2.4** release marker in the header and **Analyzer 2.4.0** marker on each report help diagnose stale Streamlit deployments and saved reports. If a report is from an older engine, re-upload it.
- Under **File details & all embedded tags** is a table of measured 10 kHz screening candidates per sampled excerpt, including whether they met the requirements.
- All previous upload, Archive.org, metadata and RDS options remain.

## Install or upgrade on Streamlit Community Cloud

1. Download and unzip the **FULL** project package. **Do not upload the ZIP itself into the repository.**
2. Upload its contents to the **root** of your GitHub `audiocheck` repository; overwrite existing files. Ensure `app.py` and `analyzer.py` are in the repository root, not in a nested `audiocheq_v24/` folder.
3. Preserve the `.streamlit/config.toml` hidden directory and the updated `packages.txt` and `requirements.txt`.
4. Commit your changes to the branch configured to deploy your Streamlit app (usually `main`). Wait for Streamlit's deployment to finish.
5. Reload the Streamlit site. **Confirm the banner shows v2.4.** Analyze a newly selected recording. **Confirm the report shows `Analyzed with engine: 2.4.0`.** If it shows an older value, the hosted app has not loaded the matching analyzer, or the displayed report predates the update.

For an already functioning v2.3 installation, the smaller update requires only `app.py` and `analyzer.py`. If you are still seeing negative NDR findings, use the full-package upgrade to avoid mixing versions.

## Two recordings measured for this fix (audio files are NOT included)

- **TMS from Compilation A.mp3** — approximately **10,298 Hz** median notch, **3.76 dB** deepest dip, **3/3** sampled sections positive.
- **N01-21-11-01_tape-2_TMS.mp3** — approximately **9,931 Hz** median notch, **4.58 dB** deepest dip, **4/4** sections positive.

These numbers describe measured filter-shaped losses and are not proof the song aired on NDR; other radio and transfer chains can produce similar effects.

## Limitations

- The 10 kHz notch test is calibrated on a small selection of historical positive and negative examples, not an independently validated station classifier.
- Phase correlation measures the channels of *this file*. Artificial stereo, recording effects and later copying may change their relationship. Phase is frequency-dependent, so the app does not report a single invented phase angle in degrees.
- Playback-speed estimates rely on a verified pre-existing tone; instrument tuning alone does not establish the original speed.
- Raw FM RDS decoding requires preserved multiplex audio and the optional `redsea` executable. The deployment helper may build it on demand; the build has **not** been verified on the live Streamlit host.

## Components

- `app.py`: UI and reporting, including explicit version labels
- `analyzer.py`: windowed audio analysis and NDR checks
- `spectrograms.py`: frequency/phase/wow graphs from real audio
- `forensics.py`: stereo, phase, tuning and speed estimators
- `observations.py`: numeric measurements in the report
- `metadata_inspector.py`, `file_history.py`: file metadata and encoder history
- `rds_inspector.py`, `redsea_bootstrap.py`: optional broadcast RDS detection/decoding
- `archive_source.py`: Internet Archive direct-file support
- `.streamlit/config.toml`, `requirements.txt`, `packages.txt`: Streamlit deployment
- `tests/`: automated regression checks

## Local use

`pip install -r requirements.txt`

`streamlit run app.py`

Ensure FFmpeg/FFprobe are on PATH. Run the test suite with `PYTHONPATH=. pytest -q` (the included tests use synthetic signals, not your recordings).
