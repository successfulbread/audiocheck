# AudioCheQ v2.1 — Validation

Run `PYTHONPATH=. pytest -q` at the repository root. **117 tests passed** in the build environment.

## Added v2.1 tests

- Real, separately authored ID3 header: embedded title, artist, custom source/recording-machine and RDS_RadioText tags read without filename guesses.
- Readability, HTML escaping, binary-artwork exclusion and bounded text values for untrusted tags.
- Standard 44.1 kHz PCM and 48 kHz MP3 return **RDS not recoverable** from ordinary audio, while separately showing any RDS-named stored file tags.
- Simulated 192 kHz **MPX-like** WAV with a 19 kHz stereo pilot and 57 kHz modulated energy: spectral screening responds, but **does not claim decoded RDS** if an optional decoder is unavailable.
- A mocked, separately validated decoder return is surfaced as decoded data; this tests the integration and report handling, **not the correctness of redsea itself**.
- A normal, high-sample-rate non-MPX recording is rejected and never passed to the optional decoder.
- Full end-to-end WAV report populates all 14 visible card observations with measured sample-specific numbers, while retaining no raw decoded audio.
- Expanded Why? cards render the measured-data subsection **before** interpretation and escape malicious tag contents.

## Existing regressions retained

FM pilot offsets, power-frequency harmonics, TV scanning signals, 10 kHz notches, vinyl click timing, cassette-like dropouts, input sample-rate gating, encoder-date heuristics, phase/correlation, speed-reference conflict rejection, 0.75 Hz synthetic wow, musical tuning, graph rendering and clearing the upload widget are covered by existing tests.

## Real-world samples

- `Everyone_Knows_That.mp3.mpeg`: actual file has three readable encoder-related tag values; a 525-line TV-related peak survives, while no decoded RDS is recoverable at 44.1 kHz. 14 cards returned, each with numbered observations.
- `01 - Hysterics Rag (A Trombone Fit) - Tony Parenti's Ragtimers.mp3`: embedded title, artist, archive.org URL in its comment field, dates/encoder information and related metadata were recovered from the file. No RDS multiplex can be recovered from a 48 kHz MP3.

These two reference audio files are deliberately **not distributed** in the code ZIP.

## Visual checks

Rendered static HTML previews of actual EKT results using current CSS/card code in Chromium at 430 px and 1,100 px viewport widths. Both had **0 px horizontal overflow**, and all **14 cards** rendered. These are **static browser checks**, not a successful test on a live hosted Streamlit page. Live optional `redsea` decoding has not been tested on real radio multiplex data because no such recording or installed decoder was available in this environment.

## Key limitations

- A legitimate RDS subcarrier is BPSK and may be weak or absent in the source; the spectral screen is a *conservative candidate finder*, not a decoder.
- On-air RDS extraction requires both a compatible source recording and a separately installed redsea executable; `pip install` requirements alone do not provide it. The app must never claim RDS was recovered when only a pilot or RDS-band energy is present.
- The first 14 tag fields appear in the Why? card, up to 90 fields in full details. Binary/embedded artwork is omitted; overly long values are visibly shortened for resource safety.
- Older music files and repeated re-encodings can obscure source traces or rewrite metadata. All detector outputs remain clues requiring independent corroboration.

## v2.2 on-demand RDS decoder deployment

- New `redsea_bootstrap.py`: installs the pinned official `windytan/redsea` v1.3.1 binary into `/tmp` only when the RDS signal gate qualifies a raw MPX file. It never changes normal file analysis.
- `packages.txt` adds the Linux compiler, Meson/Ninja, libsndfile, libliquid and nlohmann-json build prerequisites to Streamlit Community Cloud.
- Focused tests: 11 passed (`tests/test_redsea_bootstrap.py` and `tests/test_v21_metadata_rds_observations.py`). The original v2.1 release had 117 passing tests before the bootstrap change.
- Full-suit tests were attempted but hit the environment's execution timeout during unrelated prolonged audio analysis; they were not claimed as passed for v2.2.
- Live Streamlit Cloud deployment, apt availability on that instance, downloading/compiling redsea and decoding a genuine raw MPX capture remain unverified. If build fails, the app reports decoder unavailable rather than fabricating station information.
