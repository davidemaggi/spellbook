# Transcribe portability implementation plan

> **For agentic workers:** Use superpowers:executing-plans to implement this plan task by task. Steps use checkbox syntax for tracking.

**Goal:** Make the existing faster-whisper workflow reliable with and without NVIDIA hardware.

**Architecture:** Keep the standard-library launcher and private environment. Separate optional CUDA dependencies, validate device precision, retry automatic CUDA runtime failures once on CPU, and reject colliding output names before writing.

**Tech stack:** Python standard library, faster-whisper, CTranslate2, unittest, GitHub Actions.

**Spec:** The investigation and recommendation approved by the user with “procedi”.

## Global constraints

- Preserve output names and the large-v3-turbo default; document --model small for slower CPUs.
- Keep every launcher and test runnable with the Python standard library.
- Bump the skill and plugin to 1.2.0; keep skill instructions agent-portable and in English.
- Leave Apple GPU acceleration for a separate change.

## Review focus

- Help and invalid options must not trigger dependency downloads.
- Switching CPU/CUDA must invalidate the dependency stamp correctly.
- Network and corrupt-media failures must not be retried as CUDA failures.
- Collisions must be detected before filtering existing outputs.
- Lazy decoding errors must leave existing output files intact.

### Task 1: Portable setup

Files: scripts/run.py, requirements.txt, new requirements-cuda.txt under skills/transcribe; tests/test_transcribe.py.

- [x] Write tests for CPU-only setup, automatic NVIDIA detection, explicit CUDA, requirement stamps, and help without installation; run and observe failures.
- [x] Select optional CUDA dependencies using --device and nvidia-smi; hash both dependency files for CUDA environments; surface setup errors without tracebacks.
- [x] Run the setup tests until green.

### Task 2: Reliable execution and release documentation

Files: skills/transcribe/scripts/transcribe.py, SKILL.md, README.md, .claude-plugin/plugin.json; root README.md and .github/workflows/validate.yml; tests/test_transcribe.py.

- [x] Write regressions for unsupported precision, probe failures, CUDA fallback during lazy decoding, collisions, skipped inputs, and preserved outputs on failure; observe failures.
- [x] Implement the smallest fixes, retaining strict errors for explicitly requested CUDA and invalid precision.
- [x] Document CPU usage, optional CUDA setup, offline reuse after downloads, errors and supported platforms; bump both versions.
- [x] Run unittest and tools/validate.py; configure the same checks on Linux, macOS and Windows.
- [x] Run real CPU inference using the temporary environment/audio/model from the investigation; inspect raw text and SRT, then review the full diff.

## Verification record

- Offline regressions pass and repository validation prints OK.
- Public JFK speech smoke test passed on Mac ARM64 with tiny, including SRT and skip-existing assertions.
- The original synthetic recording also passed with large-v3-turbo using HF_HUB_OFFLINE=1.
- Local Python's default certificate bundle was missing. The online smoke test used SSL_CERT_FILE=/etc/ssl/cert.pem with TLS verification enabled.
- Independent review found no correctness issues; its suggested lazy non-CUDA decoding regression was added.
- Linux/Windows CI is configured but not executed locally; real NVIDIA hardware and Apple GPU acceleration were not tested.

No commit, tag or publication is needed for this task.
