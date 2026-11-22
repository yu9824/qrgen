"""Generate and read QR codes locally, without network access.

Examples
--------
    >>> import qrlocal
    >>> qrlocal.save_qr("https://example.com", "example.png")
    >>> print(qrlocal.render_terminal("hello"))
    >>> qrlocal.decode_image("example.png")  # needs qrlocal[camera]
    ['https://example.com']

"""

from importlib.metadata import PackageNotFoundError, version

# バージョンは setuptools-scm が git タグから決め、インストール時に
# メタデータへ書き込まれる。そこから読むので、インストールせずに
# src を直接 import したときは "unknown" になる。
try:
    __version__ = version("qrlocal")
except PackageNotFoundError:
    __version__ = "unknown"

__license__ = "MIT"
__author__ = "yu9824"
__copyright__ = "Copyright © 2026 yu9824"

from ._decode import decode_image, scan_camera
from ._encode import ErrorLevel, make_qr, render_terminal, save_qr
from ._text import escape_control_chars

__all__ = (
    "ErrorLevel",
    "decode_image",
    "escape_control_chars",
    "make_qr",
    "render_terminal",
    "save_qr",
    "scan_camera",
)
