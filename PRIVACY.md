# Cherry Meter candidate data handling

Current candidate: **1.3.0-rc.1 Windows AMD64 / Claude Code preview**.
See [preview installation and limits](docs/windows-preview.md). The 1.2.0 evidence below is
historical; it does not establish new platform or workflow qualification.
The report/setup boundary originated in 1.2.0/1.2.1-rc.1. The current candidate
adds explicit snapshot-bound decision recording and bounded decision-history
reads, described below. These new scopes require actual permission; they create
no standing access or work-execution authority.

The 1.2.1-rc.1 plans also describe existing ancillary writes. Report/demo output
can create adjacent persistent lock files and temporary files in approved
output directories; interrupted writes can leave temporary files. Demo creates
its own synthetic SQLite store and possible journal/WAL/shared-memory sidecars.
Setup directly creates only its config, with no lock/temp/store side effects,
but interruption can leave a partial config. See [write details](docs/MCP_SERVER.md).

The current and earlier independent previews have no approved Directory listing.
Support is available through the
[project issue tracker](https://github.com/josiahH-cf/spend-outcomes/issues).
Issues are public: do not post private logs, reports, configuration, identifiers
or credentials. This policy does not replace Anthropic's or OpenAI's policies
for their apps.

## What the local engine handles

The enabled plugin can start its declared local stdio MCP server. The interpreter
setting defaults to `python`, resolved through the host's PATH without verifying
its trust or version. A fresh enabled plugin may launch it before an override is
set. Before enabling, the operator must verify a trusted existing Python 3.10+
runtime, preferably by supplying its verified absolute path. The documented
server behavior assumes that trusted runtime, not an arbitrary PATH executable.
Startup loads bundled code but reads no usage or device config.
The server itself downloads nothing, starts no child process or receiver, and
makes no network requests. The independently installed metrics helper is a
separate human-controlled component; enabling the plugin does not install it.

- Explicitly approved Codex JSONL roots are read to extract usage metadata.
  The files can contain conversation content, so source-read permission matters
  even though that content is not saved in measurement records.
- Prospective Claude metrics arrive at the separate helper's loopback-only HTTP receiver. The engine
  accepts token counters and qualified source metadata, not log/trace endpoints.
- Stored metadata can include timestamps, session identifiers, model names,
  client/service and version, workspace paths, token classes, named agent/skill/
  plugin/MCP dimensions, source errors and collector lifecycle evidence.
- Selected user/account/email/repository identity attributes are fingerprinted
  for stream separation, not stored as raw values. Fingerprints are not a claim
  of anonymity. Unknown attributes fail closed; content fields such as prompts,
  responses, instructions, body references and tool bodies are not retained or
  followed.
- Configuration, operator-entered goals, checkpoint notes and feedback are
  private local records. Those free-text notes contain what the operator writes.

## Network and assistant boundary

The measurement engine does not send measurements to a remote service. The
separate helper's receiver listens on loopback and does not authenticate other local processes.
Use it only on a trusted machine; a local process can submit synthetic data.

All seven plugin commands call only the declared MCP tools, with no shell or
native-launcher fallback. Tool plans, selected metadata, diagnostics and report
summaries, human decision text and retrieved decision history may enter Claude's hosted conversation and be processed
under the user's Anthropic account settings and policies. Therefore, using the
assistant interface is not an end-to-end promise that all selected context stays
on the device. Do not paste raw session logs or secret headers into an assistant.

No credential or API key is required by this engine. Existing provider telemetry
headers, managed settings and launcher destinations must be reviewed before any
approved export change. This candidate does not apply those changes automatically.

## Approved reads and writes

The assistant must explain the exact configuration, sources and destinations
and obtain actual operator permission unless valid existing explicit pre-approval
already covers that exact scope. Setup, demo, report, checkpoint and decision tools
first return a plan. Applying repeats the same scope with its SHA-256 plan hash.
That hash rejects stale or changed scope; it does not authenticate human consent,
grant access or create a standing permission. Reading a config for a preview or
diagnostic can itself return private path and project metadata to the client.

Setup creates only a new config. Reporting reads bounded approved Codex metadata
and existing Claude metrics, then writes private JSON and optional HTML snapshots.
Claude SQLite is opened SQL read-only without schema or measurement changes, but
SQLite may create or update the explicitly listed `-wal` and `-shm` sidecars to
read current WAL data. A report is therefore not a promise of no filesystem writes.
Demo creates only the approved new synthetic-data directory and scoped adjacent
lock files. Checkpoint changes the selected config and adjacent lock/temporary
files. Retention remains operator controlled.

Decision preview reads the exact approved config and one saved device snapshot
under its private state/device-reports directory, validating canonical SHA256 and
matching device metadata. Apply reads the exact existing destination and optional
superseded record, and writes one immutable pv-decision-v1 record through the
existing state/decisions owner, plus the disclosed directory/lock/temp effects.
Records contain the person's actor, choice, reason, next action and review trigger,
exact snapshot digest, generation/contract/device-metadata provenance and optional
supersession. They are private free text, not anonymized data. Recording reads no
usage, changes no outcome and executes no next action.

Decision retrieval is a separately approved read of that config and its exact
decision directory: optionally one named ID, otherwise up to 128 records, each
at most 64 KiB, with a 1 MiB returned-history limit. It reads no usage or snapshots
and creates no files. Selected records are returned to the connected client.
Old reports and decisions remain immutable; no retention or deletion policy is
silently imposed. Static HTML next steps execute and save nothing.

Path checks reject traversal, UNC/device paths, Windows mapped network drives,
symlinks and reparse points. They are not an operating-system sandbox or protection
against every same-user path race. POSIX network mounts cannot reliably be
identified. Read-size and processing-time limits reduce scope; they cannot
forcibly interrupt an operating-system-blocked file read. Cancellation is
cooperative, and completed writes may remain after cancellation or failure.
Inspect the approved destinations before retrying; rollback is not automatic.

## Storage, retention and removal

The operator chooses private paths outside the plugin/repository. Measurement
stores, configuration and immutable reports remain until the operator removes
them. The candidate does not impose a retention period or silently delete old
records. Plugin updates/removal do not delete private state or unregister a
separately approved collector. Back up state before upgrades and review removal
of instrumentation or startup definitions separately.

POSIX file modes protect newly created files on supported POSIX filesystems.
Windows confidentiality depends on the selected directory's ACLs; POSIX mode
numbers do not establish equivalent Windows access control. No security settings
are changed by this candidate.

## Directory status

Publishing this source and policy does not establish Directory acceptance.
Final Directory validation, security scanning and listing approval remain
separate. The [qualification record](docs/qualification.md) describes the exact
tested platforms, workflows and remaining gaps.
