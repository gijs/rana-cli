# rana-cli

A command-line interface for the [Rana](https://www.ranawaterintelligence.com/)
water-management platform API. It authenticates with OAuth2
(authorizationCode + PKCE) and gives you typed subcommands for the most
common resources (projects, datasets, publications, files, jobs,
invitations, users, tenants), plus a generic `rana call` escape hatch for
anything else in the ~130-operation API.

## Install

```bash
pip install -e .
```

Requires Python 3.9+. This installs a `rana` command on your `PATH`.

## Authenticate

The default environment (`test`) points at the Rana test environment
(`test.ranawaterintelligence.com`, tenant `nenstest`). Its OAuth2 client is
registered with a redirect URI that lands on the API's Swagger docs page,
not on a port this CLI controls, so login is a two-step handoff:

```bash
rana auth login
# 1. Open the printed URL, log in with your Rana account.
# 2. Copy the full URL you land on afterwards (it has ?code=...&state=... in it).
rana auth exchange --url 'https://test.ranawaterintelligence.com/v1-alpha/docs/oauth2-redirect?code=...&state=...'
```

Tokens are cached at `~/.config/rana-cli/tokens.json` (override the
directory with `$RANA_CLI_STATE_DIR`) and refreshed automatically when they
expire. Check status any time with:

```bash
rana auth status     # cached-token info, no API call
rana auth whoami      # calls the API and lists a few projects
rana auth logout
```

If you register your own OAuth2 client with a `redirect_uri` of
`http://localhost:<port>/...` (e.g. for a custom or production environment),
`rana auth login` detects that automatically and captures the code itself —
no `exchange` step needed.

## Usage

```bash
rana projects list
rana projects get <project_id>
rana projects create --code demo --name "Demo project"

rana datasets list -q "rainfall"
rana datasets get <dataset_id>

rana publications list
rana publications comments list <publication_id>

rana files ls --project <project_id> --path some/dir
rana files upload ./report.pdf --project <project_id> --dest reports/report.pdf
rana files download report.pdf --project <project_id> --save-to ./report.pdf

rana jobs get <job_id>
rana jobs logs <job_id>

rana invitations create --email someone@example.com --tenant-role guest

rana users list
```

Every subcommand supports `--env` and `--tenant` to target a different
environment/tenant than the default. Run `rana <command> --help` or
`rana <command> <subcommand> --help` to see all options.

### Automation, ops & workflow commands

```bash
# Bulk-upload a local directory tree, or mirror it to a project's file tree
rana files upload-tree ./output --project <project_id> --dest results/
rana files sync ./output --project <project_id> --dest results/ --dry-run
rana files sync ./output --project <project_id> --dest results/ --delete   # prompts before deleting

# Invite a batch of people from a CSV (columns: email, tenant_role, project, project_role)
rana invitations bulk-create ./team.csv --dry-run
rana invitations bulk-create ./team.csv

# Poll a job to completion — exits 0/1/2 (success/failure/timeout), for use in CI
rana jobs watch <job_id> --timeout 1800

# Publish a new publication version after a job finishes
rana jobs watch <job_id> && \
  rana publications versions create <publication_id> --version 3 \
    --file results/map.tif --file results/report.pdf

# A pipeable/Slack-able digest of failed jobs, unresolved comments, pending invitations
rana digest run --since 24h
rana digest run --since 24h --format json | jq .
rana digest run --slack-webhook "$SLACK_WEBHOOK_URL"   # or set $RANA_SLACK_WEBHOOK

# Comments as a review queue
rana publications comments list <publication_id> --unresolved
rana publications comments reply <publication_id> <comment_id> --body "Looks good, thanks!"
rana publications comments resolve <publication_id> <comment_id>

# Fuzzy-pick a project/dataset instead of typing its id
rana files ls --project $(rana projects pick) --path some/dir
```

`rana shell` launches an interactive Textual command console — type any of
the commands above without the leading `rana`, with history and a
scrollback log.

### Shell completion

```bash
# bash (~/.bashrc) or zsh (~/.zshrc, after `autoload -U +X compinit && compinit`)
eval "$(register-python-argcomplete rana)"
```

Gives you subcommand/flag completion everywhere, plus live completion of
project/dataset/publication ids (e.g. `rana files ls --project <TAB>`) —
backed by a short-lived local cache so it doesn't hit the API on every
keystroke, and fails silently (no completions) if the API is slow or
unreachable rather than hanging your shell.

### The `call` escape hatch

Not every one of the ~130 API operations has a dedicated subcommand. For
anything else:

```bash
rana call GET /tenants/{tenant_id}/datasets --query limit=5
rana call POST /tenants/{tenant_id}/datasets --json '{"identifier": "...", ...}'
```

`{tenant_id}` is substituted automatically; fill in any other
`{placeholder}` (e.g. `{project_id}`) yourself before passing the path. See
the live OpenAPI docs at `<api_base_url>/docs` for exact request/response
shapes, or browse `references/` if you're working from the companion
`rana-api` skill this CLI was based on.

## Multiple environments

Add a `prod` (or any other name) block to `~/.config/rana-cli/config.json`
once you have a registered OAuth2 client for it:

```json
{
  "prod": {
    "api_base_url": "https://ranawaterintelligence.com/v1-alpha",
    "default_tenant_id": "your-tenant",
    "client_id": "...",
    "authorization_url": "https://auth.lizard.net/oauth2/authorize",
    "token_url": "https://auth.lizard.net/oauth2/token",
    "redirect_uri": "http://localhost:8765/callback"
  }
}
```

Then use it with `rana --env prod ...` or `export RANA_ENV=prod`. Any field
can also be overridden per-call with an environment variable
(`RANA_API_BASE_URL`, `RANA_TENANT_ID`, `RANA_CLIENT_ID`, `RANA_AUTH_URL`,
`RANA_TOKEN_URL`, `RANA_REDIRECT_URI`).

```bash
rana config show --env prod
rana config environments
rana config path
```

## Development

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -e .
rana --help
```

The code is organized as:

- `src/rana_cli/config.py` — environment/config resolution
- `src/rana_cli/auth.py` — PKCE login flow, token cache, refresh
- `src/rana_cli/client.py` — thin authenticated HTTP wrapper
- `src/rana_cli/commands/` — one module per resource, each registering its
  own argparse subparsers
