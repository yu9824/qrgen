"""Tests of reading QR codes (needs OpenCV)."""

from __future__ import annotations

import io
import subprocess
import sys

import pytest
import segno

from qrlocal import decode_image, save_qr, scan_camera

cv2 = pytest.importorskip("cv2")
np = pytest.importorskip("numpy")


def _image(qr: segno.QRCode, scale: int = 8) -> np.ndarray:
    """Render a QR code as a BGR frame, as a camera gives it."""
    buffer = io.BytesIO()
    qr.save(buffer, kind="png", scale=scale, border=4)
    data = np.frombuffer(buffer.getvalue(), dtype=np.uint8)
    return cv2.imdecode(data, cv2.IMREAD_COLOR)


def _frame_of(text: str) -> np.ndarray:
    return _image(segno.make_qr(text, encoding="utf-8"))


BLANK = np.full((240, 320, 3), 255, dtype=np.uint8)

TEXTS = [
    "hello",
    "https://example.com/path?x=1&y=2",
    "WIFI:S:my net;T:WPA;P:p@ss;w0rd;;",
    "こんにちは世界",
    "café ✓ 日本語",
]


# --- decode_image ------------------------------------------------------------


@pytest.mark.parametrize("text", TEXTS)
def test_decode_image_reads_what_save_qr_wrote(tmp_path, text):
    path = save_qr(text, tmp_path / "code.png")

    assert decode_image(path) == [text]


def test_decode_image_reads_a_jpeg_with_a_non_ascii_path(tmp_path):
    path = tmp_path / "日本語のファイル.jpg"
    ok, data = cv2.imencode(".jpg", _frame_of("hello"))
    assert ok
    path.write_bytes(data.tobytes())

    assert decode_image(str(path)) == ["hello"]


def test_decode_image_reads_several_codes(tmp_path):
    first, second = _frame_of("first"), _frame_of("second")
    height = max(first.shape[0], second.shape[0])
    pad = [
        np.pad(
            image,
            ((0, height - image.shape[0]), (0, 0), (0, 0)),
            constant_values=255,
        )
        for image in (first, second)
    ]
    path = tmp_path / "two.png"
    cv2.imwrite(str(path), np.hstack(pad))

    assert sorted(decode_image(path)) == ["first", "second"]


@pytest.mark.parametrize(
    ("qr", "text"),
    [
        # Kanji mode holds Shift_JIS.
        (segno.make_qr("こんにちは", mode="kanji"), "こんにちは"),
        # Without an encoding, segno writes ISO 8859-1 when it fits.
        (segno.make_qr("café"), "café"),
    ],
    ids=["shift_jis", "latin-1"],
)
def test_decode_image_reads_payloads_that_are_not_utf8(tmp_path, qr, text):
    path = tmp_path / "code.png"
    qr.save(str(path), scale=8)

    assert decode_image(path) == [text]


def test_decode_image_returns_nothing_without_a_code(tmp_path):
    path = tmp_path / "blank.png"
    cv2.imwrite(str(path), BLANK)

    assert decode_image(path) == []


@pytest.mark.parametrize("content", [b"", b"not an image"])
def test_decode_image_rejects_a_file_that_is_not_an_image(tmp_path, content):
    path = tmp_path / "code.png"
    path.write_bytes(content)

    with pytest.raises(ValueError, match="not an image"):
        decode_image(path)


def test_decode_image_reports_a_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        decode_image(tmp_path / "missing.png")


# --- without OpenCV ----------------------------------------------------------


def test_importing_qrlocal_does_not_import_cv2():
    # A fresh interpreter, since this one has imported cv2 already.
    code = "import sys, qrlocal; print('cv2' in sys.modules)"
    result = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True
    )

    assert result.stdout.strip() == "False", result.stderr


@pytest.mark.parametrize(
    "call",
    [
        lambda path: decode_image(path),
        lambda path: scan_camera(preview=False),
    ],
    ids=["decode_image", "scan_camera"],
)
def test_without_opencv_raises_import_error(monkeypatch, tmp_path, call):
    # A None entry in sys.modules makes the package look missing.
    monkeypatch.setitem(sys.modules, "cv2", None)

    with pytest.raises(ImportError, match=r"qrlocal\[camera\]") as excinfo:
        call(tmp_path / "code.png")

    assert excinfo.value.name == "cv2"


# --- scan_camera -------------------------------------------------------------


class FakeCapture:
    """Stand-in for cv2.VideoCapture that plays a list of frames.

    After the list, it repeats the last frame, or reports a failed read when
    ``then_fail`` is set.
    """

    instances: list[FakeCapture] = []

    def __init__(self, frames, *, opened=True, then_fail=False):
        self.frames = list(frames)
        self.opened = opened
        self.then_fail = then_fail
        self.reads = 0
        self.released = False
        FakeCapture.instances.append(self)

    def isOpened(self):  # noqa: N802 (OpenCV's name)
        return self.opened

    def read(self):
        self.reads += 1
        if self.reads <= len(self.frames):
            return True, self.frames[self.reads - 1]
        if self.then_fail:
            return False, None
        return True, self.frames[-1]

    def release(self):
        self.released = True


