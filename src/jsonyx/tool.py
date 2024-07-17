#!/usr/bin/env python
# Copyright (C) 2024 Nice Zombies
"""JSON tool."""
from __future__ import annotations

__all__: list[str] = ["JSONNamespace", "register", "run"]

import sys
from argparse import ArgumentParser
from pathlib import Path
from sys import stdin

from jsonyx import (
    EVERYTHING, NAN, JSONSyntaxError, dumps, format_syntax_error, loads,
)
from typing_extensions import Any  # type: ignore


class JSONNamespace:  # pylint: disable=R0903
    """JSON namespace."""

    compact: bool
    ensure_ascii: bool
    indent: int | str | None
    filename: str | None
    nonstrict: bool


def register(parser: ArgumentParser) -> None:
    """Register JSON tool."""
    parser.add_argument("filename", nargs="?")
    parser.add_argument("--compact", action="store_true")
    parser.add_argument("--ensure-ascii", action="store_true")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--indent", type=int, metavar="SPACES")
    group.add_argument(
        "--indent-tab", action="store_const", const="\t", dest="indent",
    )
    parser.add_argument("--nonstrict", action="store_true")


def run(args: JSONNamespace) -> None:
    """Run JSON tool."""
    s: bytes | str
    if args.filename:
        filename: str = args.filename
        s = Path(filename).read_bytes()
    elif stdin.isatty():
        filename, s = "<stdin>", "\n".join(iter(input, ""))
    else:
        filename, s = "<stdin>", stdin.buffer.read()

    try:
        obj: Any = loads(
            s,
            allow=EVERYTHING if args.nonstrict else [],
            filename=filename,
        )
    except JSONSyntaxError as exc:
        raise SystemExit(format_syntax_error(exc)) from None

    print(dumps(
        obj,
        allow=NAN if args.nonstrict else [],
        ensure_ascii=args.ensure_ascii,
        indent=args.indent,
        item_separator="," if args.compact else ", ",
        key_separator=":" if args.compact else ": ",
    ))


def _main() -> None:
    parser: ArgumentParser = ArgumentParser()
    register(parser)
    try:
        run(parser.parse_args(namespace=JSONNamespace()))
    except BrokenPipeError as exc:
        sys.exit(exc.errno)


if __name__ == "__main__":
    _main()
