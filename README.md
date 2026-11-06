# AudioCheck v0.8 — dark Streamlit edition

**Keep your existing Streamlit app and GitHub repository `audiocheck`.**

## Install in GitHub

1. Download and extract the ZIP file. **Do not upload the ZIP itself** to GitHub.
2. Open your existing GitHub repository, `audiocheck`.
3. **Add file > Upload files**, replacing these root-level files:
   `app.py`, `analyzer.py`, `youtube_source.py`, `requirements.txt`, `packages.txt`.
   You may also upload this `README.md` and `VALIDATION.md`.
4. To force the **dark theme**, preserve the file `.streamlit/config.toml`.
   If GitHub's file chooser doesn't upload hidden folders, choose **Add file > Create new file**;
   enter the filename `.streamlit/config.toml`; paste the contents below; commit.
5. Click **Commit changes** on the `main` branch.
6. Streamlit will normally redeploy automatically. Keep entrypoint `app.py`.

The dark theme configuration is:

```toml
[theme]
base = "dark"
primaryColor = "#62E8CB"
backgroundColor = "#0B1020"
secondaryBackgroundColor = "#171F33"
textColor = "#F2F6FF"
font = "sans serif"
```

The live URL remains https://audiocheckq.streamlit.app/ . If the new app fails to load,
check **Manage app > Logs**. Python 3.12 is a safe runtime selection.

## Changes

- Stronger distinction between **disc surface crackle** and **rotation speed**.
  Older shellac 78 RPM discs may crackle abundantly without any repeating
  groove scratch. They can now produce a likely disc-source result without
  an unsupported RPM estimate.
- More careful checks for irregular, impulsive, high-frequency noise that
  persists in quieter parts of a song. Regular drum hits and white-noise hiss
  are screened separately, but are not eliminated as potential false positives.
- Positive findings appear first in a dark, colourful report, with a short
  **What the evidence suggests** interpretation. Missing and inconclusive
  measurements are collapsed under **Other checks**.
- Improved 50/60 Hz interpretation when one family has a persistent strong
  tone plus a weaker harmonic, but rival family only has weak hints. We never
  equate a mains frequency with the country of original recording.
- YouTube beta installs a supported Deno JavaScript runtime with the `deno`
  Python wheel, alongside the current `yt-dlp[default]` solver components.
  More descriptive errors distinguish missing runtime, YouTube bot checks and
  HTTP 403 blocking. **It remains best-effort**; YouTube often blocks hosted
  downloaders regardless of correct dependencies.
- Five-minute maximum remains. Analyzes up to four distributed 25-second
  segments for speed, including the start and end of a song.

## Real-world reference check

The user-provided historical recording `Hysterics Rag (A Trombone Fit)`
(2 minutes 48 seconds, MP3) was measured locally, **but is not included** in
this repository or the distributed ZIP.

Before this revision, v0.7 reported `Disc-like crackle (weak)` and no matching
RPM. v0.8 reports **`Disc transfer likely`** and **`Disc surface noise likely`**.
The analyzer observed irregular impulsive clicks in multiple excerpts and
impulsive noise during quieter passages. See `VALIDATION.md` for details.

This is one historical reference example, **not a validated diagnostic
accuracy**. Test with known-clean music, true cassette copies, radio recordings,
well-transferred 78s, LPs and 45s before trusting broad source classifications.

## Optional: benchmark public historical recordings

The directory `scripts/` contains an optional benchmark that downloads a small
sample of Internet Archive MP3s **temporarily** and prints a JSON report.
It accepts a single Archive item or collection identifier, e.g. `78rpm_donald_ross`.
Nothing is redistributed and downloaded audio is removed at the end.

The `.github/workflows/archive_benchmark.yml` GitHub Actions workflow lets you
run the benchmark on GitHub's servers:

1. Upload the optional `scripts/benchmark_archive.py` and `.github/workflows/archive_benchmark.yml`, preserving the paths.
2. On GitHub go to **Actions > Benchmark historical disc recordings > Run workflow**.
3. Read the console log, or download the generated `archive-audiocheck-results` artifact.

The archive.org network was not reachable in the development environment, so
this optional benchmark has **not** been run on those downloaded files here.
The provided historical MP3 was tested locally. The benchmark identifies
potential disc indicators, not a scientifically calibrated false-positive rate.

## Engineering notes

Use Python 3.12+ with FFmpeg installed. The app has three main source files.
No `pydub` dependency. Tests can run using:

```bash
python -m pip install numpy scipy pytest
python -m pytest -q
```

The analyser is evidence-oriented: a positive can indicate an earlier stage
in a recording chain, not necessarily the final source or original studio.
78 RPM records are commonly **shellac**, not vinyl. Their crackle does not
by itself determine a precise rotation speed.

YouTube downloads should only be attempted when allowed by the platform and
applicable rights. Public visibility does not itself establish permission.
Uploaded files are processed temporarily; please consider your hosting
provider's privacy terms before submitting unreleased audio.
