"""Tests of the command line interface."""

from __future__ import annotations

import io
import subprocess
import sys

import pytest

from qrlocal import render_terminal, save_qr
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


# --- decode ------------------------------------------------------------------


@pytest.fixture
def opencv():
    return pytest.importorskip("cv2")


def test_decode_prints_the_text(capsys, tmp_path, opencv):
    path = save_qr("こんにちは", tmp_path / "code.png")

    assert main(["decode", str(path)]) == 0

    assert capsys.readouterr().out == "こんにちは\n"


def test_decode_prefixes_the_path_for_several_images(capsys, tmp_path, opencv):
    first = save_qr("one", tmp_path / "1.png")
    second = save_qr("two", tmp_path / "2.png")

    assert main(["decode", str(first), str(second)]) == 0

    assert capsys.readouterr().out == f"{first}: one\n{second}: two\n"


def test_decode_escapes_control_characters(capsys, tmp_path, opencv):
    path = save_qr("hi\x1b[2J\u202e", tmp_path / "code.png")

    assert main(["decode", str(path)]) == 0

    assert capsys.readouterr().out == "hi\\x1b[2J\\u202e\n"


def test_decode_raw_prints_control_characters(capsys, tmp_path, opencv):
    path = save_qr("hi\x1b[2J", tmp_path / "code.png")

    assert main(["decode", "--raw", str(path)]) == 0

    assert capsys.readouterr().out == "hi\x1b[2J\n"


def test_decode_reports_images_without_a_code(capsys, tmp_path, opencv):
    found = save_qr("one", tmp_path / "1.png")
    blank = tmp_path / "blank.png"
    opencv.imwrite(str(blank), opencv.imread(str(found)) * 0 + 255)

    assert main(["decode", str(found), str(blank)]) == 1

    captured = capsys.readouterr()
    assert captured.out == f"{found}: one\n"
    assert f"no QR code found in {blank}" in captured.err


def test_decode_reports_a_missing_file(capsys, tmp_path, opencv):
    assert main(["decode", str(tmp_path / "missing.png")]) == 1

    assert "missing.png" in capsys.readouterr().err


def test_decode_without_opencv_tells_how_to_install(capsys, monkeypatch):
    monkeypatch.setitem(sys.modules, "cv2", None)

    assert main(["decode", "code.png"]) == 1

    assert 'pip install "qrlocal[camera]"' in capsys.readouterr().err


# --- scan --------------------------------------------------------------------


@pytest.fixture
def fake_scan(monkeypatch):
    """Replace scan_camera; set the result and read back the arguments."""
    calls = []

    def install(result):
        def scan(**kwargs):
            calls.append(kwargs)
            if isinstance(result, BaseException):
                raise result
            return result

        monkeypatch.setattr("qrlocal.__main__.scan_camera", scan)
        return calls

    return install


def test_scan_prints_the_text(capsys, fake_scan):
    calls = fake_scan("hello")

    assert main(["scan"]) == 0

    assert calls == [{"device": 0, "timeout": None, "preview": True}]
    captured = capsys.readouterr()
    assert captured.out == "hello\n"
    assert "q or Esc" in captured.err


def test_scan_passes_the_options(capsys, fake_scan):
    calls = fake_scan("hello")

    args = ["scan", "-d", "1", "-t", "2.5", "--no-preview"]
    assert main(args) == 0

    assert calls == [{"device": 1, "timeout": 2.5, "preview": False}]
    assert "Ctrl+C" in capsys.readouterr().err


@pytest.mark.parametrize(
    ("args", "out"),
    [(["scan"], "a\\x07b\n"), (["scan", "--raw"], "a\x07b\n")],
)
def test_scan_escapes_control_characters(capsys, fake_scan, args, out):
    fake_scan("a\x07b")

    assert main(args) == 0

    assert capsys.readouterr().out == out


@pytest.mark.parametrize("result", [None, KeyboardInterrupt()])
def test_scan_stopped_by_the_user_exits_with_130(capsys, fake_scan, result):
    fake_scan(result)

    assert main(["scan"], prog="qrlocal") == 130

    captured = capsys.readouterr()
    assert captured.out == ""
    assert "qrlocal: stopped" in captured.err


@pytest.mark.parametrize(
    "error",
    [
        TimeoutError("no QR code read"),
        RuntimeError("cannot open camera 0"),
        ImportError("requires OpenCV"),
    ],
)
def test_scan_reports_errors(capsys, fake_scan, error):
    fake_scan(error)

    assert main(["scan"], prog="qrlocal") == 1

    # The last line, after the prompt to show a code.
    err = capsys.readouterr().err
    assert err.splitlines()[-1] == f"qrlocal: error: {error}"
