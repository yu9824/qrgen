"""Tests of the QR code generation in ``qrlocal``."""

from __future__ import annotations

import os
import socket
import stat
import sys

import pytest
import segno

import qrlocal
from qrlocal import make_qr, render_terminal, save_qr

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"

# Dark modules of the upper and lower half -> character (invert=True).
HALF_BLOCKS = {
    (False, False): " ",
    (True, False): "\u2580",
    (False, True): "\u2584",
    (True, True): "\u2588",
}


def test_all_public_names_are_importable():
    for name in qrlocal.__all__:
        assert hasattr(qrlocal, name)


def test_the_network_is_blocked_during_tests():
    with pytest.raises(AssertionError, match="offline"):
        socket.create_connection(("example.com", 80))


# --- make_qr -----------------------------------------------------------------


@pytest.mark.parametrize("text", ["hello", "こんにちは世界", "café ✓"])
def test_make_qr_stores_text_as_utf8_bytes(text):
    qr = make_qr(text)

    assert qr.mode == "byte"
    assert not qr.is_micro


@pytest.mark.parametrize("error", ["L", "M", "Q", "H", "q"])
def test_make_qr_keeps_the_error_level(error):
    assert make_qr("hello", error=error).error == error.upper()


def test_make_qr_rejects_empty_text():
    with pytest.raises(ValueError, match="empty"):
        make_qr("")


def test_make_qr_rejects_an_unknown_error_level():
    with pytest.raises(ValueError, match="L, M, Q, H"):
        make_qr("hello", error="X")  # type: ignore[arg-type]


def test_make_qr_rejects_too_long_text_with_a_hint():
    with pytest.raises(ValueError, match="too long.*'L'") as excinfo:
        make_qr("a" * 3000, error="H")

    assert isinstance(excinfo.value.__cause__, segno.DataOverflowError)


# --- save_qr -----------------------------------------------------------------


@pytest.mark.parametrize("name", ["code.png", "CODE.PNG"])
def test_save_qr_writes_png(tmp_path, name):
    path = save_qr("hello", tmp_path / name)

    assert path == tmp_path / name
    assert path.read_bytes().startswith(PNG_SIGNATURE)


def test_save_qr_writes_svg(tmp_path):
    path = save_qr("hello", tmp_path / "code.svg")

    assert b"<svg" in path.read_bytes()


def test_save_qr_accepts_a_str_path(tmp_path):
    path = save_qr("hello", str(tmp_path / "code.png"))

    assert path.exists()


def test_save_qr_scale_changes_the_image_size(tmp_path):
    small = save_qr("hello", tmp_path / "small.png", scale=1).stat().st_size
    large = save_qr("hello", tmp_path / "large.png", scale=20).stat().st_size

    assert large > small


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX permissions only")
def test_save_qr_makes_a_file_only_the_owner_can_read(tmp_path):
    path = save_qr("secret", tmp_path / "code.png")

    assert stat.S_IMODE(path.stat().st_mode) == 0o600


def test_save_qr_does_not_overwrite_by_default(tmp_path):
    path = tmp_path / "code.png"
    path.write_bytes(b"keep me")

    with pytest.raises(FileExistsError, match="overwrite=True"):
        save_qr("hello", path)

    assert path.read_bytes() == b"keep me"


def test_save_qr_overwrites_when_asked(tmp_path):
    path = tmp_path / "code.png"
    path.write_bytes(b"x" * 100_000)

    save_qr("hello", path, overwrite=True)

    data = path.read_bytes()
    assert data.startswith(PNG_SIGNATURE)
    # The old content is truncated, not left after the new one.
    assert len(data) < 100_000


@pytest.mark.parametrize("name", ["code.jpg", "code", "code.png.txt"])
def test_save_qr_rejects_an_unknown_extension(tmp_path, name):
    with pytest.raises(ValueError, match=r"\.png, \.svg"):
        save_qr("hello", tmp_path / name)

    assert os.listdir(tmp_path) == []


@pytest.mark.parametrize(
    ("kwargs", "match"),
    [({"scale": 0}, "scale"), ({"border": -1}, "border")],
)
def test_save_qr_rejects_invalid_sizes(tmp_path, kwargs, match):
    with pytest.raises(ValueError, match=match):
        save_qr("hello", tmp_path / "code.png", **kwargs)


def test_save_qr_writes_nothing_for_invalid_text(tmp_path):
    with pytest.raises(ValueError):
        save_qr("", tmp_path / "code.png")

    assert os.listdir(tmp_path) == []


# --- render_terminal ---------------------------------------------------------


def _modules(text, border=4):
    return [
        [bool(dark) for dark in row]
        for row in make_qr(text).matrix_iter(scale=1, border=border)
    ]


@pytest.mark.parametrize("border", [0, 1, 4])
def test_render_terminal_draws_two_rows_per_line(border):
    modules = _modules("hello", border)
    lines = render_terminal("hello", border=border).splitlines()

    assert len(lines) == (len(modules) + 1) // 2
    assert all(len(line) == len(modules[0]) for line in lines)


def test_render_terminal_draws_light_modules_by_default():
    modules = _modules("hello")
    first_line = render_terminal("hello").splitlines()[0]

    # The quiet zone is light, so it is drawn as full blocks.
    assert first_line == "█" * len(modules[0])


def test_render_terminal_invert_draws_dark_modules():
    normal = render_terminal("hello")
    inverted = render_terminal("hello", invert=True)
    swap = str.maketrans("█ ▀▄", " █▄▀")

    assert inverted == normal.translate(swap)


def test_render_terminal_matches_the_modules():
    modules = _modules("hello", border=0)
    lines = render_terminal("hello", border=0, invert=True).splitlines()

    for y, line in enumerate(lines):
        for x, char in enumerate(line):
            upper = modules[2 * y][x]
            lower = modules[2 * y + 1][x] if 2 * y + 1 < len(modules) else 0
            assert (
                char
                == {
                    (False, False): " ",
                    (True, False): "▀",
                    (False, True): "▄",
                    (True, True): "█",
                }[(upper, bool(lower))]
            )


def test_render_terminal_rejects_a_negative_border():
    with pytest.raises(ValueError, match="border"):
        render_terminal("hello", border=-1)
