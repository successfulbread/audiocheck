# AudioCheQ v2.1 — Embedded Metadata, RDS and Measured Evidence

Audio forensics / lostwave app for Streamlit. Supports MP3/MPEG, WAV, FLAC, M4A and OGG files up to 5 minutes / 100 MB, plus direct audio-file URLs from the Internet Archive. Retains the existing dark theme, native uploader, broadcast/NTSC/FM-pilot analysis, 50/60 Hz hum, 10 kHz dip, vinyl/cassette evidence, pitch/speed/wow/flutter, phase and peak-based graphs.

## New in v2.1

- **Embedded track / technical metadata card:** Reads textual tags actually saved in the file, via FFprobe and Mutagen. This includes ID3 (title, artist, album, year, encoder, encoding/tag dates, comments, website/source URLs, custom TXXX, selected unique IDs/ratings), MP4 tags, FLAC/Vorbis comments and readable WAV/RIFF tags where recognized. Duplicated identical fields are consolidated. Artwork/binary image payloads are never rendered. The card lists the first 14 found fields and reports the total; **File details & all embedded tags** displays up to 90 readable fields in a table. Oversized values are visibly truncated. No name is guessed from the filename or matched against outside catalogues.
- **RDS / RadioText card:** Explicitly distinguishes (a) **RDS-like text stored as file metadata** from (b) **actual on-air RDS digital data**. A normal 44.1/48 kHz file physically cannot preserve the 57 kHz FM multiplex subcarrier; a 19 kHz FM pilot does not imply any recoverable RDS. For mono, lossless **WAV or FLAC at >=128 kHz**, AudioCheQ checks the 19 kHz pilot and relative energy in the **57 kHz ±1.5 kHz** band. An apparent signal is reported as a *candidate only*. If the optional `redsea` command-line decoder is installed, AudioCheQ passes a bounded MPX excerpt to redsea and returns PI / PS (station) / RadioText / RT+ song and artist fields **only if the decoder emits repeated, consistent PI-coded RDS groups**. No decoded data is invented or inferred from spectral energy.
- **Data-rich Why? sections:** Every one of the 14 visible finding cards now leads with **Measured in this file**: actual excerpt times, sample rate/Nyquist, accepted/not-accepted harmonic and tone peaks, RMS click timing, spectral notch depth versus controls, bandwidth limits, dropouts, stereo correlation, phase, reference-tone tracking and other detector data applicable to that finding. Numerical metrics precede a separate **Interpretation & limits** explanation. Where a detector failed, it reports the tested windows, thresholds and/or actual candidate data rather than fabricating a frequency.
- **File details:** Container, sample representation, stored bit depth where reported, bitrate, channels, byte count, analyzed duration and a scrollable table of embedded tags. Read-only. User-supplied text is escaped in generated HTML cards.

## Updating Streamlit Cloud / GitHub

Upload the complete ZIP into the existing repository or replace/add just these files:

- **Updated:** `app.py`, `analyzer.py`
- **New:** `metadata_inspector.py`, `rds_inspector.py`, `observations.py`

The existing `forensics.py`, `spectrograms.py`, `file_history.py`, `archive_source.py`, `.streamlit/config.toml`, `requirements.txt` and `packages.txt` are unchanged and included for a full, compatible replacement. Keep `packages.txt` with `ffmpeg`.

No new Python dependencies and no external music-identification/search API. The app examines bounded parts of the file and retains only derived results and chart PNGs, not raw decoded audio in session state.

### Optional redsea decoder for raw FM multiplex only

RDS can be decoded from the original **raw demodulated FM multiplex (MPX)** signal, *not* normal FM audio output. If you need actual bit-level RDS decoding on a machine with a compatible capture, install [windytan/redsea](https://github.com/windytan/redsea) and ensure the `redsea` executable is on the application's PATH. Redsea is **not bundled**, is **not installed by `requirements.txt` or `packages.txt`**, and is not assumed present on Streamlit Cloud. The app reports **decoder unavailable** if an eligible MPX candidate is found but redsea is absent. A decoder returning no consistent groups is a negative result; spectral peaks alone do not establish transmitted station or song details. RDS Station/RadioText fields already stored in *ordinary file tags* are displayed without redsea, clearly labelled as stored metadata.

## Scientific interpretation

- Metadata is mutable. A title, artist, date or broadcast-station URL stored in a file is evidence about that *file* and its history, not verification that the source recording is authentic.
- 57 kHz is above the Nyquist limit of normal 44.1/48 kHz audio and is normally removed by FM receivers. Only a high-rate, suitable **raw MPX** capture can be used for on-air RDS decoding. 192 kHz music audio is not automatically a multiplex capture.
- Reference-tone speed estimates are conditional on the reference pre-dating the speed change. A440 tuning bias is a weak indication, not a proven playback-speed correction.
- A candidate 10 kHz notch, 19 kHz line, 50/60 Hz hum or 33⅓/45 RPM click train can have unrelated sources. No result establishes the artist's identity without further evidence.

See `VALIDATION.md` and the included unit tests for measured behaviour and limitations.


## Optional automatic redsea RDS decoder (v2.2 deployment update)

The updated `packages.txt` installs redsea **build prerequisites** on Streamlit
Community Cloud (it does not claim that redsea itself is an apt package).
On the first upload of a *suitable raw high-rate mono FM multiplex WAV/FLAC*
with measurable energy around 57 kHz, `rds_inspector.py` invokes
`redsea_bootstrap.py`. The helper checks whether redsea is already installed,
then compiles the pinned official `windytan/redsea` v1.3.1 from source into `/tmp`
if necessary. Later uploads reuse the compiled binary for that server instance.
The first such upload may take substantially longer while the binary builds.
If the build fails (no network, missing apt packages, constrained RAM), the
application remains functional and reports why RDS decoding is unavailable.
For ordinary music files or stored metadata, no build is triggered.
Set `AUDIOCHEQ_REDSEA_AUTOBUILD=0` to disable optional compilation.

To deploy, replace `packages.txt` and `rds_inspector.py` in GitHub and add
`redsea_bootstrap.py`. Streamlit Community Cloud reinstalls apt dependencies
when `packages.txt` changes. No changes to requirements.txt or app.py needed.

**Important:** Decoder installation does not recreate RDS data absent from
the source. RDS decoding requires a genuine FM multiplex signal, not normal
44.1/48 kHz music audio (even lossless FLAC). First-run compilation and on-air
RDS extraction have not been tested on the live Streamlit instance.
