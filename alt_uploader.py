"""Android-friendly alternate upload over a Streamlit V2 component channel.

Unlike st.file_uploader's HTTP upload endpoint, this uses a browser FileReader
and Streamlit's component state transport.  Best for short compressed audio.
"""
from __future__ import annotations

import base64
import binascii

import streamlit as st

ALT_MAX_BYTES = 25 * 1024 * 1024

HTML = """
<div class="ac-file-picker">
  <label for="ac-file">Choose an audio file (alternate method)</label>
  <input id="ac-file" type="file" accept=".mp3,.wav,.flac,.ogg,.m4a,audio/*" />
  <div id="ac-file-status" aria-live="polite">Select a file to begin.</div>
  <div class="ac-help">Best for MP3s under 25 MB. For larger WAV/FLAC files, use the Standard upload option.</div>
</div>
"""

CSS = """
.ac-file-picker { width: 100%; box-sizing: border-box; padding: 10px 2px; }
.ac-file-picker label { display:block; font-weight:600; margin-bottom:9px; }
.ac-file-picker input { display:block; box-sizing:border-box; width:100%; padding:10px; border:1px solid #9ca3af; border-radius:8px; background:transparent; color:inherit; }
#ac-file-status { margin-top:10px; overflow-wrap:anywhere; font-size:14px; }
.ac-help { margin-top:8px; font-size:12px; opacity:.72; }
"""

JS = """
export default function({ parentElement, setStateValue }) {
  const input = parentElement.querySelector('#ac-file');
  const status = parentElement.querySelector('#ac-file-status');
  const maxBytes = 25 * 1024 * 1024;
  let active = true;
  let selectedReader = null;
  function show(msg) { if (active) status.textContent = msg; }
  input.onchange = () => {
    const file = input.files && input.files[0];
    if (!file) { show('No file selected. Please choose again.'); return; }
    const ext = file.name.toLowerCase().split('.').pop();
    if (!['mp3','wav','flac','ogg','m4a'].includes(ext)) {
      show('Unsupported file type. Use MP3, WAV, FLAC, OGG or M4A.'); return;
    }
    if (file.size === 0) { show('The selected file is empty.'); return; }
    if (file.size > maxBytes) {
      show('This file exceeds 25 MB. Switch to Standard upload for large files.'); return;
    }
    if (selectedReader && selectedReader.readyState === 1) selectedReader.abort();
    const reader = new FileReader();
    selectedReader = reader;
    show('Reading ' + file.name + ' on your device...');
    reader.onprogress = (ev) => {
      if (ev.lengthComputable) show('Reading file: ' + Math.round(ev.loaded * 100 / ev.total) + '%');
    };
    reader.onerror = () => show('Could not read this file. Try another picker or Standard upload.');
    reader.onabort = () => show('File selection cancelled.');
    reader.onload = () => {
      if (!active || typeof reader.result !== 'string') return;
      const separator = reader.result.indexOf(',');
      if (separator < 0) { show('Failed to convert file.'); return; }
      show('File read. Sending to AudioCheck...');
      try {
        setStateValue('file', {
          upload_id: String(Date.now()) + '-' + Math.random().toString(36).slice(2),
          name: file.name,
          size: file.size,
          data_b64: reader.result.slice(separator + 1)
        });
      } catch (e) {
        show('Could not send the file to AudioCheck. Please try again or use Standard upload.');
      }
    };
    reader.readAsDataURL(file);
  };
  return () => {
    active = false;
    input.onchange = null;
    if (selectedReader && selectedReader.readyState === 1) selectedReader.abort();
  };
}
"""


def render_alternative(key: str):
    component = st.components.v2.component(
        "audiocheck_browser_file_picker", html=HTML, css=CSS, js=JS,
    )
    return component(key=key, height=176, width="stretch")


def decode_component_file(payload: dict) -> tuple[str, bytes, str]:
    """Validate metadata before decoding; never trust browser-provided data."""
    if not isinstance(payload, dict):
        raise ValueError("Unexpected alternate upload response.")
    name = payload.get("name")
    encoded = payload.get("data_b64")
    file_size = payload.get("size")
    upload_id = payload.get("upload_id")
    if not isinstance(name, str) or not name or len(name) > 255:
        raise ValueError("Invalid audio filename.")
    if not isinstance(upload_id, str) or not (1 <= len(upload_id) <= 90):
        raise ValueError("Invalid upload ID.")
    if type(file_size) is not int or not (0 < file_size <= ALT_MAX_BYTES):
        raise ValueError("Alternate uploads must be 25 MB or smaller.")
    if not isinstance(encoded, str) or len(encoded) > ((ALT_MAX_BYTES + 2) // 3) * 4 + 8:
        raise ValueError("Alternate upload is too large or invalid.")
    try:
        raw = base64.b64decode(encoded, validate=True)
    except (ValueError, binascii.Error) as exc:
        raise ValueError("Alternate upload was corrupted. Please select the file again.") from exc
    if len(raw) != file_size:
        raise ValueError("Alternate upload size mismatch; please try again.")
    return name, raw, upload_id
