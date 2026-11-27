# AudioCheQ v2.6.0 — Responsive forensic results and boxed spectrograms

An audio forensic web app for MP3, WAV, FLAC, OGG and M4A recordings. Supports five-minute uploads, Archive.org URL imports, source-path clues, NDR-style 10 kHz band notches, mains hum, radio/TV interference, stereo phase, speed/wow/flutter, embedded metadata and optional RDS decoding for suitable raw FM multiplex recordings.

## Changes in v2.6.0

- **Responsive result cards:** The origin result spans the desktop layout, while other result cards sit in two columns on large screens and one column on phones/tablets (up to 1020 CSS pixels). Opening a technical explanation no longer forces every graphed card to use the full row.
- **Origin ranking:** Six paths are considered: vinyl, cassette/tape, FM radio, AM radio, TV/video-related and digital. A transparent *estimated evidence confidence percentage* considers both absolute source-specific evidence and the strongest alternative. It is a heuristic indication, **not a calibrated probability** or proof of an original master. The origin card displays leading reasons and additional evidence in its single Why? section.
- **Bandwidth evidence:** The source report now retains measured upper-frequency reach, a median relative 15 kHz attenuation, the number of sharp-cutoff sections and the original sample-rate ceiling. The graph highlights a true measured transition only when independently supported and not created by the digital sample-rate limit. FM audio normally has a near-15 kHz upper audio limit, but MP3, copy filters and tape equipment can create similar cutoffs.
- **TV signal path:** A 15,625 Hz / 15,734 Hz signal can rank TV/video as a *possible* source or copying stage; it does not prove the music was broadcast from TV. A pure TV tone receives an intentionally capped percentage.
- **Channels & phase balance:** Clear main verdicts for mono, dual mono, stereo, and possible channel delays/phase inversion; a single Why? explains correlation and offset values in plain language with technical measurements.
- **Real frequency spectrograms:** Boxed frequency/time plots for 50/60 Hz hum and harmonic, the detected 10 kHz dip and possible upper-frequency cutoff. No reference line is drawn through the measured tone or dip. The existing detailed peak-spectrum plots remain available. Images are palette-compressed to reliably fit within Streamlit's image embedding limit without changing spectral measurements.
- **Dedicated versioned engine:** `app.py` loads `audiocheq_engine_v260.py` beside it. The bundled legacy `analyzer.py` is the matching v2.6.0 code for older tests/integrations. Neither file falls back to previous engines.

## Update GitHub / Streamlit Cloud

1. Unzip the **complete project ZIP**. Upload its **contents**, not the ZIP, into the root of the GitHub repository used by Streamlit. Replace existing files, including `app.py`, `analyzer.py`, `origin_fusion.py`, `spectrograms.py`, `.streamlit/config.toml`, `requirements.txt` and **add** `audiocheq_engine_v260.py`.
2. Commit to the actually deployed GitHub branch, then open Streamlit's **Manage app → Reboot app**.
3. Confirm the heading reads **v2.6.0** and a new report reads **Analyzed with engine: 2.6.0**. If a previous report is still visible, upload the file again to regenerate its findings and charts.
4. The five-file update ZIP is suitable only when the other supporting v2.5.0 files are already current. The full project is safer when deployments have shown module mismatches.

## Interpretation limits

- The percentages are heuristic evidence-confidence indicators; **they are not statistically calibrated odds** or measured certainty about the original studio format. One song can have passed through several media (radio → cassette → MP3, etc.).
- The NDR-style 10 kHz dip is a meaningful filter clue, but it does not uniquely identify NDR or FM. Likewise, 50/60 Hz hum cannot identify the artist's country, and a 15,734 Hz TV scan tone may reflect monitor interference during a later transfer.
- Musical A440 tuning, wow/flutter and sample-rate cutoffs need corroboration before concluding that playback speed or original recording technology is known.
- On-air RDS decoding requires high-rate raw multiplex audio and the optional redsea utility; normal music recordings rarely preserve 57 kHz RDS.
- Streamlit/Redsea behaviour on the **live** hosting service has not been confirmed by these local automated tests.

## Development

Install FFmpeg and the Linux packages listed in `packages.txt`; run `pip install -r requirements.txt` and `streamlit run app.py`. For regression tests: `PYTHONPATH=. pytest -q tests/`. Test audio files from the user are **not shipped** in this project ZIP.
