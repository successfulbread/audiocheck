# AudioCheck v1.2 - Validation

- Regression suite: 79 local tests passed (run `PYTHONPATH=. pytest -q`).
- Historical user-provided 'Hysterics Rag' MP3: **Likely Vinyl / Record** (High; about 81% relative clue score) based on irregular record crackle, quieter-section noise, and a weaker possible 45 RPM click pattern. The MP3's LAME 3.99.5 tag supports **encoded 2012 or later**.
- User-provided EKT MPEG audio: strong **NTSC-type TV scan-line interference** is retained, and digital-file metadata now shows **encoded 2015 or later** from `Lavc57.10`. The original medium is **not established** by either the scan tone or MP3 codec.
- Source-combination tests cover clear disc evidence, FM 19 kHz pilot, tape-like short dropouts, wide but clean audio, TV interference without a source conclusion, and no-evidence controls.
- Display tests cover escaping untrusted text, sorted/grey cards, combined crackle/dropout clues, age + codec subtitling, and evidence details in the Why? dropdown.
- The app still clears the selected file after successful analysis without discarding the report.

**Limitations:** Source scores are rough heuristic weights, not measured probabilities. Even a convincing vinyl fingerprint may have been copied to cassette, radio, or MP3. The file creation date cannot be established from bitrate alone. Release-year tags must not be mistaken for encode dates. The live website and all Android browsers have not been individually tested with this build.

Encoder-date reference points:
- LAME 3.99.5 was released February 28, 2012: https://github.com/enzo1982/lame/releases
- FFmpeg `libavcodec` major version 57 was introduced in 2015: https://fuchsia.googlesource.com/third_party/ffmpeg/+/n3.3.7/doc/APIchanges
