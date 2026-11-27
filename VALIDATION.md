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
