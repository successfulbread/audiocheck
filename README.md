# AudioCheck v1.3

A light-themed Streamlit app for investigating clues in old recordings. Supports MP3, WAV, FLAC, OGG, M4A and MPEG audio files, up to 5 minutes and 100 MB.

## What's new

- **Frequency profile is now part of "Likely origin" -> "Why?".** The measured upper audio range and any sharp filtering are explained alongside the record/tape/FM clues. A low-frequency cutoff or 15 kHz limit alone is not proof of a specific source. The extra standalone frequency card has been removed.
- **More informative digital-file age.** Reads ID3 `TDEN` encoding-time and `TDTG` tagging-time separately from `TDRC`/`TDRL` music dates. Checks FFprobe's encoding, creation and software tags, and MP3 encoder version. LAME 3.99.5 can suggest no earlier than 2012-02-28; LAME 3.100 no earlier than 2017-10-13. FFmpeg Lavc version families 57-62 provide broader lower bounds. The "Why?" text explains which tag or version is responsible.
- **New Archive.org link option.** Paste a *direct audio file download link* such as `https://archive.org/download/identifier/track.mp3`. Only archive.org links and redirects are accepted. This is an alternative for authorized archival material, **not a way to bypass YouTube restrictions**.
- The original file-upload form and **YouTube (beta)** option remain. YouTube retrieval can still fail with HTTP 403 on Streamlit's server; there is no guaranteed purely-Streamlit fix.

## GitHub / Streamlit update

1. Extract the ZIP, open GitHub repository `audiocheck` and replace the following files at its root: `app.py`, `analyzer.py`, `file_history.py`, `youtube_source.py`, `requirements.txt`, `packages.txt`.
2. Add **new** file `archive_source.py` at the root.
3. Optional: replace `.streamlit/config.toml` to keep the light theme.
4. Commit to `main`. The existing Streamlit app will rebuild using `app.py`.

For the Archive.org tab, use the **downloaded MP3's own URL**, not the `/details/...` item page. Users should only retrieve recordings they have permission to analyze. Internet access from Streamlit Cloud to archive.org is required and may occasionally fail.

## Date interpretation

Dates are **about the uploaded digital encoding or file processing**, never about when the song was performed or recorded.

- Explicit ID3 `TDEN`: user-editable stated encoding date.
- Explicit `TDTG`: user-editable tagging date, **not** the original creation date.
- `TDRC`, `TDRL`, `date`, `year`: may describe the music, so never treat them as file creation dates.
- LAME `TSSE` / MP3 encoder tag: earliest availability of the *named software version*; files may have been created much later.
- `Lavc` = encoded audio's software family. `Lavf` = container writer (the file may have been remuxed later, without re-encoding).
- An undated MP3 is not automatically "from the 1990s"; an MP3 may be encoded today from a much older source.

Useful references:
- [ID3v2.4 frames: TDEN / TDTG / TDRC / TSSE](https://id3.org/id3v2.4.0-frames)
- [LAME release dates](https://github.com/enzo1982/lame/releases)
- [FFmpeg API version history](https://github.com/FFmpeg/FFmpeg/blob/master/doc/APIchanges)
- [yt-dlp YouTube notes](https://github.com/yt-dlp/yt-dlp/wiki/Extractors)

## Run tests

`PYTHONPATH=. pytest -q tests`

Version 1.3 local test suite: **89 passed**. Includes actual analysis of two user-provided historical recordings, synthetic signal tests, metadata-tag tests, and simulated Archive.org downloads. A real Archive.org download through the new tab and a live YouTube request on Streamlit Cloud have **not** been verified.
