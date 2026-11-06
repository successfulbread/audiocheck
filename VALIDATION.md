# AudioCheck v1.0 validation

## Automated checks

58 tests passed in the development container (including synthetic 33 1/3, 45 and 78 RPM clicks; musical-drum false positive controls; real 50/60 Hz-style interference injected into synthetic music; TV/FM tones; NDR notch screening; browser-state upload clearing; result-card sorting; and missing-data resilience).

## User-provided real audio checks

**Tony Parenti's Ragtimers - Hysterics Rag**: 168.3-second MP3; 75 seconds sampled. Results: Likely Vinyl / Record (High); Disc crackle found (High); a weaker 45 RPM click-pattern guess (Tentative); possible 50 Hz interference (Tentative). The original disc's speed was not independently verified. This is not an accuracy claim for the 45 RPM guess.

**Everyone Knows That (EKT) sample**: 17.3-second MP3/MPEG. Results: a strong NTSC-type television frequency near 15,734 Hz; tentative 60 Hz electrical clue; no clear record-click signature. The 15,734 Hz detection does not prove the original studio's country.

## New UI tests

- All ten relevant checks produce cards even if some results are missing.
- Positive results sort first by measured strength, then grey non-findings.
- A normal successful file upload increments the file-picker key, clearing the chosen file on rerun while preserving the report.
- Untrusted filenames/results are HTML escaped.
- A static responsive layout was rendered for desktop and mobile. Full Streamlit Cloud deployment was not tested here.

## Limits

- Highly rhythmic percussion can mimic repeating groove clicks; tentative RPM guesses may be wrong.
- Crackle may be from shellac, vinyl, an earlier disc transfer, or other audio damage.
- Electrical hum and TV tones can enter during recording, copying, broadcast, or digitization.
- Short MP3s may discard high-frequency broadcast tones.
- YouTube retrieval can fail due to third-party access restrictions.

These are exploratory clues, not reliable source-identification probabilities.
