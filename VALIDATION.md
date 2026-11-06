# AudioCheck v1.3 validation

- Automated test suite: **89 passed** (local).
- Real supplied **Tony Parenti's Ragtimers / Hysterics Rag** MP3: "Likely Vinyl / Record"; bandwidth clue is "Wide range (~18.2 kHz)" (may reflect surface noise); software tag "LAME 64bits version 3.99.5" => digital encoding from **2012 or later**, earliest named release **2012-02-28**.
- Real supplied **Everyone Knows That** MP3: no definitive original medium; "MP3-like cutoff (~16 kHz)" explains that the ~90 kbps MP3 encoding may account for high-frequency filtering; TV test detects NTSC-type signal; "Lavc57.10" => encoding could date from **2015 or later**.
- New date tests: LAME 3.99.5 and 3.100, FFmpeg Lavc 57-62 families, TDRC song-year rejection, TDEN encoding dates, newer-container/older-audio distinction.
- New Archive.org link tests: reject non-HTTPS/non-archive hosts and item-page URLs, simulated file transfer, redirect host validation. This does not guarantee Streamlit Cloud access to archive.org.
- Unchanged findings: frequency range, codec, pops and hum cannot by themselves prove the original recording medium, studio or original date.
- The Streamlit Cloud live interface and direct YouTube retrieval (which may return HTTP 403) remain unverified.
