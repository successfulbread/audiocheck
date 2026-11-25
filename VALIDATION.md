# AudioCheQ v2.0 — Validation

## Automated checks

From the repository root:

```bash
PYTHONPATH=. pytest -q
```

Tests include existing app/upload/Archive.org/FFT/TV/NDR/file-age regressions and v2.0 synthetic ground-truth simulations:

- Opposite-polarity channels, dual-mono, 37-sample time-shifted channel, single-channel exclusion.
- An exactly shifted synthetic 18,940 Hz FM pilot: independent recognition, measured deviation and *conditional* speed-ratio calculation.
- White-noise rejection and insufficient input sample-rate exclusion.
- Periodic 0.75 Hz wobble on a controlled 19 kHz sine versus a stationary clean reference.
- A432-toned notes: approximate -32-cent musical tuning, explicitly not a validated speed estimate.
- Rejection of conflicting reference families rather than averaging them.
- Actual FFT-derived frequency peak profiles with reference labels on the axis, no fabricated signal guide drawn across peaks.
- Complete WAV analysis with all new result cards and valid PNG evidence, no raw decoded audio in metadata.
- HTML escaping, metric rendering and desktop/mobile contrast.

These are functional tests against carefully controlled inputs. They do NOT establish empirical false-positive rates or accuracy on a representative collection of historical cassette/vinyl/radio transfers.

## Example recordings used

- `Everyone_Knows_That.mp3.mpeg` (provided reference): detectable NTSC-style TV scanning line; no FM pilot met the upgraded thresholds. The TV line can only provide a conditional speed reference if it predates any altered playback.
- `01 - Hysterics Rag (A Trombone Fit) - Tony Parenti's Ragtimers.mp3`: prior record-transfer clues continue to register, with no FM pilot detection. A lack of stable high-frequency reference means wow/flutter can be genuinely unmeasurable.

Neither reference recording is included in the distributed ZIP.

## Visual review

Rendered desktop (1,100 px) and mobile (430 px) static HTML previews based on actual output. Confirmed no horizontal overflow. These are **static presentation QA**, not a live Streamlit Cloud browser session. `preview_*.png` may be provided separately; they are not part of the deployment package.

## Limitations requiring field validation

Real-world evaluation is still needed for faint FM pilot residues, badly compressed recordings, naturally detuned older performances, tapes with substantial azimuth error, strong singer vibrato, and stylized artificial stereo. All new detectors should be treated as investigatory clues, not conclusive provenance claims.
