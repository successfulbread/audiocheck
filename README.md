# AudioCheQ v1.8 — Clear File Upload

Five-minute Streamlit audio-forensics app featuring vinyl/tape/radio/digital clues, 50/60 Hz and TV/FM spectrograms, NDR 10 kHz notch detection, and digital-file metadata hints.

## What's new

- **Step 1: Choose an audio file** using Streamlit's native file picker. No embedded upload form or custom JavaScript uploader.
- **File received** appears with the name and size immediately after the app gets the file.
- **Step 2: ANALYZE SELECTED AUDIO** is a separate prominent button, enabled only after a file arrives.
- Brighter high-contrast button text: yellow file selection, turquoise Analyze and lavender Archive.org submit.
- After successful analysis, the selected file clears automatically but the result cards stay.
- Archive.org direct-file input, existing results, audio detection and dark background stay unchanged.

## Update your existing site

Keep your existing Streamlit deployment (`audiocheck`, main file `app.py`). In GitHub, replace **only `app.py`** to apply the upload and contrast improvements; other files in this ZIP are compatible copies for a complete update. Commit to the `main` branch. No new host required.

## Notes

The normal Streamlit file picker still sends the file to Streamlit Cloud before analysis; its separate Analyze button controls **processing**, not the network transfer itself. If Android's file picker or Streamlit transport drops a file, a button cannot remedy that underlying failure. Check for **File received** before pressing Analyze. For privacy, only the derived analysis report stays in the session after the file is cleared.

See `VALIDATION.md` for tests and limits.
