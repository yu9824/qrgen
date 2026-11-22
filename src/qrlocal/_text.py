"""Make decoded text safe to print."""

from __future__ import annotations

import unicodedata

__all__ = ("escape_control_chars",)

# Kept as is: they only move to the next line or column.
_ALLOWED = frozenset("\n\t")

# Bidirectional controls reorder how the text is displayed, so a payload
# can look different from what it is ("Trojan Source"). They are format
# characters (Cf), but other Cf characters such as the zero width joiner in
# emoji are harmless and kept.
_BIDI_CONTROLS = frozenset(
    map(
        chr,
        (
            0x061C,  # arabic letter mark
            *range(0x200E, 0x2010),  # LRM, RLM
            *range(0x202A, 0x202F),  # LRE, RLE, PDF, LRO, RLO
            *range(0x2066, 0x206A),  # LRI, RLI, FSI, PDI
        ),
    )
)


def _escape(char: str) -> str:
    if char in _ALLOWED:
        return char
    if unicodedata.category(char) == "Cc" or char in _BIDI_CONTROLS:
        return char.encode("unicode_escape").decode("ascii")
    return char


def escape_control_chars(text: str) -> str:
    r"""Escape characters that could take over a terminal.

    Text read from a QR code comes from anyone. Printed as is, an escape
    sequence in it could change the terminal (colors, title, cursor, or
    worse on some terminals), and a carriage return or bidirectional
    control could make it look like something else. This replaces control
    characters other than ``\n`` and ``\t``, and bidirectional controls,
    with escapes such as ``\x1b``.

    Parameters
    ----------
    text : str
        The text to make printable.

    Returns
    -------
    str
        The text with the characters escaped.

    Examples
    --------
    >>> escape_control_chars("ok\x1b[2J")
    'ok\\x1b[2J'
    """
    return "".join(_escape(char) for char in text)
