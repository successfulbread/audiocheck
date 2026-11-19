# AudioCheck v1.6 — Validation notes

## Performed in this workspace

- **92 automated tests passed** after removing the obsolete YouTube tests and adding six v1.6-specific checks.
- Retained synthetic 50 Hz/60 Hz harmonics, 525/625-line TV tones, 19 kHz FM, 10 kHz notch, disc clicks, metadata, no-signal, and defensive-display checks from the prior release.
- The v1.6 checks confirm: no YouTube upload or downloader dependency, dark Streamlit theme, contrasting decorative waveform header, explanations that include measured data and technical context, negative-result explanations, and the new high-contrast `inferno` chart renderer.
- **Real EKT example:** generated actual TV and power spectrograms from the attached EKT MP3, including the known peak near 15,734 Hz. The core analyzer still provides the verdict; plots do not alter its thresholds.
- **Visual browser preview** captured at desktop (1140 px) and mobile (430 px) widths. Expanded TV and power “Why?” cards successfully display the real charts, the dark background, readable pastel results, and the bright header.

## Not verified

- No end-to-end deployment or audio upload on the live Streamlit Cloud host was performed in this environment. The Streamlit package is unavailable here; browser previews are static renderings of the app's actual HTML/CSS and generated spectrograms, not a running Streamlit deployment.
- No new real-world external recording benchmark was performed for this UI-focused release. Signal detection thresholds remain those of v1.5.

## Chart methodology

- STFT on decoded audio, Hamming window, high frequency resolution; downsample to 2 kHz for low-frequency hum.
- Automatically set a **single** colour dynamic range across each complete displayed frequency/time band (30–65 dB based on percentiles), not per frequency row. This increases visibility without changing peaks or inventing lines.
- `inferno` yellow/orange = stronger audio energy, purple/black = weaker. Dashed turquoise = nominal frequency **reference**, not detection.
- NDR-style result looks for a **reduction** (a dark gap / frequency-profile trough), not a bright 10 kHz line.
- Graphs cover selected excerpts (not necessarily all five minutes), chosen based on the underlying analysis.
