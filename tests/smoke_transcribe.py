"""Online CPU integration test using Whisper's public JFK speech fixture."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import urllib.request


def main():
    root = Path(__file__).resolve().parents[1]
    with tempfile.TemporaryDirectory(prefix="transcribe-smoke-") as folder:
        work = Path(folder)
        media = work / "jfk.flac"
        with urllib.request.urlopen(
                "https://raw.githubusercontent.com/openai/whisper/main/tests/jfk.flac",
                timeout=60) as response:
            media.write_bytes(response.read())
        env = dict(os.environ)
        env.setdefault("TRANSCRIBE_VENV", str(work / "venv"))
        command = [sys.executable, str(root / "skills/transcribe/scripts/run.py"),
                   str(media), "--device", "cpu", "--model", "tiny", "-l", "en"]
        subprocess.run(command, env=env, check=True, timeout=600)
        transcript = (work / "jfk_raw.txt").read_text(encoding="utf-8").lower()
        srt = (work / "jfk.srt").read_text(encoding="utf-8")
        assert "fellow americans" in transcript and "country" in transcript, transcript
        assert "1\n" in srt and " --> " in srt, srt
        subprocess.run(command + ["--skip-existing"], env=env, check=True, timeout=60)
        print("CPU smoke test OK: speech recognized, SRT generated, existing output skipped.")


if __name__ == "__main__":
    main()
