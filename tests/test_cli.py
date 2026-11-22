"""Tests of the command line interface."""

from __future__ import annotations

import io
import subprocess
import sys

import pytest

from qrlocal import render_terminal
from qrlocal.__main__ import main

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


class _Stdin(io.StringIO):
    """A stdin replacement that can pretend to be a terminal."""

    def __init__(self, data: str = "", *, tty: bool = False) -> None:
        super().__init__(data)
        self._tty = tty

    def isatty(self) -> bool:
        return self._tty


@pytest.fixture
def stdin(monkeypatch):
    def set_stdin(data: str = "", *, tty: bool = False) -> None:
        monkeypatch.setattr(sys, "stdin", _Stdin(data, tty=tty))

    return set_stdin


def test_version(capsys):
    with pytest.raises(SystemExit) as excinfo:
        main(["--version"], prog="qrlocal")

    assert excinfo.value.code == 0
    assert capsys.readouterr().out.startswith("qrlocal: ")


def test_a_command_is_required(capsys):
    with pytest.raises(SystemExit) as excinfo:
        main([])

    assert excinfo.value.code == 2


def test_module_runs_as_a_script():
    result = subprocess.run(
        [sys.executable, "-m", "qrlocal", "encode", "hello"],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout == render_terminal("hello")


# --- encode ------------------------------------------------------------------


def test_encode_draws_in_the_terminal(capsys):
    assert main(["encode", "hello"]) == 0

    assert capsys.readouterr().out == render_terminal("hello")


def test_encode_passes_the_drawing_options(capsys):
    args = ["encode", "hello", "--error", "h", "--border", "1", "--invert"]

    assert main(args) == 0

    expected = render_terminal("hello", error="H", border=1, invert=True)
    assert capsys.readouterr().out == expected


@pytest.mark.parametrize(
    ("data", "text"),
    [
        ("secret\n", "secret"),
        ("secret\r\n", "secret"),
        ("secret", "secret"),
        ("two\nlines\n\n", "two\nlines\n"),
    ],
)
@pytest.mark.parametrize("args", [["encode"], ["encode", "-"]])
def test_encode_reads_stdin(capsys, stdin, args, data, text):
    stdin(data)

    assert main(args) == 0

    assert capsys.readouterr().out == render_terminal(text)


def test_encode_reads_stdin_for_dash_even_from_a_terminal(capsys, stdin):
    stdin("typed\n", tty=True)

    assert main(["encode", "-"]) == 0

    assert capsys.readouterr().out == render_terminal("typed")


def test_encode_without_text_on_a_terminal_explains(capsys, stdin):
    stdin(tty=True)

    assert main(["encode"], prog="qrlocal") == 1

    err = capsys.readouterr().err
    assert err.startswith("qrlocal: error: no text given")


def test_encode_writes_an_image(capsys, tmp_path):
    path = tmp_path / "code.png"

    assert main(["encode", "hello", "-o", str(path), "--scale", "3"]) == 0

    assert path.read_bytes().startswith(PNG_SIGNATURE)
    captured = capsys.readouterr()
    # stdout stays empty, so nothing but the image holds the text.
    assert captured.out == ""
    assert str(path) in captured.err


def test_encode_refuses_to_overwrite_without_force(capsys, tmp_path):
    path = tmp_path / "code.png"
    path.write_bytes(b"keep me")

    assert main(["encode", "hello", "-o", str(path)]) == 1

    assert path.read_bytes() == b"keep me"
    assert "--force" in capsys.readouterr().err


def test_encode_overwrites_with_force(tmp_path):
    path = tmp_path / "code.png"
    path.write_bytes(b"keep me")

    assert main(["encode", "hello", "-o", str(path), "--force"]) == 0

    assert path.read_bytes().startswith(PNG_SIGNATURE)


@pytest.mark.parametrize(
    ("args", "message"),
    [
        (["encode", ""], "empty"),
        (["encode", "a" * 3000, "--error", "H"], "too long"),
        (["encode", "hello", "-o", "code.jpg"], ".png, .svg"),
    ],
)
def test_encode_reports_errors(capsys, tmp_path, monkeypatch, args, message):
    monkeypatch.chdir(tmp_path)

    assert main(args) == 1

    assert message in capsys.readouterr().err


def test_encode_rejects_an_unknown_error_level(capsys):
    with pytest.raises(SystemExit) as excinfo:
        main(["encode", "hello", "--error", "X"])

    assert excinfo.value.code == 2
