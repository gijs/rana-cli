import argparse
import sys

from . import __version__
from .commands import register_all


def build_parser():
    parser = argparse.ArgumentParser(
        prog="rana",
        description="Command-line interface for the Rana water management platform API.",
    )
    parser.add_argument("--version", action="version", version=f"rana-cli {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)
    register_all(subparsers)
    return parser


def main(argv=None):
    parser = build_parser()

    try:
        import argcomplete
        argcomplete.autocomplete(parser)
    except ImportError:
        pass

    args = parser.parse_args(argv)
    try:
        args.func(args)
    except KeyboardInterrupt:
        print("\nAborted.", file=sys.stderr)
        sys.exit(130)


if __name__ == "__main__":
    main()
