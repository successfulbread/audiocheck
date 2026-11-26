"""Optional, on-demand redsea installation for Streamlit Community Cloud.

Only invoked when an uploaded file looks like a raw high-rate FM multiplex
recording. A failed build never prevents ordinary audio analysis.
"""
from __future__ import annotations

from functools import lru_cache
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

REDSEA_TAG = 'v1.3.1'
REDSEA_REPO = 'https://github.com/windytan/redsea.git'
ROOT = Path(tempfile.gettempdir()) / 'audiocheq_redsea_v1_3_1'
EXE = ROOT / 'build' / 'redsea'


def _run(args: list[str], *, cwd: Path | None = None, timeout: int = 150) -> None:
    process = subprocess.run(args, cwd=str(cwd) if cwd else None,
                             capture_output=True, text=True, timeout=timeout,
                             check=False)
    if process.returncode != 0:
        detail = (process.stderr or process.stdout or 'unknown error').strip()
        raise RuntimeError(f"{args[0]} failed: {detail[-250:]}")


@lru_cache(maxsize=1)
def resolve_redsea() -> tuple[str | None, str]:
    """Return (executable, status); build on demand if no decoder is installed.

    Runs at most once per application process, and uses /tmp so no root
    privileges are required. Compilation can take time on the first MPX upload.
    """
    existing = shutil.which('redsea')
    if existing:
        return existing, 'Installed redsea found on PATH.'
    if EXE.is_file() and os.access(EXE, os.X_OK):
        return str(EXE), 'Previously built redsea found in temporary directory.'
    if os.environ.get('AUDIOCHEQ_REDSEA_AUTOBUILD', '1').strip().lower() in ('0', 'false', 'no'):
        return None, 'Automatic decoder build disabled by AUDIOCHEQ_REDSEA_AUTOBUILD.'
    missing = [name for name in ('git', 'meson', 'ninja', 'c++') if shutil.which(name) is None]
    if missing:
        return None, ('Redsea build tools missing: ' + ', '.join(missing) +
                      '. Update packages.txt and redeploy.')
    try:
        ROOT.parent.mkdir(parents=True, exist_ok=True)
        if not (ROOT / 'meson.build').is_file():
            # Remove a partially cloned directory from an interrupted attempt.
            if ROOT.exists():
                shutil.rmtree(ROOT)
            _run(['git', 'clone', '--depth', '1', '--single-branch',
                  '--branch', REDSEA_TAG, REDSEA_REPO, str(ROOT)], timeout=100)
        if not (ROOT / 'build' / 'build.ninja').is_file():
            _run(['meson', 'setup', 'build', '-Dbuild_tests=false'], cwd=ROOT, timeout=90)
        _run(['meson', 'compile', '-C', 'build', '-j', '1'], cwd=ROOT, timeout=220)
        if EXE.is_file() and os.access(EXE, os.X_OK):
            return str(EXE), f'Redsea {REDSEA_TAG} built successfully.'
        return None, 'Redsea build completed but its executable was not found.'
    except (OSError, subprocess.SubprocessError, RuntimeError) as error:
        return None, str(error)[:350]
