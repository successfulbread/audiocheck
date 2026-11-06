# AudioCheck v0.7 — Streamlit: submit button + YouTube URL (beta)

This release **stays on Streamlit**. It is not the separate Render/FastAPI edition.

## Install/update on your existing site

1. Extract this ZIP; open your GitHub repository `audiocheck`.
2. Upload these **five files** to the repository root, replacing old versions:
   `app.py`, `analyzer.py`, `youtube_source.py`, `requirements.txt`, `packages.txt`.
   `README.md` may also be replaced. GitHub should show these files at the same level.
3. Commit changes on `main`; keep Streamlit's entrypoint as **`app.py`**.
4. Streamlit Community Cloud should redeploy and retain your existing URL.
5. Open the app directly in Chrome, select a file, and press **Analyze recording**.
   Or choose the YouTube tab, enter a permitted URL and press its submit button.

Older files like `alt_uploader.py`, `main.py`, `Dockerfile`, and `render.yaml` may remain
in GitHub but are **not used by the Streamlit app**. Do **not** upload the ZIP itself.

## Upload method

The file uploader is now inside `st.form()` with a dedicated submit button.
Changing/selecting a file does not automatically trigger the Python analysis.
This is Streamlit's supported upload flow and avoids the previous custom upload
component, but **cannot repair** failures inside Android's file picker or an
unstable mobile/Streamlit connection. Streamlit must still receive the file.

- Formats: MP3, WAV, FLAC, OGG, M4A; max 100 MB / 5 minutes.
- Analyses up to four distributed nonoverlapping 25-second portions for speed.
- Results include a coloured signal summary and expandable explanations.

## YouTube URLs (experimental)

The app accepts a single standard YouTube video URL (watch/shorts/live page or
youtu.be link) and downloads its audio using yt-dlp **only when permitted**.
It rejects playlists, videos longer than five minutes, and arbitrary websites.
It does not access private videos, cookies, logged-in sessions, DRM, or paywalls.

**Important:** YouTube's Terms of Service restrict downloading without proper
authorization. The feature should only be used when downloading is expressly
permitted by YouTube and applicable rightsholders. Merely being publicly visible
or labelled Creative Commons does not automatically override YouTube's terms.

YouTube frequently changes its access controls. yt-dlp now recommends an
external JavaScript runtime (Deno/Node 22+) and the `yt-dlp-ejs` component.
The Python dependency `yt-dlp[default]` includes the solver component, but
Streamlit Community Cloud may not have a supported JavaScript runtime.
YouTube may also reject requests from cloud servers. The YouTube tab should
therefore be treated as **best-effort beta**; **file uploads remain preferred**.
Failure to fetch YouTube audio is not an audio-analysis result.

## Technical notes

Uses the enhanced v0.6 analyzer from AudioCheck: up to 5 minutes, 50/60 Hz
multi-harmonic detection, 33 1/3 / 45 / 78 RPM click periodicity, FM/TV tone
screening, stereo analysis, dropout hints and measured bandwidth.
YouTube audio often uses lossy compression which may remove high frequencies,
FM pilot remnants, electrical hum and clicks, reducing sensitivity.

The server downloads/decodes temporary audio and deletes it after analysis.
To validate detection with reference recordings, use `tests/test_analyzer.py`
and the v0.6 public-reference test workflow if already installed.

## Troubleshooting

- `No audio file reached AudioCheck`: select again; try Chrome or a computer.
- YouTube inaccessible: paste a direct file upload instead; YouTube may refuse
  automated server-side audio retrieval.
- Install failures: check Streamlit's **Manage app → Logs**.
- Python 3.12 is recommended on Streamlit Cloud; `pydub` is not used.
