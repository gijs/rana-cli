import json
import sys


def print_json(data, stream=sys.stdout):
    print(json.dumps(data, indent=2, ensure_ascii=False), file=stream)


def print_response(resp, exit_on_error: bool = True):
    """Print an API response as pretty JSON and exit non-zero on HTTP error."""
    if resp.status_code == 204 or not resp.content:
        print(f"HTTP {resp.status_code}")
    else:
        try:
            print_json(resp.json())
        except ValueError:
            print(resp.text)
    if exit_on_error and not resp.ok:
        sys.exit(1)


def print_table(rows, columns):
    """rows: list[dict], columns: list[(header, key_or_fn)]."""
    if not rows:
        print("(no results)")
        return

    def cell(row, key_or_fn):
        value = key_or_fn(row) if callable(key_or_fn) else row.get(key_or_fn, "")
        return "" if value is None else str(value)

    headers = [h for h, _ in columns]
    table = [[cell(row, k) for _, k in columns] for row in rows]
    widths = [max(len(headers[i]), *(len(r[i]) for r in table)) for i in range(len(headers))]

    def fmt_row(cells):
        return "  ".join(c.ljust(w) for c, w in zip(cells, widths))

    print(fmt_row(headers))
    print("  ".join("-" * w for w in widths))
    for row in table:
        print(fmt_row(row))
