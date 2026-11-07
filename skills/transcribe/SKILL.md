---
name: transcribe
description: Transcribe video or audio files locally (faster-whisper on an NVIDIA GPU, CPU fallback) into a raw transcript, SRT subtitles and a cleaned-up Markdown version. Use when the user asks to transcribe, caption or get the text of a video/audio file or a folder of recordings.
license: MIT
compatibility: Requires Python 3.10-3.14 and internet access on first run to download dependencies and the model. An NVIDIA GPU (CUDA 12) is recommended.
argument-hint: <file-or-folder> [more paths] [-l <lang>] [-r] [--skip-existing]
metadata:
  author: Davide Maggi
  version: "1.1.0"
---

# Transcribe

Transcribe the video/audio files or folders the user asked for, then produce a cleaned-up version of each transcript.

## 1. Run the transcription

The launcher is `scripts/run.py`, relative to this skill's directory (the folder that contains this SKILL.md; in Claude Code: `${CLAUDE_SKILL_DIR}`). Use its absolute path and run it with Python, passing the user's paths and options, and quoting any path that contains spaces:

```text
python "<skill-dir>/scripts/run.py" <paths> [options]
```

- On macOS/Linux use `python3` if `python` is missing. On Windows, `py` works too.
- The first run creates a private virtual environment and downloads about 1 GB of dependencies plus the Whisper model (about 1.6 GB). Later runs start in seconds.
- Allow a long timeout (10 minutes or more), or run the command in the background and wait for it to finish. Expect roughly 1 minute of processing for 10 minutes of audio on a mid-range GPU, and much longer on CPU.
- Options: `-l <code>` forces the language (default: auto-detect), `-r` scans subfolders, `--skip-existing` skips files already transcribed, `--device cpu` forces CPU. `--help` lists all of them.
- If the script fails, show the error to the user and stop. Do not continue to step 2.

For each media file `<name>.<ext>`, the script writes `<name>_raw.txt` and `<name>.srt` next to it and prints both paths on lines starting with `->`. Collect every `_raw.txt` reported in this run.

## 2. Clean up each transcript

For every `<name>_raw.txt`:

1. Read the whole file. If it is long, read it in chunks without skipping anything.
2. Write `<name>_clean.md` in the same folder:
   - start with a `# <name>` title;
   - fix speech-recognition errors (misheard words, misspelled names and technical terms, homophones) by inferring them from context;
   - fix punctuation and capitalization;
   - split the text into logical paragraphs, one per idea or topic. For long content with clear sections, add `##` headings.
3. Constraints:
   - keep **every** concept, example, number and step. Do not summarize, cut or add content;
   - keep the original language of the transcript, and do not translate;
   - you may remove only filler words and content-free repetitions or false starts (e.g. "um", "uh", "you know, you know");
   - if a word is unintelligible and cannot be inferred, leave it as-is followed by `[?]`.

If there are many or very long files and you can run subagents, you may delegate each file's cleanup with these same instructions.

## 3. Report

List the files created (`_raw.txt`, `.srt`, `_clean.md`) and point out any corrections you were unsure about, quoting the original and the replacement.
