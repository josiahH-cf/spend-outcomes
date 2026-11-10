# Cherry Meter

Measure the Codex tokens observed for one project on WSL, compare them with an
advisory seven-day target, and track separately what you say has happened toward
the project’s outcome. Everything runs locally. Usage never blocks work and never
marks an outcome checkpoint for you.

Previously called Spend & Outcomes. The `spend-outcomes.pyz` download name,
`spend_outcomes` Python module, repository URL, and existing config/state paths
remain compatible. Keep using your current config and saved reports; no data
migration is required. Version 1.0.1 updates the name in newly generated reports.

## Set up with an AI assistant

Download these three files from the same versioned GitHub release:

- `spend-outcomes.pyz`
- `SHA256SUMS`
- `CUSTOMER_SETUP_PROMPT.md`

Verify the checksum, then paste the complete contents of
`CUSTOMER_SETUP_PROMPT.md` into Codex, Claude Code, or another assistant that can
run shell commands on your WSL machine. The prompt makes the assistant show the
proposed settings and ask before writing them. A chat-only assistant can walk you
through the manual commands below but cannot run them for you.

Requirements: WSL, Python 3.10 or newer, a Codex project workspace, and an
explicitly permitted local Codex JSONL root. Cherry Meter does not require an
orchestration service, Agent Telemetry, a provider API key, or a background service.

## Manual setup

First verify the exact files you downloaded:

```sh
sha256sum -c SHA256SUMS
python3 spend-outcomes.pyz --version
```

Choose private paths outside the project repository. Replace every example value
before running this command:

```sh
mkdir -p "$HOME/.config/spend-outcomes" "$HOME/.local/state/spend-outcomes/my-project"
python3 spend-outcomes.pyz init \
  --config "$HOME/.config/spend-outcomes/my-project.json" \
  --project my-project \
  --name "My project" \
  --workspace /absolute/path/to/my-project \
  --codex-root "$HOME/.codex/sessions" \
  --state "$HOME/.local/state/spend-outcomes/my-project" \
  --target-tokens 100000 \
  --outcome "A useful result in plain language" \
  --success-criterion "The evidence I will use to call it successful" \
  --checkpoint first-review="Review the first report"
```

`init` creates only the private config and prints an `inspect_argv`; it does not
read logs. Review the config, run that printed command, and open the returned HTML
path in a browser. To refresh, use the refresh command shown inside the report.
Opening an old HTML report never refreshes it.

After you actually complete a checkpoint, record that fact explicitly:

```sh
python3 spend-outcomes.pyz checkpoint \
  --config "$HOME/.config/spend-outcomes/my-project.json" \
  --project my-project --id first-review --status complete \
  --actor operator --note "Reviewed on WSL"
```

Run `inspect` again for a new immutable report. The previous JSON and HTML remain
readable. Checkpoint progress is labelled operator-reported and is not inferred
from tokens, activity, a test result, or an assistant verdict.

Adjust the advisory target or outcome definition explicitly, then inspect again:

```sh
python3 spend-outcomes.pyz target --config "$HOME/.config/spend-outcomes/my-project.json" \
  --project my-project --tokens 120000 --actor operator
python3 spend-outcomes.pyz outcome --config "$HOME/.config/spend-outcomes/my-project.json" \
  --project my-project --statement "Revised intended result" \
  --success-criterion "Revised evidence of success" --actor operator
```

These commands preserve checkpoint history and old report snapshots. They read no
usage source and have no provider or workflow execution effect.

## Try the synthetic demo

This reads no user logs and clearly labels its generated data:

```sh
python3 spend-outcomes.pyz demo --root "$HOME/.local/state/spend-outcomes-demo"
```

Open the returned HTML path. The demo includes a meaningful token target and a
pending checkpoint, plus a command that explicitly marks it complete.

## What is measured

The direct source reads only `*.jsonl` files below roots you explicitly permit.
It retains timestamp, session/workspace identity, model name, and token counters.
It does not retain prompts, responses, instructions, or tool text. A session is
assigned only through its recorded workspace and your explicit mappings. Another
checkout must be added explicitly.

Observed tokens are input plus output tokens. Cached input and reasoning output
remain visible subclasses and are not added again. Repeated cumulative counters,
copied history, and compaction-response identities are deduplicated. Missing,
malformed, ambiguous, or partial coverage is labelled; a partial source does not
produce a full-window target comparison. Zero observed tokens is distinct from an
unavailable source.

Model names are descriptive observations. API-equivalent estimates, when an
eligible compatible export supplies them, are not billed cash or subscription
charges. The included direct Codex source makes no dollar claim. Targets are
advisory and have no execution effect.

## Optional compatible export

An existing complete, checksum-bound `telemetry-consumer-v1` export remains
supported. It is optional and is documented in [docs/sources.md](docs/sources.md).
Claude Code is not advertised as a live measurement source in version 1.0.1; an
assistant used for setup does not determine which logs the product measures.

## Privacy and recovery

Configuration, source paths, receipts, decisions, and HTML reports are private
local data. Keep them outside Git. The app does not discover roots, transmit data,
change provider settings, pause work, or write upstream systems. If a source is
missing or refused, repair that named binding; existing config and reports remain.

For recovery, select a retained GitHub release, verify its `SHA256SUMS`, and use
that release’s archive and setup prompt together. Do not mix assets from versions.

## Development and reproducible builds

```sh
python3 -m unittest discover -s tests -v
python3 -m compileall -q spend_outcomes scripts tests
git diff --check HEAD
```

`scripts/hn_delivery.py` is an effect-free compatibility entrypoint for the
deterministic builder. It archives only committed application Python and fixed
metadata. Building one exact commit twice produces byte-identical archives. The
versioned release allowlist is only `spend-outcomes.pyz`, `SHA256SUMS`, and
`CUSTOMER_SETUP_PROMPT.md`.

