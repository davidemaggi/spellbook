"""Launcher for transcribe.py: creates/updates a private virtual environment on
first use, then runs the transcription inside it.

Standard library only, so it works with any Python 3.8+ on PATH.

    python run.py <files or folders> [transcribe.py options]
    python run.py --setup        # only prepare the environment

Environment variables:
    TRANSCRIBE_VENV    override the venv location
    TRANSCRIBE_PYTHON  interpreter used to create the venv (must be 3.10-3.14)
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REQUIREMENTS = HERE.parent / "requirements.txt"
SUPPORTED = [(3, 14), (3, 13), (3, 12), (3, 11), (3, 10)]  # limited by ctranslate2/PyAV wheels


def venv_dir() -> Path:
    if os.environ.get("TRANSCRIBE_VENV"):
        return Path(os.environ["TRANSCRIBE_VENV"]).expanduser()
    if os.name == "nt":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    return base / "spellbook" / "transcribe" / "venv"


def venv_python(venv: Path) -> Path:
    return venv / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def log(msg: str) -> None:
    print(f"[transcribe] {msg}", file=sys.stderr, flush=True)


def python_version(cmd: list[str]) -> tuple[int, int] | None:
    try:
        out = subprocess.run(
            cmd + ["-c", "import sys; print(sys.version_info[0], sys.version_info[1])"],
            capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return None
    if out.returncode != 0:
        return None
    major, minor = map(int, out.stdout.split())
    return major, minor


def find_python() -> list[str]:
    """Return a command for a Python interpreter that has the required binary wheels."""
    candidates: list[list[str]] = []
    if os.environ.get("TRANSCRIBE_PYTHON"):
        candidates.append([os.environ["TRANSCRIBE_PYTHON"]])
    candidates.append([sys.executable])
    for major, minor in SUPPORTED:
        if os.name == "nt" and shutil.which("py"):
            candidates.append(["py", f"-{major}.{minor}"])
        exe = shutil.which(f"python{major}.{minor}")
        if exe:
            candidates.append([exe])
    for cmd in candidates:
        if python_version(cmd) in SUPPORTED:
            return cmd
    sys.exit(
        "[transcribe] No supported Python found. Install Python 3.10-3.14 "
        "(3.15+ has no ctranslate2/PyAV wheels yet) or set TRANSCRIBE_PYTHON.")


def requirements_hash() -> str:
    return hashlib.sha256(REQUIREMENTS.read_bytes()).hexdigest()


def ensure_venv() -> Path:
    venv = venv_dir()
    py = venv_python(venv)
    stamp = venv / ".requirements.sha256"
    if py.exists() and stamp.exists() and stamp.read_text().strip() == requirements_hash():
        return py

    if not py.exists():
        base = find_python()
        log(f"creating virtual environment in {venv} (one-time setup)...")
        subprocess.run(base + ["-m", "venv", str(venv)], check=True)

    log("installing dependencies (about 1 GB with CUDA libraries, one-time)...")
    pip = [str(py), "-m", "pip", "install", "--disable-pip-version-check"]
    subprocess.run(pip + ["--upgrade", "pip", "-q"], check=True)
    subprocess.run(pip + ["-r", str(REQUIREMENTS), "--only-binary=av,ctranslate2"], check=True)
    stamp.write_text(requirements_hash())
    return py


def cuda_env(py: Path) -> dict[str, str]:
    """Put pip-installed NVIDIA libraries on the loader search path."""
    env = dict(os.environ)
    env.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
    purelib = subprocess.run(
        [str(py), "-c", "import sysconfig; print(sysconfig.get_paths()['purelib'])"],
        capture_output=True, text=True, check=True).stdout.strip()
    sub = "bin" if os.name == "nt" else "lib"
    dirs = [str(d) for d in sorted((Path(purelib) / "nvidia").glob(f"*/{sub}"))]
    if dirs:
        var = "PATH" if os.name == "nt" else "LD_LIBRARY_PATH"
        env[var] = os.pathsep.join(dirs + ([env[var]] if env.get(var) else []))
    return env


def main() -> int:
    args = sys.argv[1:]
    setup_only = "--setup" in args
    py = ensure_venv()
    if setup_only:
        log(f"environment ready: {py}")
        log(json.dumps({"venv": str(venv_dir())}))
        return 0
    cmd = [str(py), str(HERE / "transcribe.py"), *args]
    return subprocess.run(cmd, env=cuda_env(py)).returncode


if __name__ == "__main__":
    sys.exit(main())
