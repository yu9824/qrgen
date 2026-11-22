"""Command line interface: ``qrlocal encode``."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

from . import __version__
from ._encode import ERROR_LEVELS, render_terminal, save_qr

__all__ = ("entrypoint", "main")

_STDIN = "-"


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
        Exit status: 0 on success, 1 on an error with a message on stderr.
    """
    parser = _build_parser(prog)
    args = parser.parse_args(cli_args)
    try:
        args.run(args)
    except (ValueError, OSError) as exc:
        print(f"{parser.prog}: error: {exc}", file=sys.stderr)
        return 1
    return 0


def entrypoint() -> None:
    sys.exit(main(sys.argv[1:]))


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:], prog="qrlocal"))
