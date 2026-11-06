# AudioCheck v0.9 — Light theme and simpler findings

**Repository:** `audiocheck` · **Platform:** Streamlit Community Cloud · **Entrypoint:** `app.py`

AudioCheck screens uploaded recordings (4 seconds to 5 minutes, up to 100 MB) for possible recording-source clues. It provides **qualitative best guesses, not scientifically calibrated probabilities**.

## What's new

- Accessible light theme, updated results layout, prominent source guess, short explanations. Strongest measured clues appear first; empty / inconclusive checks are collapsed.
- One standard Streamlit file uploader with a separate **Analyze recording** button. YouTube URL form is still available as a beta; YouTube may block cloud-server retrieval.
- Direct uploads of `.mp3`, `.mpeg`, `.mpga`, `.wav`, `.flac`, `.ogg` and `.m4a` are supported.
- More permissive *tentative* 33⅓ / 45 / 78 RPM detection for shorter repeating click trains. Never infer RPM from random crackle alone.
- More readable best-supported 50 / 60 Hz *electrical-system* clues, including a tentative guess if one candidate dominates (still no claim about the country where a song was recorded).
- NTSC / PAL / FM high-frequency line screening accepts narrow peaks shifted slightly from their nominal frequency but requires evidence of persistence and narrowband prominence.
- **NDR-style 10 kHz notch** detector (new). It looks for a *dip*, not a tone, within about 9.65–10.38 kHz, with persistence across overlapping segments and checks against unrelated spectral dips. This is an experimental radio-chain clue, not a definitive NDR attribution.

## Update the existing Streamlit website

1. Extract the ZIP.
2. Open the GitHub repository named `audiocheck`.
3. Replace the files at the **repository root**: `app.py`, `analyzer.py`, `youtube_source.py`, `requirements.txt`, `packages.txt`.
4. **Important for the light theme:** replace `.streamlit/config.toml` in the `.streamlit` folder. If GitHub's browser upload doesn't preserve hidden folders, open `.streamlit/config.toml` directly on GitHub, click Edit (pencil), and replace its content with the version in this ZIP. It specifies `base = "light"`.
5. Commit to the `main` branch. Your existing Streamlit Community Cloud app should update automatically. The main file remains `app.py`.
6. If the original black page remains, refresh after deployment or clear the browser cache, and verify `.streamlit/config.toml` contains `base = "light"`.

No Render account or redeployment setup is needed.

## How it works

- FFmpeg probes files and decodes up to four 25-second windows distributed across each recording.
- Grooved-disc *surface noise* and revolution-aligned *click timings* are separate forms of evidence. Recurring clicks can suggest RPM; irregular surface crackle alone cannot.
- Electrical hum screening looks at persistence of 50 / 60 Hz frequency families, including harmonics. A single narrow line may be music instead.
- NTSC (approximately 15,734.26 Hz), PAL/SECAM (15,625 Hz), FM stereo pilot (19,000 Hz) are examined for narrowband persistent signals.
- The experimental NDR notch check looks for a narrow, consistently depressed frequency band, accounting for modest tape-speed offsets.
- Cassette/tape suggestions remain preliminary; a dropout is not uniquely a cassette defect.

## Run tests

If you have Python, FFmpeg, and the dependencies from `requirements.txt` installed:

```sh
PYTHONPATH=. python -m pytest -q tests
```

All 49 local tests passed in this revision. These are engineering regression tests, not proof of general accuracy. See `VALIDATION.md` for the EKT and historical-record checks.

## Limitations

- A TV line or mains signal may have entered through later copying, playback, or digitization; it cannot identify the original studio location.
- Strong musical notes may imitate 50 / 60 Hz interference; even an electronic harmonic family can be ambiguous.
- A TV-related frequency does not prove the song was broadcast on television; it might come from a nearby CRT monitor.
- The 10 kHz dip is **not unique to NDR**; it was a useful clue in the TMS case, not a station ID encoded in every recording.
- A record may have no repeating scratch, and a cassette can inherit scratches from vinyl. Shellac 78s are not made of vinyl; the app uses `record (vinyl/shellac)` rather than implying all historical records are vinyl.
- The entire Streamlit interface and actual live YouTube retrieval were not exercised in this offline build environment; the Python analyzer and test suite were.

No uploaded audio is intentionally stored in GitHub. Standard Streamlit file uploads are processed in memory, with temporary-file handling during decoding/YouTube extraction.
