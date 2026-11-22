# qrlocal

<!-- badges -->
[![CI](https://github.com/yu9824/qrlocal/actions/workflows/CI.yml/badge.svg)](https://github.com/yu9824/qrlocal/actions/workflows/CI.yml)
[![docs](https://github.com/yu9824/qrlocal/actions/workflows/docs.yml/badge.svg)](https://github.com/yu9824/qrlocal/actions/workflows/docs.yml)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![mypy](https://www.mypy-lang.org/static/mypy_badge.svg)](https://github.com/python/mypy)
<!-- /badges -->

Generate and read QR codes entirely on your machine. No network access, works offline.

- **Generate**: text → PNG / SVG, or draw it right in the terminal
- **Read**: image files, or your computer's camera

## Installation

```bash
# generate only (depends on segno, pure Python)
pip install git+https://github.com/yu9824/qrlocal.git

# also read QR codes (adds OpenCV)
pip install "qrlocal[camera] @ git+https://github.com/yu9824/qrlocal.git"
```

`opencv-python` cannot share an environment with the other OpenCV wheels (`opencv-python-headless`, `opencv-contrib-python`, ...). Uninstall those first.

## Command line

```bash
# Draw in the terminal (use --invert on a light background)
qrlocal encode "https://example.com"

# Write an image; .png or .svg. Existing files are kept unless --force
qrlocal encode "https://example.com" -o example.png

# Secrets: pipe them in so they stay out of the shell history
pbpaste | qrlocal encode -o wifi.png

# Read image files
qrlocal decode example.png

# Read with the camera (q / Esc in the preview window to stop)
qrlocal scan
qrlocal scan --device 1 --timeout 30 --no-preview
```

See `qrlocal <command> --help` for all options.

## Python

```python
import qrlocal

qrlocal.save_qr("https://example.com", "example.png", error="Q")
print(qrlocal.render_terminal("hello"))

# needs qrlocal[camera]
texts = qrlocal.decode_image("example.png")  # -> ["https://example.com"]
text = qrlocal.scan_camera(timeout=30)  # None if the user stopped

# Decoded text comes from anyone: escape it before printing to a terminal
print(qrlocal.escape_control_chars(text))
```

## Camera permission

The first `qrlocal scan` asks the OS for camera access for the app that runs Python, not for qrlocal itself.

| OS | Where to allow |
| --- | --- |
| macOS | System Settings > Privacy & Security > Camera: turn on Terminal / iTerm2 / VS Code, then restart that app. The first run fails while the dialog is shown; run again after allowing |
| Windows | Settings > Privacy & security > Camera > Let desktop apps access your camera |
| Linux | Your user needs read access to `/dev/video*` (usually the `video` group) |

The camera does not work inside the dev container. Run `scan` on the host.

## Security

- **No network.** Neither segno nor OpenCV is used in a way that connects anywhere. The test suite blocks sockets to keep it that way.
- **Decoded text is untrusted.** qrlocal never opens URLs or runs anything it reads. The CLI escapes control characters (terminal escape sequences, `\r`, bidirectional overrides) unless you pass `--raw`.
- **Nothing is recorded.** Camera frames stay in memory and are never written to disk.
- **Files.** Images are created readable by you only (mode `0600` on macOS / Linux), since they contain the text, and existing files are not overwritten without `--force` / `overwrite=True`.
- **Shell history.** Text given as an argument is saved in your shell history and visible to other processes; pipe secrets through stdin instead.

## Directory layout

| Directory | Purpose |
| --- | --- |
| `src/qrlocal/` | Package source |
| `tests/` | pytest tests |
| `docs_src/` | Sphinx source |
| `.devcontainer/` | Development container (VS Code Dev Containers) |
