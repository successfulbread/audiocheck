# AudioCheck v0.3 - Validation notes

## What was actually tested

- 15 unit tests passed (synthetic controls, deterministic seeds, standard unittest library).
- 33 1/3, 45 and 78 RPM *simulated* repeating impulses were detected.
- Random noise without rotation did not produce a vinyl speed.
- A conventional 90 BPM decaying drum-like signal did not produce a vinyl speed.
- Synthetic 50 and 60 Hz signals with harmonics were distinguished.
- A single isolated 60 Hz sinusoid did not qualify as an electrical harmonic family.
- White noise and music-like sine controls did not qualify as mains or broadcasts.
- Synthetic 19 kHz pilot and 15,625 Hz TV interference were detected.
- Lower input sample rates correctly disabled impossible 19 kHz pilot assessment.
- Stereo/mono file processing and short clip analysis completed successfully.
- A **five-minute synthetic MP3** was accepted, with 160 seconds of audio sampled from four distinct locations; an over-length file was rejected.
- A **65-second 45 RPM synthetic source** was detected in both WAV and lossy 192 kbps MP3 form.
- The beta dropout detector and pilot stability estimator passed their limited synthetic checks.

## Important adversarial result

Very sharp *repeating broadband drum bursts* timed exactly at 45 RPM can also trigger the vinyl detector. This is a fundamental identification ambiguity: a transient percussive sound can be nearly indistinguishable from a very short vinyl defect after mixing and MP3 compression.

**Consequences**: AudioCheck currently limits vinyl findings to **Possible** and explains that percussion may imitate vinyl. No reliable quantitative false-positive rate has been measured. If a user needs forensic certainty, do not rely on an automated 45 RPM verdict alone.

Likewise, an electronic instrument that creates stable tones exactly at 50, 100 and 150 Hz can imitate a mains-harmonic comb. The app cannot prove geographic recording origin or original medium from these features alone.

## Relevant existing projects / methodology comparison

- https://github.com/smcclem/TurntableRPMAnalysis - proven intervals in locked runout grooves, unlike ordinary music.
- https://github.com/keithhanlon/NeedledroppersDeclick - documents major percussion/impulse detection ambiguity.
- https://github.com/BitEU/ENF-Extractor - harmonic presence gate, tracking and caution about speed inference.
- https://github.com/audiojs/denoise - local prediction-error approach to transient click detection.

Code is independently implemented; these projects were methodological references.

## Known-source recordings suitable for **future** real-world validation

These were identified from openly licensed/public-domain sources, but their actual audio files were **not fetched and processed** in this testing environment. They are not part of the test results above.

1. 1916 recording of **Hawaiian Portuguese Tango**, identified on Wikimedia Commons as digitized from a 78 RPM Victor record. https://commons.wikimedia.org/wiki/File:Frank_Ferera,_Helen_Louise_-_Hawaiian_Portuguese_Tango.ogg
2. Sousa's Band, **In The Good Old Summertime** (1905), an openly available historical recording. https://commons.wikimedia.org/wiki/File:In_The_Good_Old_Summertime.ogg
3. **Ambient music test, Yamaha CK61** (2024), a modern CC0-licensed recording useful as a reference for non-vinyl musical transients. https://commons.wikimedia.org/wiki/File:Ambient_music_test,_Yamaha_CK61.flac

A 78 RPM original will not necessarily show 78 RPM recurring defects: an undamaged or restored transfer should correctly return `Unclear`. Real testing must include dozens of known cassette transfers, FM-airchecks, vinyl captures with/without groove defects, modern digital masters and lossy MP3 derivatives before any accuracy percentages are claimed.

## Deployment verification not performed here

Python syntax compilation and local FFmpeg decoding were tested. Streamlit's actual browser interface and Streamlit Community Cloud deployment must still be exercised on the user's live application. The package uses Streamlit 1.53+ for the per-widget upload cap; the Python dependencies are installed on the Cloud host.
