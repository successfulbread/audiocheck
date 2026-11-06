# AudioCheck v1.2 - Recording-source guesses and digital-file dating

AudioCheck is a Streamlit app for checking clues in MP3, WAV, FLAC, OGG, M4A and MPEG audio (4 seconds to 5 minutes; 100 MB maximum).

The homepage explains what it does: **Upload a song to check its likely source, record speed, broadcast signals and digital file age.**

## What changed in v1.2

- **Likely origin:** One bright result combining record crackle, repeated RPM clicks, FM pilot tones, tape-like gaps and frequency response. Crackle and dropout results no longer appear as duplicate main cards.
- **Rough score:** If meaningful evidence exists, the main card shows a percentage *clue score*. This is an uncalibrated relative evidence ranking, **not a probability** or scientific statement of original medium. A source may have passed through vinyl, cassette, FM and digital conversion in sequence.
- **Why?:** Each source result lists the actual supporting signals in plain English. Electrical/TV interference is reported separately; a TV scan-line tone alone does not prove radio, tape or record as the original medium.
- **Frequency fingerprint:** The old 'Audio range & origin' label is gone. This card reports cutoff, filtering, or wide-band sound; it is not treated as decisive medium evidence.
- **Digital file age:** Where recognizable, shows the earliest possible *digital encoding* year (for example LAME 3.99.5 -> 2012 or later; Lavc57.* -> 2015 or later). Codec, bitrate, VBR/CBR and encoder are still shown beneath the result. A tagged encode date is reported as an unverified tag. This does not date the original music.
- Existing file upload and YouTube beta remain. A successful file upload clears the file selection; results stay on screen. All remaining result cards are sorted by strength with greys last.

## Updating the live Streamlit site

1. Extract the ZIP. Open your existing GitHub `audiocheck` repository.
2. Replace `app.py`, `analyzer.py`, and `file_history.py` at the repository root. All other existing files can remain as they are.
3. Commit to `main`; Streamlit automatically redeploys. Keep `app.py` as the main script.
4. For a clean or full reinstall, also upload `youtube_source.py`, `requirements.txt`, `packages.txt`, and `.streamlit/config.toml`, preserving paths.

## Important interpretation

'Likely Vinyl' means the **audio carries evidence of a disc in its chain**. It may have been copied through tape or radio afterward. A 50/60 Hz hum suggests electrical equipment, not necessarily the original country. A high-frequency cutoff by itself cannot prove cassette, radio, vinyl or digital mastering. A digital file's codec date is a lower bound on the currently encoded version, not the date of the original recording.

## Running tests

`PYTHONPATH=. pytest -q`

The tests use synthetic signals, metadata-tagged MP3s and two user-supplied recordings (when available). Results are documented in `VALIDATION.md`. Live Streamlit Cloud deployment remains to be verified after GitHub update.
