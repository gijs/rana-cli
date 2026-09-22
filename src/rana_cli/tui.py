"""Interactive Textual shell for rana-cli.

A single-screen command console: commands are typed the same way as on the
regular command line (minus the leading `rana`), dispatched through the
exact same argparse parser/handlers as the non-interactive CLI, and their
output is captured into a scrollback log. Auth/config already persist to
disk between invocations (see config.py/auth.py), so nothing special is
needed to carry state across commands here.
"""
import contextlib
import io
import shlex
import traceback

from textual import work
from textual.app import App, ComposeResult
from textual.widgets import Footer, Header, Input, RichLog

from .cli import build_parser

LOCAL_COMMANDS = {"exit", "quit", "clear"}


class RanaShellApp(App):
    """Type CLI commands (without the `rana` prefix) at the prompt."""

    CSS = """
    RichLog {
        border: round $primary;
        margin: 0 1;
        background: $surface;
    }
    Input {
        margin: 0 1 1 1;
    }
    """

    BINDINGS = [("ctrl+l", "clear_log", "Clear")]

    def __init__(self):
        super().__init__()
        self.parser = build_parser()
        self.history: list[str] = []
        self.history_pos: int | None = None

    def compose(self) -> ComposeResult:
        yield Header()
        yield RichLog(id="log", wrap=True, markup=True, highlight=False)
        yield Input(placeholder="e.g. 'projects ls'  —  'help' for commands  —  'exit' to quit", id="cmd-input")
        yield Footer()

    def on_mount(self) -> None:
        self.title = "rana shell"
        log = self.query_one("#log", RichLog)
        log.write("[b]Rana interactive shell.[/b] Type a command exactly as you would after `rana`, e.g.:")
        log.write("  projects ls")
        log.write("  files ls --project <id>")
        log.write("Type 'help' for the full command list, 'clear' to clear this log, 'exit' to quit.")
        self.query_one(Input).focus()

    def action_clear_log(self) -> None:
        self.query_one("#log", RichLog).clear()

    def on_key(self, event) -> None:
        input_widget = self.query_one("#cmd-input", Input)
        if self.focused is not input_widget or not self.history:
            return
        if event.key == "up":
            event.stop()
            event.prevent_default()
            self._navigate_history(-1)
        elif event.key == "down":
            event.stop()
            event.prevent_default()
            self._navigate_history(1)

    def _navigate_history(self, step: int) -> None:
        if self.history_pos is None:
            self.history_pos = len(self.history)
        self.history_pos = max(0, min(len(self.history), self.history_pos + step))
        input_widget = self.query_one("#cmd-input", Input)
        if self.history_pos == len(self.history):
            input_widget.value = ""
        else:
            input_widget.value = self.history[self.history_pos]
        input_widget.cursor_position = len(input_widget.value)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        text = event.value.strip()
        event.input.value = ""
        self.history_pos = None
        if not text:
            return
        if not self.history or self.history[-1] != text:
            self.history.append(text)

        log = self.query_one("#log", RichLog)
        log.write(f"[b]$[/b] {text}")

        if text in ("exit", "quit"):
            self.exit()
            return
        if text == "clear":
            log.clear()
            return

        tokens = ["--help"] if text == "help" else self._tokenize(text)
        if tokens is None:
            return

        event.input.disabled = True
        self.run_command(tokens)

    def _tokenize(self, text: str) -> list[str] | None:
        try:
            return shlex.split(text)
        except ValueError as exc:
            self.query_one("#log", RichLog).write(f"[red]Parse error: {exc}[/red]")
            return None

    @work(thread=True)
    def run_command(self, tokens: list[str]) -> None:
        output, exit_code = self._execute(tokens)
        self.call_from_thread(self._show_result, output, exit_code)

    def _execute(self, tokens: list[str]) -> tuple[str, int]:
        buf = io.StringIO()
        exit_code = 0
        try:
            with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
                try:
                    args = self.parser.parse_args(tokens)
                except SystemExit as exc:
                    exit_code = exc.code or 0
                else:
                    try:
                        args.func(args)
                    except SystemExit as exc:
                        exit_code = exc.code or 0
        except Exception:
            buf.write(traceback.format_exc())
            exit_code = 1
        return buf.getvalue(), exit_code

    def _show_result(self, output: str, exit_code: int) -> None:
        log = self.query_one("#log", RichLog)
        if output:
            log.write(output.rstrip("\n"))
        if exit_code:
            log.write(f"[red](exit code {exit_code})[/red]")
        input_widget = self.query_one("#cmd-input", Input)
        input_widget.disabled = False
        input_widget.focus()


def run():
    RanaShellApp().run()
