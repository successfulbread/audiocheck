# AudioCheQ v2.4 — validation

## Real user-supplied recordings (not included with the distributable code)

The exact submitted MP3s were reopened and analyzed through v2.4 `analyze_path()`:

| File | Finding | Typical centre | Strongest depth | Positive sections |
|---|---|---:|---:|---:|
| TMS from Compilation A.mp3 | Detected, High certainty in the notch itself | 10,298.25 Hz | 3.76 dB | 3/3 |
| N01-21-11-01_tape-2_TMS.mp3 | Detected, High certainty in the notch itself | 9,930.84 Hz | 4.58 dB | 4/4 |
| Everyone_Knows_That.mp3.mpeg | No measurable 10 kHz notch region | n/a | n/a | 0 |
| Tony Parenti's Ragtimers MP3 | No confirmed notch | n/a | n/a | 0 |

For the N01 sample, the full evidence-chart path returned an NDR peak plot and a phase estimate with median interchannel delay approximately +0.181 ms. These measurements describe the **digital files as provided**, not proven recording provenance.

## UI verification

- The v2.4 static preview uses actual results from the Compilation A MP3.
- Chrome/Chromium rendering at 390 px and 1,120 px shows all 14 cards without horizontal overflow.
- Every result card has a single 'Why?' disclosure, one highlighted possible outcome, and muted alternatives.
- The file-source and NDR cards appear first in the report; NDR includes observed notch frequency, depth and sampled-section count.
- Phase and Stereo/Mono appear as separate cards. Phase displays median correlation and delay in the main card; its plot is labelled as an example excerpt, which may not equal the median across the full sampled sections.
- The visible release badge is `v2.4`; the report identifies its analysis engine as `2.4.0` and warns about a stale report.

## Regression checks

**134 tests passed**, executed in three groups because a single combined run exceeded the environment's time limit:

- Group A: **59 passed** (core analyzer, metadata history, RDS bootstrap, source scoring and UI defensive checks)
- Group B: **31 passed** (upload clearing, source frequency display, broadcast, NDR and chart tests)
- Group C: **44 passed** (prior and new UI, phase, speed, metadata/RDS and v2.4 outcome card tests)

## Caveats

- This is a code/runtime test with real local audio plus a **static HTML visual QA**, not a live hosted Streamlit deployment test.
- The high certainty displayed for a repeatable notch refers to the **spectral notch**, not to station identity. NDR/ARD broadcast fingerprints are not unique.
- If the user still sees 'Not detected' for either supplied file on Streamlit, first verify the visible build and engine labels. The hosted deployment or saved report may be stale or using a different file/version; the expanded file details include the raw screening measurements.
- The optional `redsea` decoder may require build dependencies and is not guaranteed to compile on every Streamlit Cloud image.
