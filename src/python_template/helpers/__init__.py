"""Small helpers used inside the package.

- ``is_installed``: check whether an optional dependency is importable
- ``is_argument``: check whether a callable accepts an argument

Examples
--------
    >>> from python_template.helpers import is_installed
    >>> if is_installed("cv2"):
    ...     import cv2

"""

from ._helpers import is_argument, is_installed

# _helpers.pyだと、_が入っているのでドキュメント化されない。
# ドキュメント化したい場合は、モジュールメソッドとして登録するため、
# __all__に入れる。
__all__ = ("is_argument", "is_installed")
