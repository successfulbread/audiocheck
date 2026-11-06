# AudioCheck v0.9 — validation notes

## Tests executed locally

- `PYTHONPATH=. pytest -q tests`: **49 passed** (synthetic audio plus no-signal, incorrect-standard and non-periodic-click controls).
- Syntax compilation: `python -m py_compile analyzer.py app.py` passed.
- Streamlit itself could not be installed in this isolated build environment, so the hosted app's visual appearance and phone file picker have **not** been run end-to-end. The theme uses the supported Streamlit `.streamlit/config.toml` format.

## Uploaded reference recordings

**Everyone_Knows_That.mp3.mpeg**, supplied by user, 17.3 seconds, MP3 at 44.1 kHz:

- TV interference: **Likely NTSC-type TV interference**, with a measured narrow frequency peak around **15,734.3 Hz** (approximately **34 dB** above nearby spectral energy on an averaged spectrum).
- Power region: **Possible 60 Hz region (North America and others)**, *tentative*; also contained 50 Hz candidates, so no original recording country is asserted. The 60 Hz line was stronger in the initial measurements, but musical tones are an alternative explanation.
- Source guess: **Possible TV / monitor recording**, because of the TV scan tone; this signal may have entered in a later transfer or from nearby equipment.
- NDR-style 10 kHz dip: **Not found**.

**Hysterics Rag (A Trombone Fit) — Tony Parenti's Ragtimers**, supplied by user, 168.3-second MP3:

- Source guess: **Likely record (vinyl/shellac)**, based on short irregular impulses and crackle that persists through quiet passages. This does **not** give a trustworthy RPM.
- Power region: a **tentative 50 Hz candidate**; not proof of a European recording location.
- TV/FM tone: no qualifying persistent tone found.
- NDR-style 10 kHz dip: not found.

## Engineering controls (among the 49 tests)

- Idealized 33⅓, 45 and 78 RPM click trains detected.
- Seven sparse 45 RPM clicks now produce only a *relaxed/tentative* rotation hit.
- Regular non-impulsive drums and non-periodic pops do not automatically produce an RPM.
- Synthetic broadband filtered material with a sharp notch at 10,000 Hz, 10,135 Hz and 10,310 Hz is detected; broadband audio without the notch is not flagged.
- A TV tone at 15,751 Hz (slightly away from nominal NTSC) is correctly picked up. Broadband music without TV/FM lines returns no broadcast tone.
- 50 Hz and 60 Hz hum with harmonics survives moderately compressed MP3 and opposite stereo-channel phase. Pure white noise and synth music without hum are negative controls.
- Five-minute MP3 accepted; files exceeding five minutes rejected.

## Interpretation and limitations

These are **heuristic screens**, not scientifically validated forensic likelihoods. The RPM relaxation can produce additional false positives in rhythmic music; weak matches are explicitly tentative. The NDR notch is a filter signature and is not specific enough to establish a broadcaster. Broadcast and hum signatures can be introduced at any stage of the recording chain. More independent real-world controls (commercial vinyl, shellac 78s, cassette dubs, clean digital masters, broadcast recordings) are needed to measure sensitivity and specificity.
