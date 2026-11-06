# AudioCheck v1.0 - Colourful Clues

AudioCheck is an experimental Streamlit app for clues about old recordings.
Upload an MP3/WAV/FLAC/OGG/M4A file (up to 5 minutes), or try a YouTube URL if retrieval is permitted.

## What's new

- Bright light-theme results in colourful cards, sorted from clearer clues to weaker guesses.
- Every check remains visible; unknown/not-detected checks are grey at the bottom.
- Short, beginner-friendly **Why?** explanations contain the key evidence.
- Strong disc crackle produces a more confident "Likely Vinyl / Record" result.
- Moderately relaxed repeating-click detection gives more useful tentative RPM guesses.
- Prominent NTSC/PAL/SECAM, power hum and NDR 10 kHz clues.
- The uploaded file automatically clears after a **successful** analysis. The report stays on screen.
- Original YouTube beta and five-minute limit are retained.

## Update existing Streamlit Cloud app

1. Download and unzip the project.
2. Open the `audiocheck` repository on GitHub.
3. Replace `app.py` and `analyzer.py` at the top of the repository. These are the only required changes when upgrading from v0.9.1.
4. Optionally update `.streamlit/config.toml`, `README.md` and `VALIDATION.md`.
5. Commit to the `main` branch. Streamlit Cloud should redeploy automatically. Keep the app's entrypoint as `app.py`.

For a clean installation, upload `app.py`, `analyzer.py`, `youtube_source.py`, `requirements.txt`, `packages.txt`, and `.streamlit/config.toml`, preserving the folder path.

## Result meanings

- Clear clue (green): repeated or well-corroborated measured evidence.
- Good clue (blue): supportive evidence, but other interpretations are possible.
- Best guess (orange): a weaker hint that could be coincidental.
- No clue (grey): nothing detected or insufficient information.

The terms **Likely** and **Best guess** are informal. They are not calibrated probabilities. A record played from cassette or radio may carry clues from multiple stages. Power and TV interference can likewise enter on later copies.

## Requirements and testing

Python is installed automatically by Streamlit Cloud. FFmpeg is installed through `packages.txt`.
Run `python -m pytest -q` to run the optional automated tests, if pytest and test libraries are installed locally.
See `VALIDATION.md` for the measured test results and limitations.
