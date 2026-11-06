# AudioCheck v1.1 — Audio Range + Digital File History

Fun forensic clues about old records, lost songs and digitized recordings. Light theme, colourful cards, short **Why?** explanations. Results are ordered from strongest clues to grey non-findings.

## What's new

- **Audio range & origin:** Measures broad frequency content without letting a lone TV/19 kHz pilot tone artificially increase the result. Describes wide range, limited high frequencies, a sharp FM/MP3-style cutoff, or sample-rate limitations. It considers the file's codec and MP3 bitrate before offering an interpretation.
- **Digital file history:** Reads metadata dates, encoder/software tags, LAME version, bitrate, and CBR/VBR. A recognizable encoder version can provide an earliest plausible **encoding** year; tagged creation dates are reported as unverified claims, not facts. A song's release/recording date is NOT shown as the file creation date.
- The existing disc, RPM, hum, broadcast/TV, NDR 10 kHz, stereo, tape-dropout, YouTube beta, 5-minute length and clear-after-upload features remain unchanged.
- Added `file_history.py` and the small `mutagen` dependency.

## Update your current Streamlit app

1. Unzip the project. In your GitHub `audiocheck` repository, upload the extracted files to the repository **root** (keep the `.streamlit/` folder structure).
2. **Required:** replace `app.py`, `analyzer.py`, and `requirements.txt`, and add new `file_history.py`.
3. Optionally replace `README.md`, `VALIDATION.md`, tests and `.streamlit/config.toml`.
4. Commit to the `main` branch. Keep Streamlit's app entrypoint as `app.py`.
5. Streamlit will install `mutagen` and restart. Python 3.12 is recommended if the existing app is already configured for it.

## What the findings mean

- **Audio range** is based on the frequencies present in the uploaded file. Hiss, crackle, low bitrate, sampling-rate limits and old transfer filters can all affect it; it cannot conclusively establish tape vs FM vs vinyl.
- **Digital file history** concerns the **last known encoding**, not the date the music was played or first recorded. It uses explicit encoding/creation tags when available, otherwise a recognizable software version. Tags may be edited or stripped, and later conversions replace earlier clues.
- YouTube converts streams, so the file history of a downloaded YouTube stream does **not** date the original upload.
- Current uploader supports MP3, MPEG audio, WAV, FLAC, OGG and M4A up to **5 minutes**, with a maximum file size of 100 MB.

## Testing

Run `PYTHONPATH=. pytest -q` if pytest is available, or deploy directly through Streamlit Cloud. See `VALIDATION.md` for tested examples and remaining limitations.
