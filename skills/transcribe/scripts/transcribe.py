"""Local video/audio transcription with faster-whisper.

For every input media file, writes next to it:
    <name>_raw.txt   plain transcript, one segment per line
    <name>.srt       subtitles with timestamps

Usually invoked through run.py, which bootstraps the virtual environment.
Can also be run directly from an environment where faster-whisper is installed.
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

MEDIA_EXTS = {
    # video
    ".mp4", ".mkv", ".mov", ".avi", ".webm", ".m4v", ".wmv", ".flv",
    ".mpg", ".mpeg", ".ts", ".3gp",
    # audio
    ".mp3", ".wav", ".m4a", ".flac", ".ogg", ".opus", ".aac",
}


def add_windows_cuda_dlls() -> None:
    """Expose pip-installed cuBLAS/cuDNN DLLs to ctranslate2 on Windows.

    On Linux this must happen before the process starts (LD_LIBRARY_PATH),
    which run.py takes care of.
    """
    if os.name != "nt":
        return
    import site

    for root in map(Path, site.getsitepackages()):
        for d in (root / "nvidia").glob("*/bin"):
            os.add_dll_directory(str(d))
            os.environ["PATH"] = f"{d}{os.pathsep}{os.environ.get('PATH', '')}"


def collect_media(inputs: list[str], recursive: bool) -> list[Path]:
    found: dict[Path, None] = {}  # ordered set
    for raw in inputs:
        p = Path(raw).expanduser()
        if p.is_dir():
            it = p.rglob("*") if recursive else p.iterdir()
            for f in sorted(it):
                if f.is_file() and f.suffix.lower() in MEDIA_EXTS:
                    found[f.resolve()] = None
        elif p.is_file():
            found[p.resolve()] = None
        else:
            print(f"[warn] path not found, skipped: {p}", file=sys.stderr)
    return list(found)


def output_paths(media: Path) -> tuple[Path, Path]:
    return media.with_name(media.stem + "_raw.txt"), media.with_suffix(".srt")


def srt_time(t: float) -> str:
    ms = int(round(t * 1000))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def load_model(name: str, device: str, compute_type: str | None):
    from faster_whisper import WhisperModel

    if device == "auto":
        import ctranslate2

        device = "cuda" if ctranslate2.get_cuda_device_count() > 0 else "cpu"

    def ct(dev: str) -> str:
        # int8_float16 fits large-v3-turbo comfortably in 4 GB of VRAM.
        return compute_type or ("int8_float16" if dev == "cuda" else "int8")

    print(f"Loading model {name} on {device} ({ct(device)})...", flush=True)
    try:
        return WhisperModel(name, device=device, compute_type=ct(device))
    except Exception as e:
        if device != "cuda":
            raise
        print(f"[warn] CUDA unavailable ({e}); falling back to CPU, this will be slow.",
              file=sys.stderr)
        return WhisperModel(name, device="cpu", compute_type=ct("cpu"))


def transcribe_one(model, media: Path, language: str | None, beam_size: int,
                   show_progress: bool) -> tuple[Path, Path]:
    raw_path, srt_path = output_paths(media)
    t0 = time.time()
    segments, info = model.transcribe(
        str(media),
        language=language,
        beam_size=beam_size,
        vad_filter=True,
        vad_parameters={"min_silence_duration_ms": 500},
    )
    print(f"    language: {info.language} (p={info.language_probability:.2f}), "
          f"duration: {info.duration / 60:.1f} min", flush=True)

    texts: list[str] = []
    srt_blocks: list[str] = []
    for seg in segments:  # lazy generator: decoding happens here
        text = seg.text.strip()
        if not text:
            continue
        texts.append(text)
        srt_blocks.append(
            f"{len(srt_blocks) + 1}\n{srt_time(seg.start)} --> {srt_time(seg.end)}\n{text}\n")
        if show_progress and info.duration:
            pct = min(100.0, seg.end / info.duration * 100)
            print(f"\r    progress: {pct:5.1f}%", end="", flush=True)
    if show_progress:
        print()

    # Write only after a successful run, so a crash never leaves half-written outputs.
    srt_path.write_text("\n".join(srt_blocks), encoding="utf-8")
    raw_path.write_text("\n".join(texts) + "\n", encoding="utf-8")
    print(f"    -> {raw_path}\n    -> {srt_path}\n    ({time.time() - t0:.0f}s)", flush=True)
    return raw_path, srt_path


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(
        description="Transcribe video/audio files locally with faster-whisper.")
    ap.add_argument("inputs", nargs="+", help="media files and/or folders")
    ap.add_argument("-l", "--language", default=None,
                    help="language code (e.g. en, it). Default: auto-detect")
    ap.add_argument("-r", "--recursive", action="store_true", help="also scan subfolders")
    ap.add_argument("--skip-existing", action="store_true",
                    help="skip files that already have both _raw.txt and .srt")
    ap.add_argument("--model", default="large-v3-turbo", help="Whisper model (default: %(default)s)")
    ap.add_argument("--device", choices=["auto", "cuda", "cpu"], default="auto")
    ap.add_argument("--compute-type", default=None,
                    help="default: int8_float16 on CUDA, int8 on CPU")
    ap.add_argument("--beam-size", type=int, default=5)
    return ap.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass

    args = parse_args(argv)
    media = collect_media(args.inputs, args.recursive)
    if args.skip_existing:
        media = [m for m in media if not all(p.exists() for p in output_paths(m))]
    if not media:
        print("Nothing to transcribe.", file=sys.stderr)
        return 1

    add_windows_cuda_dlls()
    model = load_model(args.model, args.device, args.compute_type)
    show_progress = sys.stdout.isatty()

    failures = 0
    for n, m in enumerate(media, start=1):
        print(f"[{n}/{len(media)}] {m}", flush=True)
        try:
            transcribe_one(model, m, args.language, args.beam_size, show_progress)
        except Exception as e:  # keep going with the remaining files
            failures += 1
            print(f"    [error] {type(e).__name__}: {e}", file=sys.stderr)

    print(f"Done: {len(media) - failures} ok, {failures} failed.")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
