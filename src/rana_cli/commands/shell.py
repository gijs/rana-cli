def register(subparsers):
    p = subparsers.add_parser("shell", help="launch an interactive Textual command console")
    p.set_defaults(func=cmd_shell)


def cmd_shell(args):
    from ..tui import run
    run()
