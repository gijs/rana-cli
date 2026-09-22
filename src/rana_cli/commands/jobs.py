import sys
import time

from ..output import print_json
from ._shared import add_env_tenant_args, add_pagination_args, emit, get_client, pagination_query

# JobStatus values that mean "still going" — keep polling.
IN_PROGRESS = {"scheduled", "pending", "running", "cancelling", "paused"}
TERMINAL_OK = {"completed"}
# Anything terminal not in TERMINAL_OK (failed/crashed/cancelled) is a failure exit.

LOG_LEVEL_NAMES = {10: "DEBUG", 20: "INFO", 30: "WARNING", 40: "ERROR", 50: "CRITICAL"}


def register(subparsers):
    p = subparsers.add_parser("jobs", help="inspect async jobs")
    sub = p.add_subparsers(dest="jobs_command", required=True)

    p_list = sub.add_parser("list", help="list jobs")
    add_env_tenant_args(p_list)
    add_pagination_args(p_list)
    p_list.set_defaults(func=cmd_list)

    p_get = sub.add_parser("get", help="show a job")
    add_env_tenant_args(p_get)
    p_get.add_argument("job_id")
    p_get.set_defaults(func=cmd_get)

    p_logs = sub.add_parser("logs", help="show job logs")
    add_env_tenant_args(p_logs)
    p_logs.add_argument("job_id")
    p_logs.set_defaults(func=cmd_logs)

    p_results = sub.add_parser("results", help="show job results")
    add_env_tenant_args(p_results)
    p_results.add_argument("job_id")
    p_results.set_defaults(func=cmd_results)

    p_watch = sub.add_parser("watch", help="poll a job until it finishes, streaming status and logs")
    add_env_tenant_args(p_watch)
    p_watch.add_argument("job_id")
    p_watch.add_argument("--interval", type=float, default=3.0, help="seconds between polls")
    p_watch.add_argument("--no-logs", action="store_true", help="don't tail job logs while polling")
    p_watch.add_argument("--timeout", type=float, default=None,
                          help="give up (exit code 2) after this many seconds")
    p_watch.set_defaults(func=cmd_watch)


def cmd_list(args):
    client = get_client(args)
    emit(client.get("/tenants/{tenant_id}/jobs", query=pagination_query(args)))


def cmd_get(args):
    client = get_client(args)
    emit(client.get(f"/tenants/{{tenant_id}}/jobs/{args.job_id}"))


def cmd_logs(args):
    client = get_client(args)
    emit(client.get(f"/tenants/{{tenant_id}}/jobs/{args.job_id}/logs"))


def cmd_results(args):
    client = get_client(args)
    emit(client.get(f"/tenants/{{tenant_id}}/jobs/{args.job_id}/results"))


def cmd_watch(args):
    client = get_client(args)
    base = f"/tenants/{{tenant_id}}/jobs/{args.job_id}"
    started = time.monotonic()
    last_status_line = None
    logs_shown = 0

    while True:
        resp = client.get(base)
        if not resp.ok:
            emit(resp)
            return

        job = resp.json()
        state = job["state"]

        if not args.no_logs:
            logs_resp = client.get(f"{base}/logs")
            if logs_resp.ok:
                # This endpoint has no pagination/since param — it always returns the
                # full log list, so only print what's new since the last poll.
                items = logs_resp.json().get("items", [])
                for entry in items[logs_shown:]:
                    level = LOG_LEVEL_NAMES.get(entry.get("log_level"), entry.get("log_level"))
                    print(f"[{level}] {entry.get('message')}")
                logs_shown = len(items)

        status_line = f"status={state['type']} progress={state.get('progress', 0):.0%}"
        if state.get("message"):
            status_line += f" — {state['message']}"
        if status_line != last_status_line:
            print(status_line)
            last_status_line = status_line

        if state["type"] not in IN_PROGRESS:
            print_json(job)
            sys.exit(0 if state["type"] in TERMINAL_OK else 1)

        if args.timeout is not None and time.monotonic() - started > args.timeout:
            print(f"Timed out after {args.timeout}s waiting for job {args.job_id}", file=sys.stderr)
            sys.exit(2)

        time.sleep(args.interval)
