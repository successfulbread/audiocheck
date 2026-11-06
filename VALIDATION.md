# AudioCheck v0.8 — validation record

## Actual uploaded recording

- **Reference:** `01 - Hysterics Rag (A Trombone Fit) - Tony Parenti's Ragtimers.mp3`
- **Source:** User-provided historical record MP3; original physical medium
  not independently documented by these tests.
- **Duration:** 168.3 seconds; MP3 128 kbps, 48 kHz stereo.
- **Sampling:** Three distributed 25-second windows (75 seconds analyzed).

| Measurement | v0.7 | v0.8 |
|---|---|---|
| Likely audio source | Disc-like crackle (weak) | **Disc transfer likely — Possible** |
| Disc surface noise | Not independently reported | **Disc surface noise likely — Possible** |
| Rotation speed | None detected | None detected (no reliable repeating defect) |
| Power-system pattern | 50 and 60 Hz candidates | Ambiguous, not a claimed regional origin |

**Concrete evidence in the reference excerpt:** In the qualifying excerpts,
there were **33 irregular high-pass click candidates**, a strongly impulsive
high-frequency noise texture in **105 half-second frames**, and **7 quieter
half-second frames** that still contained highly impulsive noise. These are
measurement-specific, not a calibrated statistical probability. Some clicks
may be missed or duplicated by MP3 encoding and music transients.

The improvement is specifically that disc evidence does **not** now require
repeating clicks once every 0.769/1.333/1.800 seconds. The application still
refuses to guess the RPM without a rotation-period signature.

## Controlled signal checks

**40 automated tests passed**, including:

- Synthetic 33 1/3, 45 and 78 RPM rotating-click sequences.
- Clean synthesized music, regular percussion, Gaussian hiss (disc negatives).
- Synthetic irregular crackle with quiet run-in and run-out (disc positive).
- 50 Hz and 60 Hz hum + harmonics mixed into synthesized music, including
  real MP3 encoding/decoding and opposite-channel hum.
- Broadcast-frequency tests for 19 kHz FM pilot and 15.625/15.734 kHz TV lines.
- Five-minute MP3 length and overlength rejection.
- YouTube URL validation, duration rejection, simulated successes/failures,
  Deno-runtime selection and understandable error messages.

**Additional diagnostic experiment using real historical music:** Adding
controlled 50 Hz or 60 Hz hum plus harmonics to 25 seconds of the supplied
MP3 produced the correct frequency-family interpretation. With smaller
synthetic additions the result was **Tentative**, and with stronger additions
it was **Possible**. This tests interference injected into actual music, but
**does not establish which mains frequency, if any, is present in the
unmodified historical recording**.

## What remains unverified

1. No real YouTube video was downloaded or processed from Streamlit Cloud;
   server-side access depends on YouTube and the hosting environment.
2. Internet Archive downloads were unreachable here. The optional manual
   GitHub Actions benchmark has not yet run.
3. A single real historical recording and synthetic tests cannot establish
   a general false-positive/false-negative rate. Further known-source
   recordings are needed, especially percussion-heavy music and cassette
   copies made from crackling records.
4. Surface crackle is consistent with physical discs but is not uniquely
   attributable to them; static, damaged tape and deliberately added noise
   can mimic the fingerprint.
5. The recording method does not directly identify the studio, country,
   track title or artist. 50/60 Hz hum can originate during subsequent transfer.
