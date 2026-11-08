# transcribe

Transcribe video and audio files locally with [faster-whisper](https://github.com/SYSTRAN/faster-whisper), on CPU or an optional NVIDIA GPU. The transcription script does not upload audio. Your agent reads the resulting text to produce the cleaned-up version.

For every input file `<name>.<ext>`, the skill writes these files next to it:

| File | Content |
| --- | --- |
| `<name>_raw.txt` | Raw transcript, one segment per line |
| `<name>.srt` | Subtitles with timestamps |
| `<name>_clean.md` | The transcript cleaned up by your AI agent: recognition errors fixed, punctuation added, text split into paragraphs. Nothing is summarized or cut. |

## Install

```bash
npx skills add davidemaggi/spellbook --skill transcribe -g
```

This works with any agent that supports Agent Skills; you will be asked which agents to install it for. With Claude Code you can also install it as a plugin (Claude Code 2.1.275+):

```text
/plugin install transcribe --marketplace davidemaggi/spellbook
```

See the [repository README](../../README.md#installation) for all options.

## Usage

Ask your agent in plain words, for example *"transcribe ~/Recordings/talk.mkv"* or *"transcribe every video in this folder and its subfolders, they are in Italian"*.

In agents with slash commands, such as Claude Code, you can also call the skill directly:

```text
/transcribe path/to/video.mp4
/transcribe path/to/folder -r --skip-existing
/transcribe "my talk.mkv" -l en
```

## Requirements

- **Python 3.10–3.14** on PATH, with binary wheels available for your OS and architecture. If your default `python` is a different version, set `TRANSCRIBE_PYTHON` to a supported interpreter. The launcher never compiles dependencies from source.
- **CPU:** supported by CTranslate2 on compatible x86-64 and ARM64 platforms. Apple Silicon runs on CPU; Apple, AMD and Intel GPUs are not accelerated by this backend. OS/Python wheel availability also matters; arbitrary hardware is not guaranteed.
- **Optional NVIDIA GPU with a recent driver (CUDA 12)** for faster transcription on Linux/Windows. Tested previously on an RTX A500 Laptop GPU with 4 GB of VRAM. In `auto` mode, CUDA initialization or decoding failures retry on CPU; explicit `--device cuda` reports failure instead.
- ffmpeg is **not** required, because PyAV bundles its own FFmpeg libraries.

## First run

On the first run, `scripts/run.py`:

1. picks a supported Python interpreter;
2. creates a private virtual environment in
   - Windows: `%LOCALAPPDATA%\spellbook\transcribe\venv`
   - macOS/Linux: `~/.local/share/spellbook/transcribe/venv`

   (override the location with `TRANSCRIBE_VENV`);
3. installs CPU dependencies from `requirements.txt`. In `auto` mode, a working `nvidia-smi` also enables `requirements-cuda.txt`; `--device cpu` skips CUDA installation, and `--device cuda` explicitly requests it. The dependency stamp includes the selected profile and its requirement files.

Existing environments are reused. Switching to CPU does not uninstall CUDA libraries already present; use a fresh `TRANSCRIBE_VENV` if you want a CPU-only environment.

The Whisper model (`large-v3-turbo`, about 1.6 GB) is downloaded to the Hugging Face cache on the first transcription.

To prepare dependencies ahead of time, run:

```text
python scripts/run.py --setup
python scripts/run.py --setup --device cpu
python scripts/run.py --setup --device cuda
```

`--setup` prepares dependencies only. Transcribe a file with the desired `--model` while online to download that model too. Subsequent runs can reuse the cached model offline. `--help` never creates an environment or downloads packages.

## Running without an agent

```text
python scripts/run.py video.mp4 -l en
python scripts/run.py ~/Recordings -r --skip-existing
python scripts/run.py video.mp4 --device cpu --model small
python scripts/run.py --help
```

`--model small` reduces download size and CPU work, with a possible accuracy tradeoff. The default model is unchanged. On a Mac ARM64, a 6.38-second synthetic English clip took about 1 second with `tiny` and 6 seconds with `large-v3-turbo`, excluding download and model loading; long recordings can behave differently.

Input files with the same output names, such as `talk.mp3` and `talk.mp4`, are rejected before writing, including with `--skip-existing`. Rename one input or place it in another directory. Re-running a single input replaces its existing raw/SRT files unless `--skip-existing` is used. When every input is skipped, the exit code is zero.

| Option | Default | Description |
| --- | --- | --- |
| `-l, --language` | auto | Language code (`en`, `it`, ...) |
| `-r, --recursive` | off | Scan subfolders |
| `--skip-existing` | off | Skip files that already have `_raw.txt` and `.srt` |
| `--model` | `large-v3-turbo` | Any faster-whisper model name |
| `--device` | `auto` | `auto`, `cuda` or `cpu` |
| `--compute-type` | `int8_float16` (GPU) / `int8` (CPU), or `float32` when unavailable | Validated against the selected device; CPU fallback resets precision |
| `--beam-size` | `5` | Beam search width |

## Troubleshooting

- **`No supported Python found`**: install Python 3.10–3.14, or point `TRANSCRIBE_PYTHON` at an existing interpreter.
- **Dependency download/install failure**: check connectivity, available disk space, and wheel support for your Python/OS/architecture. For Linux Python installations missing `venv`, install your distribution's Python venv package. A failed setup is retried on the next run.
- **`CUDA unavailable ... falling back to CPU`**: update the NVIDIA driver, or use `--device cpu`. If NVIDIA hardware is available but `nvidia-smi` is not on PATH, use `--setup --device cuda` to install the optional runtime libraries explicitly.
- **Unsupported compute type**: use one of the types listed in the error, or omit `--compute-type` to select a supported default.
- **Out of GPU memory**: try `--compute-type int8` or a smaller model (`--model medium`).

## Development checks

From the repository root:

```text
python -m unittest discover -s tests
python tools/validate.py
python tests/smoke_transcribe.py
```

The unit tests need only the standard library. The smoke test downloads a public speech sample and the `tiny` model, bootstraps a CPU environment through the launcher, and checks the transcript and SRT. CI runs these checks on Linux, macOS and Windows; NVIDIA hardware still requires a separate manual test.
