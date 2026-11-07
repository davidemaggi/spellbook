# transcribe

Transcribe video and audio files locally with [faster-whisper](https://github.com/SYSTRAN/faster-whisper). Nothing is uploaded: the audio stays on your machine.

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

- **Python 3.10–3.14** on PATH. Python 3.15 is not supported yet because ctranslate2 and PyAV publish no wheels for it. If your default `python` is a different version, set `TRANSCRIBE_PYTHON` to a supported interpreter.
- **NVIDIA GPU with a recent driver (CUDA 12)** for fast transcription. The skill falls back to CPU automatically, which works but is much slower. Tested on an RTX A500 Laptop GPU with 4 GB of VRAM.
- ffmpeg is **not** required, because PyAV bundles its own FFmpeg libraries.

## First run

On the first run, `scripts/run.py`:

1. picks a supported Python interpreter;
2. creates a private virtual environment in
   - Windows: `%LOCALAPPDATA%\spellbook\transcribe\venv`
   - macOS/Linux: `~/.local/share/spellbook/transcribe/venv`

   (override the location with `TRANSCRIBE_VENV`);
3. installs `requirements.txt`, about 1 GB including the CUDA libraries. The install runs again only when `requirements.txt` changes.

The Whisper model (`large-v3-turbo`, about 1.6 GB) is downloaded to the Hugging Face cache on the first transcription.

To prepare everything ahead of time, run:

```text
python scripts/run.py --setup
```

## Running without an agent

```text
python scripts/run.py video.mp4 -l en
python scripts/run.py ~/Recordings -r --skip-existing
python scripts/run.py --help
```

| Option | Default | Description |
| --- | --- | --- |
| `-l, --language` | auto | Language code (`en`, `it`, ...) |
| `-r, --recursive` | off | Scan subfolders |
| `--skip-existing` | off | Skip files that already have `_raw.txt` and `.srt` |
| `--model` | `large-v3-turbo` | Any faster-whisper model name |
| `--device` | `auto` | `auto`, `cuda` or `cpu` |
| `--compute-type` | `int8_float16` (GPU) / `int8` (CPU) | ctranslate2 compute type |
| `--beam-size` | `5` | Beam search width |

## Troubleshooting

- **`No supported Python found`**: install Python 3.14 (or 3.10–3.13), or point `TRANSCRIBE_PYTHON` at an existing interpreter.
- **`CUDA unavailable ... falling back to CPU`**: update the NVIDIA driver. To rebuild the environment, delete the venv folder and run again.
- **Out of GPU memory**: try `--compute-type int8` or a smaller model (`--model medium`).
