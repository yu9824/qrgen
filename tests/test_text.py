"""Tests of ``qrlocal.escape_control_chars``."""

from __future__ import annotations

import pytest

from qrlocal import escape_control_chars


@pytest.mark.parametrize(
    "text",
    [
        "https://example.com/?q=1",
        "こんにちは世界",
        "two\nlines\tand a tab",
        "family: \U0001f468‍\U0001f469‍\U0001f467",  # ZWJ emoji
        "back\\slash",
        "",
    ],
)
def test_keeps_ordinary_text(text):
    assert escape_control_chars(text) == text


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("ok\x1b[2J", "ok\\x1b[2J"),  # clear screen
        ("\x1b]0;title\x07", "\\x1b]0;title\\x07"),  # set window title
        ("safe\rrm -rf ~", "safe\\rrm -rf ~"),  # hide text behind \r
        ("a\x00b\x7fc", "a\\x00b\\x7fc"),
        ("\x9b31m", "\\x9b31m"),  # C1 control sequence introducer
        ("file‮gnp.exe", "file\\u202egnp.exe"),  # right-to-left override
        ("⁦x⁩", "\\u2066x\\u2069"),  # isolates
        ("‎‏؜", "\\u200e\\u200f\\u061c"),  # marks
    ],
)
def test_escapes_control_characters(text, expected):
    assert escape_control_chars(text) == expected


def test_the_result_has_no_control_characters_left():
    text = "".join(map(chr, range(0x00, 0xA0)))

    escaped = escape_control_chars(text)

    assert all(char.isprintable() or char in "\n\t" for char in escaped)
