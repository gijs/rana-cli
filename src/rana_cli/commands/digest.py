"""`rana digest run` — a scriptable summary of recent failed jobs, unresolved
publication comments, and pending invitations. Meant to be cron'd/CI'd and
piped into whatever notification tool you like (mail, Slack, etc); an
optional --slack-webhook posts directly to a Slack incoming webhook (no
OAuth needed).
"""
import os
import re
import sys
from datetime import datetime, timedelta, timezone

import requests

from ..output import print_json
from ._shared import add_env_tenant_args, get_client, paginate_all

FAILED_JOB_STATES = {"failed", "crashed"}
_DURATION_RE = re.compile(r"^(\d+)([hd])$")


def register(subparsers):
    p = subparsers.add_parser("digest", help="summarize recent activity across jobs/comments/invitations")
    sub = p.add_subparsers(dest="digest_command", required=True)

    p_run = sub.add_parser("run", help="generate (and optionally Slack-post) a digest")
    add_env_tenant_args(p_run)
    p_run.add_argument("--since", default="24h", help="lookback window, e.g. 24h or 7d (default: 24h)")
    p_run.add_argument("--project", dest="project_id", default=None,
                        help="scope jobs/publications to one project")
    p_run.add_argument("--format", choices=["text", "json"], default="text")
    p_run.add_argument("--slack-webhook", default=os.environ.get("RANA_SLACK_WEBHOOK"),
                        help="Slack incoming-webhook URL to post the digest to (default: $RANA_SLACK_WEBHOOK)")
    p_run.add_argument("--max-publications", type=int, default=50,
                        help="cap on how many publications to check for unresolved comments "
                             "(there's no cross-publication comment search, so this is one API "
                             "call per publication)")
    p_run.set_defaults(func=cmd_run)


def _parse_since(spec):
    m = _DURATION_RE.match(spec.strip())
    if not m:
        raise SystemExit(f"--since must look like '24h' or '7d', got {spec!r}")
    n, unit = int(m.group(1)), m.group(2)
    delta = timedelta(hours=n) if unit == "h" else timedelta(days=n)
    return datetime.now(timezone.utc) - delta


def _parse_dt(value):
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _failed_jobs(client, project_id, since):
    query = {"project_id": project_id} if project_id else {}
    jobs = []
    for job in paginate_all(client, "/tenants/{tenant_id}/jobs", query):
        if job.get("state", {}).get("type") not in FAILED_JOB_STATES:
            continue
        finished_at = _parse_dt(job.get("finished_at"))
        if finished_at and finished_at < since:
            continue
        jobs.append(job)
    return jobs


def _unresolved_comments(client, project_id, max_publications):
    pub_query = {"project_id": project_id} if project_id else {}
    sections = []
    truncated = False
    checked = 0
    for pub in paginate_all(client, "/tenants/{tenant_id}/publications", pub_query):
        if checked >= max_publications:
            truncated = True
            break
        checked += 1
        pub_id = pub.get("id")
        resp = client.get(f"/tenants/{{tenant_id}}/publications/{pub_id}/comments",
                           query={"resolved": "false"})
        if not resp.ok:
            continue
        items = resp.json().get("items", [])
        if not items:
            continue
        previews = []
        for comment in items[:3]:
            messages = comment.get("messages") or []
            body = messages[0].get("body", "") if messages else ""
            previews.append(body[:80])
        sections.append({
            "publication_id": pub_id, "publication_name": pub.get("name"),
            "count": len(items), "previews": previews,
        })
    return sections, truncated


def _pending_invitations(client):
    resp = client.get("/tenants/{tenant_id}/invitations")
    if not resp.ok:
        return None
    body = resp.json()
    items = body.get("items", []) if isinstance(body, dict) else body
    # Best-effort: reports whatever `list` returns as-is. The exact
    # pending-vs-accepted status field wasn't confirmed against a live
    # response — adjust this filter once you can see real invitation objects.
    return len(items) if isinstance(items, list) else None


def _format_text(digest):
    lines = [f"Rana digest since {digest['since']}", ""]

    jobs = digest["failed_jobs"]
    lines.append(f"Failed/crashed jobs ({len(jobs)}):")
    if jobs:
        for j in jobs:
            lines.append(f"  - {j['name']} ({j['id']}) [{j['state']}] finished {j['finished_at']}")
    else:
        lines.append("  none")
    lines.append("")

    sections = digest["unresolved_comments"]
    total_unresolved = sum(s["count"] for s in sections)
    suffix = ", truncated" if digest["unresolved_comments_truncated"] else ""
    lines.append(f"Unresolved comments ({total_unresolved} across {len(sections)} publication(s){suffix}):")
    if sections:
        for s in sections:
            lines.append(f"  - {s['publication_name']} ({s['publication_id']}): {s['count']} unresolved")
            for preview in s["previews"]:
                lines.append(f'      "{preview}"')
    else:
        lines.append("  none")
    lines.append("")

    pending = digest["pending_invitations"]
    lines.append(f"Pending invitations: {pending if pending is not None else 'unknown'}")
    return "\n".join(lines)


def cmd_run(args):
    client = get_client(args)
    since = _parse_since(args.since)

    failed_jobs = _failed_jobs(client, args.project_id, since)
    comment_sections, truncated = _unresolved_comments(client, args.project_id, args.max_publications)
    pending_invitations = _pending_invitations(client)

    digest = {
        "since": since.isoformat(),
        "failed_jobs": [{"id": j.get("id"), "name": j.get("name"),
                          "state": j.get("state", {}).get("type"), "finished_at": j.get("finished_at")}
                         for j in failed_jobs],
        "unresolved_comments": comment_sections,
        "unresolved_comments_truncated": truncated,
        "pending_invitations": pending_invitations,
    }
    text = _format_text(digest)

    if args.format == "json":
        print_json(digest)
    else:
        print(text)

    if args.slack_webhook:
        try:
            resp = requests.post(args.slack_webhook, json={"text": text}, timeout=10)
            if not resp.ok:
                print(f"warning: Slack post failed: HTTP {resp.status_code}", file=sys.stderr)
        except requests.RequestException as exc:
            print(f"warning: Slack post failed: {exc}", file=sys.stderr)
