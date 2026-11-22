"""Read QR codes from images and a camera with OpenCV.

OpenCV is optional (``pip install "qrlocal[camera]"``), so it is imported
inside the functions that need it.
"""

from __future__ import annotations

import os
import sys
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path
from types import ModuleType
from typing import Any

from .helpers import is_installed

__all__ = ("decode_image", "scan_camera")

INSTALL_HINT = 'pip install "qrlocal[camera]"'

# Byte mode has no fixed text encoding. UTF-8 is what most generators
# write; Shift_JIS is what Kanji mode holds; ISO 8859-1 is the default of
# the standard and decodes any bytes, so it comes last.
_FALLBACK_ENCODINGS = ("utf-8", "shift_jis")
_LAST_ENCODING = "iso-8859-1"

_WINDOW_NAME = "qrlocal scan - q / Esc to stop"
_QUIT_KEYS = frozenset({ord("q"), ord("Q"), 27})  # 27: Esc

# Takes a frame to show; returns True when the user asks to stop.
_ShowFrame = Callable[[Any], bool]


def _import_cv2() -> ModuleType:
    if not is_installed("cv2"):
        raise ImportError(
            f"reading QR codes requires OpenCV; install it with "
            f"`{INSTALL_HINT}`.",
            name="cv2",
        )
    import cv2

    return cv2


def _bytes_to_text(data: bytes) -> str:
    for encoding in _FALLBACK_ENCODINGS:
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode(_LAST_ENCODING)


def _make_decoder(cv2: ModuleType) -> Callable[[Any], list[str]]:
    """Return a function that reads every QR code in an image."""
    # The ArUco based detector finds codes in camera frames more reliably.
    detector = cv2.QRCodeDetectorAruco()

    def decode(image: Any) -> list[str]:
        # The bytes variant, because the str variant fails on payloads that
        # are not UTF-8 (UnicodeDecodeError raised from inside OpenCV).
        found, payloads, _, _ = detector.detectAndDecodeBytesMulti(image)
        if not found:
            return []
        # A code that was found but could not be decoded gives b"".
        return [_bytes_to_text(bytes(data)) for data in payloads if data]

    return decode


def decode_image(path: str | os.PathLike[str]) -> list[str]:
    """Read the QR codes in an image file.

    Parameters
    ----------
    path : str or os.PathLike
        An image OpenCV can read, such as PNG, JPEG, or BMP.

    Returns
    -------
    list of str
        The text of each code found, in no particular order. Empty if there
        is none.

    Raises
    ------
    ImportError
        If OpenCV is not installed.
    FileNotFoundError
        If ``path`` does not exist.
    ValueError
        If the file is not an image OpenCV can read.

    Notes
    -----
    The text comes from outside; do not open or run it without checking.
    """
    cv2 = _import_cv2()
    import numpy as np

    path = Path(path)
    # Read the bytes in Python: cv2.imread cannot open non-ASCII paths on
    # Windows and returns None instead of telling why it failed.
    data = np.frombuffer(path.read_bytes(), dtype=np.uint8)
    image = cv2.imdecode(data, cv2.IMREAD_GRAYSCALE) if data.size else None
    if image is None:
        raise ValueError(
            f"{path} is not an image OpenCV can read; "
            "use a format such as PNG, JPEG, or BMP."
        )
    return _make_decoder(cv2)(image)


def _camera_hint(device: int) -> str:
    if sys.platform == "darwin":
        hint = (
            "On macOS, allow camera access for the app running Python "
            "(Terminal, iTerm2, VS Code, ...) in System Settings > Privacy "
            "& Security > Camera, then quit and reopen that app. The first "
            "run fails while macOS asks for permission; run again after "
            "allowing it."
        )
    elif sys.platform == "win32":
        hint = (
            "On Windows, turn on Settings > Privacy & security > Camera > "
            "Let desktop apps access your camera."
        )
    else:
        hint = (
            f"On Linux, check that /dev/video{device} exists and that your "
            "user may read it (e.g. is in the 'video' group)."
        )
    return (
        f"cannot open camera {device}. {hint} Also close other apps using "
        "the camera, or try another device number."
    )


@contextmanager
def _open_camera(cv2: ModuleType, device: int) -> Iterator[Any]:
    capture = cv2.VideoCapture(device)
    try:
        if not capture.isOpened():
            raise RuntimeError(_camera_hint(device))
        yield capture
    finally:
        capture.release()


@contextmanager
def _preview(cv2: ModuleType, enabled: bool) -> Iterator[_ShowFrame]:
    """Give a function that shows frames in a window, if enabled."""
    if not enabled:
        yield lambda frame: False
        return

    try:
        cv2.namedWindow(_WINDOW_NAME)
    except cv2.error as exc:
        raise RuntimeError(
            "cannot open a preview window (is there a display?); "
            "turn the preview off (--no-preview on the command line)."
        ) from exc

    def is_open() -> bool:
        visible = cv2.getWindowProperty(_WINDOW_NAME, cv2.WND_PROP_VISIBLE)
        return bool(visible >= 1)

    def show(frame: Any) -> bool:
        # Mirror the view so that moving the code feels natural. Only the
        # view: the decoder reads the frame as the camera took it.
        cv2.imshow(_WINDOW_NAME, cv2.flip(frame, 1))
        key = cv2.waitKey(1)
        return (key & 0xFF) in _QUIT_KEYS or not is_open()

    try:
        yield show
    finally:
        if is_open():
            cv2.destroyWindow(_WINDOW_NAME)
        # Let the GUI event loop process the close (needed on macOS).
        cv2.waitKey(1)


def scan_camera(
    *,
    device: int = 0,
    timeout: float | None = None,
    preview: bool = True,
) -> str | None:
    """Read a QR code with a camera.

    Frames are processed in memory only and never written anywhere. The
    camera and the window are released when this returns, also on errors
    and Ctrl+C.

    Parameters
    ----------
    device : int, default 0
        Index of the camera.
    timeout : float, optional
        Give up after this many seconds. Wait forever by default.
    preview : bool, default True
        Show what the camera sees in a window. Press q or Esc there, or close
        it, to stop.

    Returns
    -------
    str or None
        The text of the first code read, or None if the user stopped.

    Raises
    ------
    ImportError
        If OpenCV is not installed.
    ValueError
        If ``timeout`` is not positive.
    RuntimeError
        If the camera or the preview window cannot be opened, or the camera
        stops sending frames.
    TimeoutError
        If no code is read within ``timeout`` seconds.

    Notes
    -----
    The text comes from outside; do not open or run it without checking.
    """
    if timeout is not None and timeout <= 0:
        raise ValueError(f"timeout must be positive, not {timeout}.")
    cv2 = _import_cv2()
    decode = _make_decoder(cv2)
    deadline = None if timeout is None else time.monotonic() + timeout

    with _open_camera(cv2, device) as capture, _preview(cv2, preview) as show:
        while True:
            ok, frame = capture.read()
            if not ok:
                raise RuntimeError(
                    f"camera {device} stopped sending frames; check that "
                    "no other app took it over."
                )
            texts = decode(frame)
            if texts:
                return texts[0]
            if show(frame):
                return None
            if deadline is not None and time.monotonic() >= deadline:
                raise TimeoutError(
                    f"no QR code read within {timeout} seconds; hold the "
                    "code closer to the camera, in good light."
                )
