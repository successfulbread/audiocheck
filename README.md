# AudioCheQ v2.0 — Signal Forensics

Five-minute Streamlit audio-forensics application (MP3/MPEG, WAV, FLAC, M4A, OGG; 100 MB maximum), designed for lostwave provenance work. The existing dark theme, native two-step upload, Archive.org direct-audio input, 50/60 Hz screening, TV scan lines, NDR dip, vinyl noise/clicks, file history and origin guess are retained.

## New in v2.0

- **Dedicated 19 kHz FM stereo pilot check**: separate result card with observed frequency (Hz), offset from nominal 19,000 Hz, peak-to-local-band signal strength (dB), persistence in two halves of each excerpt and per-file section counts. A wide search allows moderate pitch deviations, with stricter local-prominence screening than the general TV detector.
- **Stereo phase / channel delay**: zero-lag Pearson correlation, strongest +/-4 ms cross-correlation, approximate lag in ms, L/R level difference, side/mid ratio and separate bass/mid/high correlation. Identifies polarity reversal, near-mono and possible delayed channel copies; does not prove tape azimuth.
- **Playback-speed *reference* estimate**: measures the observed/nominal ratio of a confirmed FM pilot, TV scanning frequency or multiple coherent mains harmonics; returns percentage and reverse mathematical correction. Rejects conflicting reference families. Never claims a speed error from tone that could have entered after transfer.
- **Musical tuning estimate**: votes from STFT spectral peaks across multiple pitched frames and note bins, expressed as cents relative to A440. Reports a hypothetical uniform speed correction as *unverified*; deliberate tuning, temperament and instrument harmonics can explain the same displacement.
- **Wow / flutter**: tracks instantaneous pitch of a spectrally confirmed stationary reference using complex demodulation and a phase derivative; shows RMS cents variation and the largest modulation-frequency peak, then labels possible periodic wow (~0.3–6 Hz), flutter (~6–30 Hz), drift or no clear wobble. No reference = not measurable, rather than false diagnosis from musical vibrato.
- **Peak-based evidence graphs**: measured Welch power spectrum profiles for 50/60 Hz hum, TV scanning, FM pilot and 10 kHz notch; frequency markers are on the horizontal axis (never drawn across peaks). Stereo delay correlation, tuning vote histograms and time-domain pitch drift graphs accompany findings where enough signal exists. The legacy `render_evidence()` spectrogram API remains for compatibility; normal displayed charts use the new peak plots.
- **Expanded Why?** sections: actual measured values, methods, threshold rationale, competing explanations, conditional assumptions and limitations. Uncertain findings are retained rather than forced into a detection.

## Update the existing Streamlit website

The app entry point is still `app.py`. Replace these files in the existing GitHub repository and commit to `main`:

1. `app.py`
2. `analyzer.py`
3. `spectrograms.py`
4. **New:** `forensics.py`

No new requirements or external music-matching services. For a clean installation, upload all files in this ZIP, including `.streamlit/config.toml`, `requirements.txt`, `packages.txt`, `archive_source.py`, `file_history.py` and `tests/`. Streamlit Cloud must have FFmpeg via `packages.txt`.

The main pipeline still examines up to four 25-second windows across a recording. Plot audio excerpts are disposed of after rendering, and only the derived summary and base64 plot images remain in the Streamlit session. No audio recording is sent to Shazam, fingerprinting databases or outside recognition services.

## Critical limitations

- A nominal 19 kHz pilot (or its absence) is **not proof** of FM origin; many receivers remove it. A lone unrelated high-frequency tone can sometimes mimic it. AudioCheQ operates on decoded 44.1 kHz stereo, so it **cannot test the 38 kHz FM multiplex subcarrier**.
- A measured frequency offset is a *conditional* playback-speed estimate, not evidence that the artist performed at another pitch. The tone could have been added later; a broadcast tone's frequency does not necessarily track the original song's transport speed.
- A440 musical tuning estimates are tentative, particularly for recordings with vibrato, unusual tuning, many harmonics or limited pitched content. Never use the hypothetical correction as a measured fact.
- Wow/flutter needs a confirmed, trackable tonal reference; it does not identify turntable speed or cassette speed from music alone. Frequency modulation from a real oscillator or mains can mimic mechanical wobble.
- Channel polarity and delay are properties of the *present copy*. They do not prove whether a tape machine, microphone, codec, remix or stereo effect caused the difference.
- The visualization's highest spectral bin is a measurement only; a source-specific detection requires the separate screening thresholds and temporal evidence. Encoder metadata and source clues cannot establish a lost song's identity.

See `VALIDATION.md` and `tests/test_v20_forensics.py` for reproducible verification.
