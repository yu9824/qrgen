"""Generate QR codes locally with segno."""

from __future__ import annotations

import io
import os
from pathlib import Path
from typing import Literal

import segno

__all__ = ("ErrorLevel", "make_qr", "render_terminal", "save_qr")

ErrorLevel = Literal["L", "M", "Q", "H"]
"""Error correction level: about 7 %, 15 %, 25 %, or 30 % of the code can be
damaged and still read."""

ERROR_LEVELS: tuple[ErrorLevel, ...] = ("L", "M", "Q", "H")

# Extension -> segno's ``kind``.
_FORMATS = {".png": "png", ".svg": "svg"}

# The written image holds the text itself, which may be a secret such as a
# Wi-Fi password, so only the owner may read a newly created file.
_NEW_FILE_MODE = 0o600

# Light / dark modules of the upper and lower half of a character cell.
_HALF_BLOCKS = {
    (False, False): " ",
    (True, False): "▀",  # upper half block
    (False, True): "▄",  # lower half block
    (True, True): "█",  # full block
}


def _check_error_level(error: str) -> ErrorLevel:
    level = error.upper()
    for candidate in ERROR_LEVELS:
        if level == candidate:
            return candidate
    raise ValueError(
        f"unknown error correction level {error!r}; "
        f"use one of {', '.join(ERROR_LEVELS)}."
    )


def make_qr(text: str, *, error: ErrorLevel = "M") -> segno.QRCode:
    """Encode text into a QR code.

    Non-ASCII text is stored as UTF-8 in byte mode without an ECI header,
    which phones and OpenCV read as is.

    Parameters
    ----------
    text : str
        The text to encode. Must not be empty.
    error : {"L", "M", "Q", "H"}, default "M"
        Error correction level. A higher level survives more damage but holds
        less text.

    Returns
    -------
    segno.QRCode
        The QR code.

    Raises
    ------
    ValueError
        If ``text`` is empty or too long, or ``error`` is unknown.
    """
    if not text:
        raise ValueError("text is empty; give at least one character.")
    level = _check_error_level(error)
    try:
        return segno.make_qr(
            text,
            error=level,
            encoding="utf-8",
            eci=False,
            # Keep the level that was asked for, so the size of the code
            # does not depend on how much room is left.
            boost_error=False,
        )
    except segno.DataOverflowError as exc:
        size = len(text.encode("utf-8"))
        raise ValueError(
            f"text is too long for a QR code ({size} bytes in UTF-8 at "
            f"error correction level {level}); shorten it or use a lower "
            "level such as 'L'."
        ) from exc


def save_qr(
    text: str,
    path: str | os.PathLike[str],
    *,
    scale: int = 10,
    border: int = 4,
    error: ErrorLevel = "M",
    overwrite: bool = False,
) -> Path:
    """Write text as a QR code image.

    The format follows the extension of ``path``: ``.png`` or ``.svg``.
    A new file is readable by its owner only, since the image holds the text.

    Parameters
    ----------
    text : str
        The text to encode.
    path : str or os.PathLike
        Where to write the image.
    scale : int, default 10
        Size of one module, in pixels (PNG) or user units (SVG).
    border : int, default 4
        Width of the quiet zone around the code, in modules. Readers need
        at least 4 to find the code reliably.
    error : {"L", "M", "Q", "H"}, default "M"
        Error correction level.
    overwrite : bool, default False
        Replace ``path`` if it already exists.

    Returns
    -------
    pathlib.Path
        The path written to.

    Raises
    ------
    ValueError
        If the extension, ``scale``, ``border``, ``text``, or ``error`` is
        invalid.
    FileExistsError
        If ``path`` exists and ``overwrite`` is False.
    """
    path = Path(path)
    kind = _FORMATS.get(path.suffix.lower())
    if kind is None:
        raise ValueError(
            f"cannot tell the image format from {path.name!r}; "
            f"end the file name with one of {', '.join(_FORMATS)}."
        )
    if scale < 1:
        raise ValueError(f"scale must be 1 or more, not {scale}.")
    if border < 0:
        raise ValueError(f"border must be 0 or more, not {border}.")

    buffer = io.BytesIO()
    make_qr(text, error=error).save(
        buffer, kind=kind, scale=scale, border=border
    )

    # O_EXCL creates the file only if it does not exist, in one step, so a
    # file made between a check and the write is never overwritten.
    flags = os.O_WRONLY | os.O_CREAT | getattr(os, "O_BINARY", 0)
    flags |= os.O_TRUNC if overwrite else os.O_EXCL
    try:
        fd = os.open(path, flags, _NEW_FILE_MODE)
    except FileExistsError as exc:
        raise FileExistsError(
            f"{path} already exists; pass overwrite=True "
            "(--force on the command line) to replace it."
        ) from exc
    with os.fdopen(fd, "wb") as file:
        file.write(buffer.getvalue())
    return path


def render_terminal(
    text: str,
    *,
    error: ErrorLevel = "M",
    border: int = 4,
    invert: bool = False,
) -> str:
    """Draw text as a QR code with Unicode half blocks.

    Two rows of modules fit in one line. By default light modules are drawn
    with blocks, which suits a light-on-dark terminal; pass ``invert=True``
    for a dark-on-light one.

    Parameters
    ----------
    text : str
        The text to encode.
    error : {"L", "M", "Q", "H"}, default "M"
        Error correction level.
    border : int, default 4
        Width of the quiet zone, in modules.
    invert : bool, default False
        Draw dark modules with blocks instead of light ones.

    Returns
    -------
    str
        The drawing, one line per two rows of modules, ending in a newline.
    """
    if border < 0:
        raise ValueError(f"border must be 0 or more, not {border}.")
    qr = make_qr(text, error=error)
    # True where a block is drawn.
    rows = [
        [bool(dark) == invert for dark in row]
        for row in qr.matrix_iter(scale=1, border=border)
    ]
    if len(rows) % 2:
        rows.append([not invert] * len(rows[0]))
    lines = (
        "".join(_HALF_BLOCKS[pair] for pair in zip(upper, lower, strict=True))
        for upper, lower in zip(rows[::2], rows[1::2], strict=True)
    )
    return "\n".join(lines) + "\n"
