# Cherry Meter

## 1.2.1-rc.1 Windows AMD64 / Claude Code preview

This independent preview provides device-local Codex and prospective Claude metrics
reports through a declared, readable-source MCP server. All five plugin commands
call only its tools. The server can start with the enabled plugin, but reads no
usage or device config at startup. It starts no receiver or child process,
downloads nothing, and makes no network requests. The interpreter setting defaults
to `python`, resolved through the host's PATH; that default is not a trust or
version check. A fresh enabled plugin may launch it before an override is set.
Before enabling, verify that it resolves to trusted Python 3.10+, preferably by
setting its verified absolute path in plugin settings. No runtime is bundled or
downloaded. Native qualification used an explicit trusted absolute override, not
an unconfigured PATH default.

Version 1.2.1-rc.1 packages the 1.2.0 declared-MCP design for an independent
self-hosted marketplace. It is not a stable release or an approved Anthropic
Directory listing. Start with [preview installation](docs/windows-preview.md).
Version and distribution metadata change, and plans now spell out existing
ancillary lock/temp/store writes. Actual I/O scope and the MCP execution boundary
are unchanged. Preview hashes change with the expanded descriptions.
The following native result belongs to the earlier 1.2.0 source: one controlled native Windows
Claude Code path passed declared-server discovery, info/doctor/report preview
and one approved report apply, with no denials, shell fallback or unrelated tool
calls. Other commands and client paths remain unqualified. Earlier 1.1.x results
below are historical and remain separate. See [MCP contract](docs/MCP_SERVER.md) and
[qualification](docs/qualification.md) for the current evidence and limits.

The separate native metrics helper and provider export settings remain
human-controlled installation steps. The plugin does not install, start, probe
or register that helper. Its tools work in-process on explicitly approved local
data. A missing server or a held operation must be reported, never retried through
a shell, PowerShell, native launcher, arbitrary file reader or external consumer.
The independent native CLI remains available to the operator outside plugin work.

The repository root is a self-contained readable-source Claude Code plugin.
Build a new source directory outside the checkout with
`python scripts/build_candidate.py --output NEW_DIRECTORY`.
This command records file hashes and has no publication or installation capability.
It emits no compiled archive or runtime download. The legacy deterministic pyz
builder remains separate from the directory candidate.

Use `/cherry-meter:setup`, `/cherry-meter:demo`, `/cherry-meter:report`,
`/cherry-meter:checkpoint` and `/cherry-meter:doctor` through the declared server.
Setup, demo, report and checkpoint first return a plan. Obtain actual approval
for its exact reads and writes, unless valid existing explicit pre-approval
already covers that scope, then apply with matching arguments and plan hash.
The hash guards stale or changed scope; it does not authenticate consent or grant
future access. Report plans include private snapshot writes and possible SQLite
`-wal`/`-shm` sidecar writes even though the metrics database is opened SQL
read-only. Diagnostics read only the approved config and path existence.

Paths must be ordinary absolute local paths without symlinks or reparse points.
Bounds and cooperative cancellation are not an OS sandbox: an OS-blocked read
cannot be forcibly interrupted, and completed writes may remain after failure
or cancellation. See [directory preparation](docs/directory-readiness.md) and
[data handling](PRIVACY.md) before considering submission.
The [qualification record](docs/qualification.md) distinguishes tested behavior
from missing evidence. The [remaining verification plan](docs/next-verification-plan.md)
sets out the policy, live-provider, native Mac and publisher actions in order.

## Documentation, privacy and support

