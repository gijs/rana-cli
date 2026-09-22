"""Small Textual fuzzy-filter picker, shared by `projects pick` / `datasets pick`.

Type to filter, Up/Down to move the highlight, Enter to select, Esc to cancel.
"""
from textual.app import App, ComposeResult
from textual.widgets import Input, OptionList
from textual.widgets.option_list import Option


def _fuzzy_score(query, text):
    """None if `query` isn't a subsequence of `text` (case-insensitive), else a
    smaller-is-better score that favors an earlier, tighter match."""
    if not query:
        return 0
    text_lower = text.lower()
    pos = -1
    positions = []
    for ch in query.lower():
        pos = text_lower.find(ch, pos + 1)
        if pos == -1:
            return None
        positions.append(pos)
    return (positions[-1] - positions[0]) + positions[0]


class _PickerApp(App):
    CSS = """
    OptionList { height: 1fr; margin: 0 1; border: round $primary; }
    Input { margin: 0 1; }
    """

    def __init__(self, items, label_fn, id_fn):
        super().__init__()
        self.items = items
        self.label_fn = label_fn
        self.id_fn = id_fn
        self.filtered = []
        self.chosen = None

    def compose(self) -> ComposeResult:
        yield Input(placeholder="type to filter — Enter to select — Esc to cancel")
        yield OptionList()

    def on_mount(self) -> None:
        self._refresh_options("")
        self.query_one(Input).focus()

    def _refresh_options(self, query: str) -> None:
        scored = []
        for item in self.items:
            label = self.label_fn(item)
            score = _fuzzy_score(query, label)
            if score is not None:
                scored.append((score, item, label))
        scored.sort(key=lambda t: t[0])
        self.filtered = [item for _, item, _ in scored]

        options = self.query_one(OptionList)
        options.clear_options()
        for _, _item, label in scored:
            options.add_option(Option(label))
        if scored:
            options.highlighted = 0

    def on_input_changed(self, event: Input.Changed) -> None:
        self._refresh_options(event.value)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        options = self.query_one(OptionList)
        if options.highlighted is not None:
            self.chosen = self.filtered[options.highlighted]
        self.exit()

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        self.chosen = self.filtered[event.option_index]
        self.exit()

    def on_key(self, event) -> None:
        options = self.query_one(OptionList)
        if event.key == "up":
            event.stop()
            event.prevent_default()
            options.action_cursor_up()
        elif event.key == "down":
            event.stop()
            event.prevent_default()
            options.action_cursor_down()
        elif event.key == "escape":
            self.chosen = None
            self.exit()


def pick(items, label_fn, id_fn):
    """Launch an interactive fuzzy picker over `items`. Returns the chosen
    item's id (via id_fn), or None if the user cancelled or nothing matched."""
    app = _PickerApp(items, label_fn, id_fn)
    app.run()
    return None if app.chosen is None else id_fn(app.chosen)
