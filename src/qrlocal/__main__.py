"""Command line interface: ``qrlocal encode`` / ``decode`` / ``scan``."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

from . import __version__
from ._decode import INSTALL_HINT, decode_image, scan_camera
from ._encode import ERROR_LEVELS, render_terminal, save_qr
from ._text import escape_control_chars

__all__ = ("entrypoint", "main")

_STDIN = "-"


class _Cancelled(Exception):
    """The user stopped the command."""


def _read_text(text: str | None) -> str:
    """Return the text to encode, reading stdin for ``-`` or no argument.

    Reading stdin keeps secrets out of the shell history and the process
    list. One trailing newline, as added by ``echo`` or a text file, is
    dropped.
    """
    if text is not None and text != _STDIN:
        return text
    if text is None and sys.stdin.isatty():
        raise ValueError(
            "no text given; pass TEXT, or pipe it in "
            "(e.g. `pbpaste | qrlocal encode`)."
        )
    data = sys.stdin.read()
    if data.endswith("\r\n"):
        return data[:-2]
    if data.endswith("\n"):
        return data[:-1]
    return data


def _run_encode(args: argparse.Namespace) -> None:
    text = _read_text(args.text)
    if args.output is None:
        sys.stdout.write(
            render_terminal(
                text, error=args.error, border=args.border, invert=args.invert
            )
        )
        return
    path = save_qr(
        text,
        args.output,
        scale=args.scale,
        border=args.border,
        error=args.error,
        overwrite=args.force,
    )
    print(f"wrote {path}", file=sys.stderr)


def _printable(text: str, raw: bool) -> str:
    # Decoded text comes from anyone; escape what could control the
    # terminal unless the user asks for the bytes as they are.
    return text if raw else escape_control_chars(text)


def _run_decode(args: argparse.Namespace) -> None:
    missing = []
    for path in args.images:
        texts = decode_image(path)
        if not texts:
            missing.append(path)
        prefix = f"{path}: " if len(args.images) > 1 else ""
        for text in texts:
            print(prefix + _printable(text, args.raw))
    if missing:
        raise ValueError(f"no QR code found in {', '.join(missing)}.")


def _run_scan(args: argparse.Namespace) -> None:
    stop = (
        "press q or Esc in the preview window"
        if args.preview
        else "press Ctrl+C"
    )
    print(
        f"Show a QR code to camera {args.device} ({stop} to stop).",
        file=sys.stderr,
    )
    text = scan_camera(
        device=args.device, timeout=args.timeout, preview=args.preview
    )
    if text is None:
        raise _Cancelled("stopped before a QR code was read.")
    print(_printable(text, args.raw))


def _add_raw_option(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--raw",
        action="store_true",
        help=(
            "print control characters as they are (by default they are "
            "escaped, so a crafted code cannot control the terminal)"
        ),
    )


def _build_parser(prog: str | None) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=prog,
        description="Generate and read QR codes locally, without network.",
    )
    parser.add_argument(
        "-v",
        "--version",
        action="version",
        help="show current version",
        version=f"%(prog)s: {__version__}",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    encode = subparsers.add_parser(
        "encode",
        help="turn text into a QR code",
        description=(
            "Turn text into a QR code. Without -o, draw it in the terminal. "
            "For secrets, pipe the text in instead of passing it as an "
            "argument, so it stays out of the shell history."
        ),
    )
    encode.add_argument(
        "text",
        nargs="?",
        metavar="TEXT",
        help="text to encode; '-' or omitted reads stdin",
    )
    encode.add_argument(
        "-o",
        "--output",
        metavar="FILE",
        help="write an image (.png or .svg) instead of drawing in terminal",
    )
    encode.add_argument(
        "-e",
        "--error",
        type=str.upper,
        choices=ERROR_LEVELS,
        default="M",
        help="error correction level (default: %(default)s)",
    )
    encode.add_argument(
        "-s",
        "--scale",
        type=int,
        default=10,
        help="pixels per module in the image (default: %(default)s)",
    )
    encode.add_argument(
        "-b",
        "--border",
        type=int,
        default=4,
        help="quiet zone width in modules (default: %(default)s)",
    )
    encode.add_argument(
        "-f",
        "--force",
        action="store_true",
        help="overwrite FILE if it exists",
    )
    encode.add_argument(
        "--invert",
        action="store_true",
        help="for a terminal with a light background",
    )
    encode.set_defaults(run=_run_encode)

    decode = subparsers.add_parser(
        "decode",
        help="read QR codes in image files",
        description=(
            "Print the text of the QR codes in image files. "
            f"Needs OpenCV: {INSTALL_HINT}"
        ),
    )
    decode.add_argument(
        "images", nargs="+", metavar="IMAGE", help="PNG, JPEG, BMP, ..."
    )
    _add_raw_option(decode)
    decode.set_defaults(run=_run_decode)

    scan = subparsers.add_parser(
        "scan",
        help="read a QR code with the camera",
        description=(
            "Print the text of the first QR code the camera sees. Frames "
            f"stay in memory and are never saved. Needs OpenCV: "
            f"{INSTALL_HINT}"
        ),
    )
    scan.add_argument(
        "-d",
        "--device",
        type=int,
        default=0,
        help="camera index (default: %(default)s)",
    )
    scan.add_argument(
        "-t",
        "--timeout",
        type=float,
        metavar="SECONDS",
        help="give up after this many seconds (default: wait forever)",
    )
    scan.add_argument(
        "--no-preview",
        dest="preview",
        action="store_false",
        help="do not open a window showing the camera",
    )
    _add_raw_option(scan)
    scan.set_defaults(run=_run_scan)
    return parser


def main(cli_args: Sequence[str], prog: str | None = None) -> int:
    """Run the command line interface.

    Parameters
    ----------
    cli_args : Sequence[str]
        Arguments without the program name.
    prog : str, optional
        Program name shown in messages.

    Returns
    -------
    int
        Exit status: 0 on success, 1 on an error with a message on stderr,
        130 when the user stops ``scan``.
    """
    parser = _build_parser(prog)
    args = parser.parse_args(cli_args)
    try:
        args.run(args)
    except (ValueError, OSError, ImportError, RuntimeError) as exc:
        print(f"{parser.prog}: error: {exc}", file=sys.stderr)
        return 1
    except (_Cancelled, KeyboardInterrupt):
        print(f"{parser.prog}: stopped", file=sys.stderr)
        return 130
    return 0


def entrypoint() -> None:
    sys.exit(main(sys.argv[1:]))


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:], prog="qrlocal"))