- [Windows preview installation, updates and rollback](docs/windows-preview.md)
- [Setup and platform limits](docs/native-candidate.md)
- [Declared MCP contract and limitations](docs/MCP_SERVER.md)
- [Data handling and retention](PRIVACY.md)
- [Troubleshooting and support](docs/support.md)
- [Report an issue](https://github.com/josiahH-cf/spend-outcomes/issues)
- [Reviewer examples and Directory status](docs/directory-readiness.md)

GitHub issues are public. Do not attach private logs, reports, configuration,
workspace paths, session identifiers, credentials or personal information.
The Windows AMD64 and controlled Claude Code/Codex results are scoped to the
exact workflows recorded below. Directory validation and acceptance remain
separate from this independent preview. The 1.2.0 Directory submission was
refused on organization eligibility; see the [status record](docs/directory-readiness.md).

The measurement engine sends no measurements to a remote service. When used
through Claude, selected command output and reports may enter Claude's hosted
conversation and are processed under the user's Anthropic settings and policies.
Keep raw logs, secrets and unrelated private context out of the conversation.

## Preview packaging qualification (2026-11-11)

The 1.2.1-rc.1 package passed an isolated fresh-profile Claude Code install with
an explicit absolute Python setting, synthetic version update/rollback cycles,
and direct installed-manifest MCP demo/report calls returning 300 synthetic
tokens. The final permitted suite passed 147 tests, with one symlink skip and one
prior-denied PowerShell test excluded. Production configuration was unchanged.
This is not clean-OS, public-Git acquisition or authenticated fresh-client
qualification. See the [dated preview checks](docs/windows-preview.md).

## Controlled 1.2.0 native MCP result

On 2026-11-10, the naturally loaded declared server on audited commit
`ca7ce5499aa48cd984c7438b34c356eded1a7912` completed info, doctor, report preview
and one separately approved report apply. Plugin source/cache and configuration
remained unchanged. The MCP-produced report showed **112,131** tokens before
that apply session's final export. Independent reconciliation at 20:58:07 UTC
matched its 19,721 exported tokens, then three direct 1.2.0 reads held
**131,852 = 113,083 Claude + 18,769 Codex**. Preview-session usage separately
matched 18,460 tokens. These are dated checkpoints, not fixed or auto-refresh totals.

Claude attribution remained unassigned, coverage partial, and nine historical
collector gaps remained visible. This did not establish continuous capture,
full native acquisition, other client/IDE paths, native Mac/ARM, clean-machine
installation, or actual-client setup/demo/checkpoint workflows. The independent
helper remained at its existing 1.1.3 runtime. See [qualification](docs/qualification.md).

## Historical 1.1.x tandem setup and evidence

These results predate the 1.2.0 declared-MCP design. They qualify only the exact
native helper, provider sessions and shell-guided plugin path described here.

The candidate implements two independent measurement paths: Codex token metadata
from explicitly approved local JSONL roots, and prospective Claude Code token
metrics delivered to a separate loopback collector. They can appear together in
one device report. Using Claude to run a setup prompt does not itself enable
Claude measurement, and this does not measure ordinary Claude chat or Cowork.

- **Implemented:** independent and combined provider/model accounting, explicit
  attribution and coverage, and prospective Claude collection.
- **Live Codex evidence:** one controlled native Windows CLI session produced
  18,769 tokens. CLI output, its exact new session JSONL and the installed report
  agree; repeating the report did not double-count. Only that new test session
  was selected, so this does not establish ongoing acquisition from all sessions.
- **Other checks passed:** synthetic Claude and tandem accounting, local plugin
  installation, native Windows collector registration, stop/restart, duplicate
  prevention, relocation/rollback and a 1.1.1-to-1.1.2 collector upgrade/rollback
  with state retained.
- **Live tandem evidence (2026-11-10):** one native Claude Code 2.1.287
  noninteractive `sdk-cli` turn on `claude-sonnet-5-5` produced 513 tokens
  (500 input, 13 output, zero cache read/creation). Independent usage output and
  actual OTLP metrics matched exactly. Three reports were stable at 19,282:
  18,769 Codex plus 513 Claude. This is a controlled-pair checkpoint, not a fixed
  ongoing total. Claude project attribution remained explicitly unassigned.
- **Second live checkpoint (2026-11-10):** a cache-bearing Claude plugin-activation
  session matched 21,744 tokens independently, including nonzero cache-read and
  cache-creation. Three direct reports held 41,026 = 18,769 Codex + 22,257 Claude.
  The installed report command loaded, but its version check was denied before
  execution; that model call did not generate a report.
- **Corrected plugin workflow:** the normal 1.1.3 update matched all 31 package
  files. An operator-provided validator result passed, followed by exactly three
  installed-guide PowerShell commands for version, help and report in `dontAsk`
  mode, without permission denials, broader tools, root injection or fallback.
  Independent reconciliation at 19:22:39 UTC on 2026-11-10 matched 52,645 new
  tokens; three post-export direct reports held **93,671 = 74,902 Claude +
  18,769 Codex**. The plugin's own report showed 41,026 before its final export.
  The later total is a separately authorized direct refresh without further
  inference, not an auto-refresh dashboard. Attribution remained unassigned.
- **Still unverified:** other installed-plugin workflows,
  interactive CLI variants, each desktop/IDE launch path, ongoing full native
  source acquisition, reboot/logon/sleep continuity, schema-changing upgrades,
  and native Mac/ARM. A collector termination/gap was detected and recovered
  before the Claude test; capture was not uninterrupted. Synthetic inputs alone
  prove accounting/plumbing, not provider export delivery.

The following native CLI setup describes the separate human-controlled helper,
not commands for the 1.2.0 plugin to execute. Follow
[native device setup](docs/native-candidate.md), not the legacy archive prompt
below. With existing Python 3.10+, the operator can inspect
`python native/launch.py device-init --help`, choose explicit private config/state
paths and workspace bindings, and approve each Codex source root. Configure both
`--codex-root APPROVED_ROOT` and `--claude` for tandem use. Review the prospective
tracking start before collection. Separately review `export-plan`, approve the
specific client settings and collector startup, then verify actual client delivery
and `device-inspect` output. A synthetic `device-demo` is useful preparation but
cannot complete live-provider qualification. Never overwrite existing telemetry
settings or infer permission from a default source path. The local report viewer
shows a saved snapshot, not an auto-refresh dashboard; create a new report to
reflect later usage.

## Published 1.0.1: legacy WSL/Codex usage

The following archive instructions describe the published 1.0.1 project workflow,
not the 1.2.0 declared-MCP candidate. Keep historical release assets together.


Measure the Codex tokens observed for one project on WSL, compare them with an
advisory seven-day target, and track separately what you say has happened toward
the project’s outcome. The measurement engine runs locally; using an assistant
interface is also subject to that assistant's data handling. Usage never blocks work and never
marks an outcome checkpoint for you.

Previously called Spend & Outcomes. The `spend-outcomes.pyz` download name,
`spend_outcomes` Python module, repository URL, and existing config/state paths
remain compatible. Keep using your current config and saved reports; no data
migration is required. Version 1.0.1 updates the name in newly generated reports.

## Set up with an AI assistant (legacy 1.0.1)

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

## Manual setup (legacy 1.0.1)

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

## Legacy 1.0.1 synthetic demo

This reads no user logs and clearly labels its generated data:

```sh
python3 spend-outcomes.pyz demo --root "$HOME/.local/state/spend-outcomes-demo"
```

Open the returned HTML path. The demo includes a meaningful token target and a
pending checkpoint, plus a command that explicitly marks it complete.

## What the legacy Codex source measures

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

## Legacy optional compatible export

An existing complete, checksum-bound `telemetry-consumer-v1` export remains
supported. It is optional and is documented in [docs/sources.md](docs/sources.md).
Claude Code is not advertised as a live measurement source in version 1.0.1; an
assistant used for setup does not determine which logs the product measures.

## Legacy privacy and recovery

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

