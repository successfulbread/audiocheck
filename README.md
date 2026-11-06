# AudioCheck (Audio Origin Analyzer) (experimental prototype)

Upload a 5–120 second MP3, WAV, or FLAC recording. The app estimates whether detectable periodic vinyl clicks, electrical hum harmonics (50/60 Hz), or FM/TV tones are present. It reports inconclusive findings as **Unclear**, rather than inventing certainty. Stereo is measured directly from the uploaded channels.

## Deploy on Streamlit Community Cloud

1. Create a GitHub repository, e.g. `audiocheck`.
2. Upload `app.py`, `analyzer.py`, `requirements.txt`, `packages.txt` to its top level (not a nested folder).
3. At https://share.streamlit.io/ create an app from your GitHub repository, branch `main`, with entrypoint `app.py`.
4. Select Python 3.11 or 3.12 if prompted and deploy.

Dependencies are automatically installed; `packages.txt` installs FFmpeg for MP3 decoding. GitHub updates redeploy the app.

## Important limits

This is a demonstration, **not a validated forensic classifier**. Vinyl RPM detection requires a recurring defect and can be confused by musical transients. ENF detection checks narrowband hum harmonics rather than a genuine time-varying electrical-network fingerprint. FM/TV detection looks for isolated tones which may have another cause. The app deliberately returns Unclear for tape identification, original playback speed, analog/digital provenance, and copy generation until defensible algorithms and labelled validation recordings exist. Confidence colours are heuristic, not calibrated probabilities.

For a rigorous next step, test against known original vinyl/tape/radio sources, digitally sourced recordings, and many compressed transfers, then evaluate sensitivity and false positives.

## Review of existing methods

- `TurntableRPMAnalysis` measures clicks in a locked runout groove; that is a controlled signal. Music is a much harder problem. AudioCheck uses per-channel click candidates and requires a repeated sequence, rather than directly applying its peak-picking routine.
- `NeedledroppersDeclick` highlights percussion-induced false positives. AudioCheck's click detector is intentionally conservative but is not yet validated on a real dataset.
- `ENF-Extractor` uses harmonic combs and explicit detection gates. AudioCheck's electrical test is simpler; it must not be interpreted as a verified grid-frequency trace or recording location.
- FM/TV findings require genuine, persistent interference. A single spectral line may have a different cause.

This remains an exploratory prototype. The color 'Possible' is an engineering indicator, **not** a calibrated probability. No automatic vinyl, radio, cassette, or geographic conclusion should be treated as forensic proof.
