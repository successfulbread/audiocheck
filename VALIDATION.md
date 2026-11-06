# AudioCheck v1.1 — Validation and limits

- Automated Python regression tests: **69 passed** (including metadata checks and audio-frequency tests).
- User-provided historical ragtime MP3: ID3 software tag names **LAME 3.99.5**; AudioCheck reports **Encoded 2012 or later**. The record itself is much older; the tag describes a digital encoding.
- User-provided EKT MPEG audio: encoder tag **Lavc57.10**, approximately 90 kbps VBR; broad-spectrum check found a **sharp high-frequency cutoff ~16 kHz**, consistent with MP3 filtering. A broadcast scan line can coexist with codec filtering.
- Synthetic test: gradual low-pass filter around 15 kHz is classified as limited/filtered bandwidth, without claiming it must be radio.
- Synthetic test: full-band noise remains wide-band. Noise at high frequencies (including record hiss/crackle) does *not* demonstrate that music was recorded digitally.
- Synthetic test: reduced original sample rate is correctly called out as a sampling-rate limit.
- Synthetic metadata tests: encoded-date tag is recognized, a song's recording-year tag is not confused with file creation, and contradictory encoding years are flagged.
- All existing vinyl, power-hum, broadcast, NDR, stereo, failure-handling, sorting and uploaded-file reset tests are retained.

**Not established:** A spectral cutoff cannot uniquely distinguish FM, cassette, or MP3; the LAME release date gives only a possible *lower bound* for encoding. Encoder and creation tags can be edited, and some programs or transfers overwrite them. Original creation dates of YouTube videos are not recoverable from their transcoded audio streams. File-system timestamps on temporary uploads are intentionally ignored.

The complete Streamlit browser interface still requires confirmation on the live deployment. Automated tests exercise the analysis and display helper logic, not real Streamlit Cloud browser sessions.
