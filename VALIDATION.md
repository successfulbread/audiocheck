# AudioCheQ v2.5.0 — Local validation

## Changes verified

- Startup loads `audiocheq_engine_v250.py` from the same directory as `app.py`. Both expose `ANALYZER_VERSION = "2.5.0"`.
- Main path creates 17 internal detector results and displays 13 cards, including **one** combined Stereo/Mono/Phase card. Every visible card has exactly one “Why?” disclosure and one selected outcome.
- `origin_fusion.py` ranks a confirmed 19 kHz FM pilot as strong FM evidence, a strong vinyl-crackle + click pattern as likely vinyl, and a 10 kHz notch *alone* as only possible FM-path evidence. Electrical-hum and TV-line clues do not falsely establish FM.
- Mixed-type metadata and unexpected tag objects do not stop the measured-descriptions stage. Text in the metadata card is HTML-escaped.
- Evidence figures render using unfilled orange rectangles, not horizontal/vertical reference lines through measurements.
- Static HTML is checked at 412px and 1100px with Chromium; no horizontal overflow. Real audio preview generated for NDR example.

## Real recording checks (local only)

The tests below were run against four privately supplied or previously available recordings; those audio files are deliberately excluded from the distribution archives.

| Recording | NDR notch | Source estimate | Optional errors |
| --- | --- | --- | --- |
| TMS from Compilation A.mp3 | Detected, ~10,298 Hz | Possible FM broadcast path | None |
| N01-21-11-01_tape-2_TMS.mp3 | Detected, ~9,931 Hz | Possible FM broadcast path | None |
| Everyone_Knows_That.mp3.mpeg | High-frequency range inadequate for a two-sided notch | Tentative default digital (not a source claim) | None |
| Hysterics Rag — Tony Parenti's Ragtimers.mp3 | Not detected | Likely vinyl/record | None |

The previously reported extremely large *wow* estimate in Compilation A was rejected as an unreliable reference-tone track rather than counted as plausible wow.

## Not verified

The user's own live GitHub/Streamlit deployment and optional `redsea` decoder build were not accessed or tested. A negative result on any untested upload is not proof of a recording's origin.
