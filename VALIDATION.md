# AudioCheQ v2.6.0 verification

## Regressions

- 61 audio-analysis tests passed.
- 48 file-format, metadata, RDS, chart and new-feature tests passed.
- 51 UI, upload-flow, startup, display-safety and ranking tests passed.
- Total: 160 passing tests, run in three groups.
- A versioned engine import test confirms app.py binds to audiocheq_engine_v260.py, not an older `analyzer.py`.

## Supplied recording checks (local, not on Streamlit Cloud)

| Recording | NDR 10 kHz feature | Top path | Heuristic confidence | Cutoff measurement |
|---|---|---|---:|---:|
| TMS from Compilation A.mp3 | Detected around 10,298 Hz | FM-related | 71% | 16.0 kHz |
| N01-21-11-01_tape-2_TMS.mp3 | Detected around 9,931 Hz | FM-related | 71% | 16.0 kHz |
| Everyone_Knows_That.mp3.mpeg | Full 10 kHz region unavailable | Possible TV/video-related | 60% | 16.0 kHz |
| Historical Hysterics Rag MP3 | No confirmed NDR dip | Vinyl | 79% | 18.2 kHz |

All four recordings completed without an optional-check TypeError. The two NDR recordings generated **real** hum, cutoff and notch spectrogram PNGs alongside the earlier peak plots, each below the inline encoded-graphic size limit. The same files were used to check that charts show the measured feature as an outline and do not paint reference lines through the evidence.

## Responsive visual checks

Chrome/Chromium static HTML previews generated from the actual app CSS and result-card renderer: 1440 px desktop, 850 px tablet, 390 px phone. No horizontal overflow was observed. Desktop displayed the source card at full width and subsequent cards in two columns. Tablet and phone were one-column layouts. Note this is a **static browser check**, not a live Streamlit session.

## Known limits

Origin percentages are heuristic and the 10 kHz filter clue is not unique to NDR or FM. Raw-RDS decoder installation and the live Streamlit deployment were not verified in this environment. Tests do not ship the audio sources.
