# AudioCheck v0.3 - Experimental Audio Origin Analyzer

A Streamlit web application for recordings up to **5 minutes (300 seconds)** and **100 MB**. Accepts MP3, WAV, FLAC, OGG and M4A. The software automatically samples up to four independent portions of the recording (up to ~160 seconds total); you do not need to trim the file yourself.

## Updating an existing deployment

1. Download and unzip the replacement project.
2. Upload/replace `app.py`, `analyzer.py`, `requirements.txt`, `packages.txt`, and `README.md` in the **root** of your GitHub repository named `audiocheck`.
3. Commit to the `main` branch. Streamlit Community Cloud should automatically redeploy after the commit.
4. Python 3.12 is a good choice, but this release no longer depends on pydub/audioop and can run on other modern supported Python versions.

The `packages.txt` manifest installs FFmpeg. Streamlit 1.53+ supports a per-upload file limit, set to 100 MB directly in `app.py`; no `.streamlit` folder is needed.

## Main outputs

- Likely source: vinyl evidence, FM radio evidence, or unclear.
- Likely vinyl speed: 33.333, 45, 78 RPM or unclear.
- Likely power origin: 50 Hz regions or 60 Hz regions, or unclear.
- Likely broadcast signals: 19 kHz FM stereo pilot, 15,625 Hz or 15,734 Hz TV line interference, multiple signals, or unclear.
- Likely playback speed: unclear without a trustworthy speed reference.
- Likely recording medium: analog transfer evidence if vinyl signature is detected, otherwise unclear.
- Likely audio generation: unclear unless there is more than one copy or reliable external reference.
- Stereo format: mono, dual mono / near-mono, stereo, or unclear.

Optional beta diagnostics show input codec, sample rate, near-full-scale samples, approximate upper spectral energy, short near-silent interruptions and (when a strong pilot signal is present) pilot frequency variation. These are **not** cassette, wow/flutter or copying-generation classifiers.

## Important limitations and false-positive precautions

- **Vinyl**: Unlike TurntableRPMAnalysis, which operates on a known locked runout groove, music has drum hits and other similar impulses. AudioCheck seeks narrow impulses with a strong local contrast, then requires consistent repeated events, multiple adjacent rotations, low timing error and no competing RPM. Even then results are only **Possible**. Vinyl transferred onto cassette can retain these clicks.
- **Power**: Checks multiple narrowband harmonics near 50/60 Hz across independent sampled sections (or three strong harmonics in one section). It does **not** calculate an independently authenticated electrical grid trace or establish a country. Musical bass tones can mimic hum.
- **FM/TV**: Checks persistent narrowband interference at 19 kHz, 15,625 Hz and ~15,734 Hz, including the two halves of each analyzed section. A 19 kHz pilot may be filtered out. Television line-frequency sounds can enter through equipment and do not prove broadcast provenance.
- **Tape/cassette**: Hiss, high-frequency loss and dropouts are shared with other recording chains. We deliberately do not label a recording cassette without validated, distinctive tape evidence.
- **Playback speed**: Cannot determine absolute correctness without a trusted reference signal or known reference recording. The presence of electrical hum at its nominal frequency is not sufficient to prove original-speed playback.
- **Recording generation**: Cannot count copying generations from a short compressed mix. The software deliberately returns Unclear.
- **Sampling**: Only selected portions of the recording are checked. A sound present exclusively outside these windows may be missed.
- **Certainty**: The color labels are engineering evidence levels, **not calibrated probabilities**. Real-world sensitivity and false-positive rates remain unmeasured.

## Method references (reviewed, not copied)

- TurntableRPMAnalysis: https://github.com/smcclem/TurntableRPMAnalysis
- NeedledroppersDeclick: https://github.com/keithhanlon/NeedledroppersDeclick
- ENF-Extractor: https://github.com/BitEU/ENF-Extractor
- AudioJS denoise click analysis: https://github.com/audiojs/denoise

## Test suite

`python -m unittest discover -s tests -v`

The included synthetic tests cover known noise, musical beat patterns, intentional groove clicks, mains harmonics, broadcast pilot tones, negative controls and the duration limits. They are not substitutes for a large labeled corpus of authentic disc, cassette and FM transfers.

## Upload reliability update

The upload page shows an explicit **File received** confirmation and no longer automatically embeds the entire recording as a browser audio player. A **Clear selection / try another file** button resets the uploader without restarting the whole site. Analyze is only offered once the file appears successfully in Streamlit. Some Android file-picker failures occur *before* the browser uploads anything; server-side code cannot fully repair those, so try another browser/file picker or refreshing the tab if the selected file never appears. The 5-minute and 100 MB limits are unchanged.
