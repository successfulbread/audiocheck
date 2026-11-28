# AudioCheQ v2.7.3 validation

46 targeted regression tests passed, including six new measured-analog tests and existing memory lifecycle, origin gating, NDR, layout, explanation and defensive-rendering tests. The new tests cover changing stereo delay, identical-channel and mono controls, two timed treble losses, clean and low-rate controls, low-frequency rumble, separately measured slow wow and flutter, conflict-aware source ranking, actual RPM click timestamps and end-to-end WAV analysis. The attempted full suite exceeded the execution limit; a stale theme expectation from a previous release was updated and subsequently passed. The full suite has not been verified in a single run.

Synthetic tests establish detector behavior on controlled signals, not real-world classification accuracy. No authentic cassette/record comparison corpus was available for this release. Live Streamlit deployment and extended memory load testing have not been performed. The experimental faint-copy screen is not independently validated as a print-through or reverse-side bleed detector.

# AudioCheQ v2.7.2 reliability validation

42 targeted tests passed locally (upload state, concurrency, temp-file cleanup, graph cleanup and failure, engine startup, spectrograms, hiss, NDR and layout). The complete suite was not completed in this environment. Browser/Streamlit Community Cloud behavior and long-term server RSS have not been verified. The actual host may retain uploaded bytes until widget cleanup and Python/native allocators may retain freed memory.

# AudioCheQ v2.7.0 validation

## Automated tests

167 tests collected across 24 test files. All tests passed when run in independent groups, including seven new v2.7.0 tests. The groups cover the analyzer, NDR notch, synthetic hiss, origin gating/weights, user interface, upload clearing, startup versioning, file-format metadata, RDS, graphics and defensive error handling. The full combined suite was not completed as one run because one long batch exceeded the execution limit; all test files were covered by smaller passing runs.

## Four existing real recordings (local, not Streamlit Cloud)

| Recording | 10 kHz notch | Origin verdict | Other clues |
|---|---|---|---|
| TMS from Compilation A MP3 | Detected ~10,312 Hz (2/3 qualifying sections) | Possible FM path, ~60% heuristic confidence | Cutoff ~16.0 kHz; no reliable standalone hiss detection |
| N01-21-11-01 tape-2 TMS MP3 | Detected ~9,931 Hz (4/4) | Possible FM path, ~61% heuristic confidence | Cutoff ~16.0 kHz; possible background hiss in quieter parts |
| Everyone Knows That MP3 | No usable 10 kHz notch | Possible TV/video-related stage | 15,734 Hz scanning line; codec-limited treble cutoff, not promoted to FM |
| Historical Hysterics Rag MP3 | No confirmed notch | Likely vinyl/record (~76% heuristic confidence) | Disc surface crackle, some RPM pattern and background noise |

All four completed without an optional forensic check error. These are *recording-path* hypotheses, not authentication of the original studio medium.

## Targeted synthetic checks

- Strong 19 kHz pilot plus measured ~15 kHz cutoff can produce a high-confidence FM result.
- FM pilot alone, NDR notch alone, weak cutoff, and codec-limited 90 kbps MP3 **cannot** produce an FM verdict.
- Repeated hiss, dropouts and credible flutter can outweigh competing FM evidence; near-45-RPM periodic wow supports vinyl with corroborating crackle.
- Broadband noise-only or an implausible pitch track does not falsely become record-speed wow.
- A generated intermittent-music recording with continuous noise reveals broadband hiss in quiet passages; a steady pure tone does not.
- Positive NDR recordings retained; unrelated controls remained negative.

## UI check

Static HTML assembled from the app's actual card functions/CSS was displayed in Chromium at 1440 px desktop and 390 px phone widths for both NDR and vinyl examples. Origin card spans the page width; other cards appear in two desktop columns and one mobile column. Both sizes had no horizontal overflow, with 17 result cards. This is a static CSS check, not a live hosted Streamlit session.
