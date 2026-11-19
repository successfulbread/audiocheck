# AudioCheck v1.4 — Source and Power Best Guesses

Keep deploying on Streamlit Community Cloud with `app.py` as the main file.

## Changes

- **Likely origin** now ranks five possibilities: vinyl/record, cassette/tape, FM radio, AM radio, and digital source. The existing frequency-range, surface-crackle, click-periodicity, FM pilot and dropout checks contribute to a single best-supported source. AM is *possible* only when sufficiently bandwidth-limited audio is also mono and the restriction is not readily explained by sample rate or low-bitrate encoding.
- **Power region** makes a tentative 50 Hz or 60 Hz guess when the detected narrow lines favour one system. With no convincing signal, or competing equally weak signals, it displays **Uncertain**. An electrical hum cannot establish the studio's country.
- **Why?** provides short reasoning about the clues, including why power is uncertain.
- Existing light interface, input choices, five-minute maximum, digital-file dating, RPM, NDR notch and broadcast checks remain intact.

## Deploy

Unzip and replace `app.py` and `analyzer.py` in the root of your existing `audiocheck` GitHub repo; commit to `main`. No change to Streamlit settings or hosting is necessary. The ZIP contains unchanged supporting files for a clean full replacement.

## Important limitations

Source ranking is heuristic: percentages are rough clue shares, not probabilities. Cassette and AM have no unique signature in an ordinary compressed song, and a record can be copied to tape, rebroadcast and digitally encoded. Power-region guesses refer to electrical interference that could have entered anywhere in this chain.
