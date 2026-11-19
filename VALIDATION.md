# AudioCheck v1.5 — Validation notes

## Checks completed

- **105 automated tests passed** on Python 3.13, covering the baseline analyzers and new spectrogram image creation, frequency resolution, stereo-channel choice, high-frequency availability, PNG embedding, mobile-friendly result-card markup, and successful clearing of uploaded file selections.
- **Synthetic 60 Hz + 120 Hz hum**: graph contains a visible horizontal line at both frequencies; measured STFT levels exceed the respective 50/100 Hz comparison regions.
- **Synthetic 15,734.26 Hz television-frequency tone**: chart shows a bright horizontal line and narrow spectral-profile peak.
- **Synthetic 10 kHz notch**: graph shows a dark horizontal band and corresponding profile trough. Test confirmed the feature is a *dip*, not a 10 kHz tone.
- **Stereo anti-phase hum**: renderer chooses a channel rather than mixing to mono and cancelling the hum.
- **Actual attached EKT sample (17 seconds)**: the previously detected ~15,734 Hz TV scan signature appears as a clear bright line on the generated TV spectrogram. Its power result remains *tentative*.
- **Actual attached historical Hysterics Rag MP3**: produced power, TV, and 10 kHz plots without a crash. The core classifier still reports record-like source evidence; no TV or NDR finding was added based solely on display graphs.
- **Visual QA:** static browser previews were checked at desktop and 430-pixel mobile widths. Both render the image previews in the correct result cards. This is **not** an end-to-end test on the live Streamlit Cloud host.

## Important limits

- A *horizontal line on a spectrogram* is not sufficient to prove 50/60 Hz electrical interference; music can have sustained notes in the same band. Existing classifier logic still determines the verdict from persistence and harmonics.
- A dashed guide line is drawn even when the frequency is absent. It is **not** the detected signal.
- Band colours are scaled relative to the surrounding selected frequency band; visually bright pixels are not automatically meaningful.
- The graph shows a bounded excerpt with the best available clue, **not the entire file**. Other portions can differ.
- Streamlit must install Matplotlib from the updated requirements; uploads on actual Android browsers and the YouTube 403 problem are outside this change.
- No recorded audio is included in the distributable ZIP. Only source files and tests are packaged.