@pytest.fixture
def camera(monkeypatch):
    """Replace the camera; call it with the frames it should give."""
    FakeCapture.instances = []
    devices = []

    def install(frames=(BLANK,), **kwargs):
        def make(device):
            devices.append(device)
            return FakeCapture(frames, **kwargs)

        monkeypatch.setattr(cv2, "VideoCapture", make)
        return devices

    return install


def _capture() -> FakeCapture:
    (capture,) = FakeCapture.instances
    return capture


def test_scan_camera_returns_the_first_code_it_reads(camera):
    devices = camera([BLANK, BLANK, _frame_of("こんにちは"), _frame_of("x")])

    assert scan_camera(device=2, preview=False) == "こんにちは"

    assert devices == [2]
    assert _capture().reads == 3
    assert _capture().released


def test_scan_camera_times_out_and_releases_the_camera(camera):
    camera([BLANK])

    with pytest.raises(TimeoutError, match="0.05 seconds"):
        scan_camera(timeout=0.05, preview=False)

    assert _capture().reads > 1
    assert _capture().released


@pytest.mark.parametrize("timeout", [0, -1])
def test_scan_camera_rejects_a_timeout_that_is_not_positive(camera, timeout):
    camera()

    with pytest.raises(ValueError, match="positive"):
        scan_camera(timeout=timeout, preview=False)

    assert FakeCapture.instances == []


@pytest.mark.parametrize(
    ("platform", "hint"),
    [
        ("darwin", "Privacy & Security > Camera"),
        ("win32", "Let desktop apps access your camera"),
        ("linux", "/dev/video3"),
    ],
)
def test_scan_camera_explains_how_to_allow_the_camera(
    camera, monkeypatch, platform, hint
):
    camera(opened=False)
    monkeypatch.setattr(sys, "platform", platform)

    with pytest.raises(RuntimeError, match="cannot open camera 3") as excinfo:
        scan_camera(device=3, preview=False)

    assert hint in str(excinfo.value)
    assert _capture().released


def test_scan_camera_reports_a_camera_that_stops(camera):
    camera([BLANK], then_fail=True)

    with pytest.raises(RuntimeError, match="stopped sending frames"):
        scan_camera(preview=False)

    assert _capture().released


def test_scan_camera_releases_the_camera_on_ctrl_c(camera, monkeypatch):
    camera([BLANK])

    def interrupt(frame):
        raise KeyboardInterrupt

    monkeypatch.setattr("qrlocal._decode._make_decoder", lambda cv2: interrupt)

    with pytest.raises(KeyboardInterrupt):
        scan_camera(preview=False)

    assert _capture().released


class FakeWindow:
    """Stand-in for the HighGUI functions used by the preview."""

    def __init__(self, keys=(), *, fail_to_open=False):
        self.keys = list(keys)
        self.fail_to_open = fail_to_open
        self.open = False
        self.shown = []
        self.destroyed = False

    def install(self, monkeypatch):
        for name in (
            "namedWindow",
            "imshow",
            "waitKey",
            "getWindowProperty",
            "destroyWindow",
        ):
            monkeypatch.setattr(cv2, name, getattr(self, name))

    def namedWindow(self, name):  # noqa: N802
        if self.fail_to_open:
            raise cv2.error("no display")
        self.open = True

    def imshow(self, name, frame):
        self.shown.append(frame)

    def waitKey(self, delay):  # noqa: N802
        return self.keys.pop(0) if self.keys else -1

    def getWindowProperty(self, name, prop):  # noqa: N802
        return 1.0 if self.open else -1.0

    def destroyWindow(self, name):  # noqa: N802
        self.open = False
        self.destroyed = True


@pytest.mark.parametrize("key", [ord("q"), 27])
def test_scan_camera_stops_when_the_user_presses_a_key(
    camera, monkeypatch, key
):
    camera([BLANK])
    window = FakeWindow(keys=[-1, key])
    window.install(monkeypatch)

    assert scan_camera() is None

    assert len(window.shown) == 2
    assert window.destroyed
    assert _capture().released


def test_scan_camera_stops_when_the_user_closes_the_window(
    camera, monkeypatch
):
    camera([BLANK])
    window = FakeWindow()
    window.install(monkeypatch)
    real_imshow = window.imshow

    def imshow_then_close(name, frame):
        real_imshow(name, frame)
        window.open = False

    monkeypatch.setattr(cv2, "imshow", imshow_then_close)

    assert scan_camera() is None
    assert _capture().released


def test_scan_camera_previews_a_mirrored_view(camera, monkeypatch):
    frame = BLANK.copy()
    frame[:, :10] = 0
    camera([frame])
    window = FakeWindow(keys=[ord("q")])
    window.install(monkeypatch)

    scan_camera()

    np.testing.assert_array_equal(window.shown[0], cv2.flip(frame, 1))


def test_scan_camera_explains_when_there_is_no_display(camera, monkeypatch):
    camera([BLANK])
    FakeWindow(fail_to_open=True).install(monkeypatch)

    with pytest.raises(RuntimeError, match="--no-preview"):
        scan_camera()

    assert _capture().released
